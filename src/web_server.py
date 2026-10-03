#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云枢 (YunShu) - Web Server Edition
Multi-brand Server Cluster & Thermal Management Web System
Strict Security & Authentication Gate with Apple Design Standards
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, Optional
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

# Set up module resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 解决 Windows 控制台默认 GBK 编码导致的字符异常
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from bottle import Bottle, request, response, static_file, redirect

from config_manager import ConfigManager
from log_manager import LogManager
from ipmi_core import IPMICore
from ssh_probe import SubsystemProbeManager
from alert_engine import AlertEngine
from api_bridge import APIBridge
from auth_manager import AuthManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("WebServer")

class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True

def create_app(bridge: APIBridge, auth_mgr: AuthManager) -> Bottle:
    app = Bottle()
    ui_dir = os.path.join(CURRENT_DIR, "ui")
    assets_dir = os.path.join(CURRENT_DIR, "assets")

    def get_client_ip() -> str:
        for header in ["X-Forwarded-For", "X-Real-IP"]:
            ip_val = request.headers.get(header)
            if ip_val:
                return ip_val.split(',')[0].strip()
        return request.remote_addr or "127.0.0.1"

    def get_auth_token() -> Optional[str]:
        # 1. Bearer header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        # 2. X-YunShu-Token header
        x_token = request.headers.get("X-YunShu-Token", "")
        if x_token:
            return x_token.strip()
        # 3. HttpOnly Cookie
        cookie_token = request.get_cookie("yunshu_session")
        if cookie_token:
            return cookie_token
        # 4. URL query param
        query_token = request.query.get("token")
        if query_token:
            return query_token
        return None

    def require_auth() -> Optional[Dict[str, Any]]:
        token = get_auth_token()
        return auth_mgr.validate_session(token)

    # -------------------------------------------------------------
    # Global Security Headers (Apple Security Standard)
    # -------------------------------------------------------------
    @app.hook('after_request')
    def enable_security_headers():
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # -------------------------------------------------------------
    # Static Assets (CSS, JS, Icons, Images)
    # -------------------------------------------------------------
    @app.route('/ui/<filename:path>')
    def serve_ui(filename):
        return static_file(filename, root=ui_dir)

    @app.route('/assets/<filename:path>')
    def serve_assets(filename):
        return static_file(filename, root=assets_dir)

    @app.route('/favicon.ico')
    def serve_favicon():
        return static_file('app_icon.ico', root=ui_dir)

    @app.route('/styles.css')
    def serve_styles():
        return static_file('styles.css', root=ui_dir, mimetype='text/css')

    @app.route('/app.js')
    def serve_app_js():
        return static_file('app.js', root=ui_dir, mimetype='application/javascript')

    @app.route('/api_client.js')
    def serve_api_client():
        return static_file('api_client.js', root=ui_dir, mimetype='application/javascript')

    @app.route('/<filename:re:.*\.(css|js|png|jpg|jpeg|ico|svg|woff|woff2|ttf)>')
    def serve_static_root(filename):
        if os.path.exists(os.path.join(ui_dir, filename)):
            return static_file(filename, root=ui_dir)
        if os.path.exists(os.path.join(assets_dir, filename)):
            return static_file(filename, root=assets_dir)
        return static_file(filename, root=ui_dir)

    @app.route('/healthz')
    def health_check():
        response.content_type = 'application/json; charset=utf-8'
        return {"status": "ok", "app": "YunShu", "version": "2.2-web"}

    # -------------------------------------------------------------
    # HTML Views (Protected vs Public)
    # -------------------------------------------------------------
    @app.route('/login')
    @app.route('/login.html')
    def login_page():
        session = require_auth()
        if session:
            redirect('/')
        return static_file('login.html', root=ui_dir)

    @app.route('/')
    @app.route('/index.html')
    def index_page():
        session = require_auth()
        if not session:
            redirect('/login')
        return static_file('index.html', root=ui_dir)

    # -------------------------------------------------------------
    # Auth Management Endpoints
    # -------------------------------------------------------------
    @app.post('/api/auth/login')
    def api_login():
        response.content_type = 'application/json; charset=utf-8'
        try:
            data = request.json or {}
        except Exception:
            data = {}
        username = str(data.get('username', '')).strip()
        password = str(data.get('password', ''))
        client_ip = get_client_ip()

        if not username or not password:
            response.status = 400
            return {"status": "error", "message": "用户名和密码不能为空"}

        success, message, user_info = auth_mgr.authenticate(username, password, client_ip)
        if not success:
            response.status = 401
            return {"status": "error", "message": message}

        token = user_info["token"]
        response.set_cookie(
            "yunshu_session",
            token,
            path="/",
            max_age=86400,
            httponly=True,
            samesite="Lax"
        )

        return {
            "status": "success",
            "message": message,
            "token": token,
            "user": user_info
        }

    @app.post('/api/auth/logout')
    def api_logout():
        response.content_type = 'application/json; charset=utf-8'
        token = get_auth_token()
        if token:
            auth_mgr.destroy_session(token)
        response.delete_cookie("yunshu_session", path="/")
        return {"status": "success", "message": "已成功退出登录"}

    @app.get('/api/auth/me')
    def api_auth_me():
        response.content_type = 'application/json; charset=utf-8'
        session = require_auth()
        if not session:
            response.status = 401
            return {"status": "error", "code": 401, "message": "未登录或登录已过期"}
        return {
            "status": "success",
            "user": {
                "username": session["username"],
                "display_name": session["display_name"],
                "role": session["role"],
                "require_password_change": session.get("require_password_change", False)
            }
        }

    @app.post('/api/auth/change_password')
    def api_change_password():
        response.content_type = 'application/json; charset=utf-8'
        session = require_auth()
        if not session:
            response.status = 401
            return {"status": "error", "code": 401, "message": "未登录或登录已过期"}

        try:
            data = request.json or {}
        except Exception:
            data = {}
        old_pwd = str(data.get('old_password', ''))
        new_pwd = str(data.get('new_password', ''))

        success, msg = auth_mgr.change_password(session["username"], old_pwd, new_pwd)
        if not success:
            response.status = 400
            return {"status": "error", "message": msg}
        return {"status": "success", "message": msg}

    @app.post('/api/auth/update_account')
    def api_update_account():
        response.content_type = 'application/json; charset=utf-8'
        session = require_auth()
        if not session:
            response.status = 401
            return {"status": "error", "code": 401, "message": "未登录或登录已过期"}

        try:
            data = request.json or {}
        except Exception:
            data = {}
        old_pwd = str(data.get('old_password', ''))
        new_username = str(data.get('new_username', '')).strip() if data.get('new_username') else None
        new_pwd = str(data.get('new_password', '')).strip() if data.get('new_password') else None
        display_name = str(data.get('display_name', '')).strip() if data.get('display_name') else None

        success, msg, user_info = auth_mgr.update_account(
            current_username=session["username"],
            old_password=old_pwd,
            new_username=new_username,
            new_password=new_pwd,
            display_name=display_name
        )
        if not success:
            response.status = 400
            return {"status": "error", "message": msg}
        return {"status": "success", "message": msg, "user": user_info}

    # -------------------------------------------------------------
    # Protected Business API Bridge Dispatcher
    # STRICT SECURITY: 未登录不得获取任何信息或执行任何操作
    # -------------------------------------------------------------
    @app.route('/api/<action:path>', method=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    def dispatch_api(action):
        response.content_type = 'application/json; charset=utf-8'

        if request.method == 'OPTIONS':
            return {}

        # 1. Enforce Authentication Guard
        session = require_auth()
        if not session:
            response.status = 401
            client_ip = get_client_ip()
            logger.warning(f"Unauthorized API access blocked: /api/{action} from {client_ip}")
            return {
                "status": "error",
                "code": 401,
                "message": "未登录或登录已过期，请重新登录"
            }

        # 2. Check if action exists on APIBridge
        method_name = action.strip('/')
        if not hasattr(bridge, method_name):
            response.status = 404
            return {
                "status": "error",
                "code": 404,
                "message": f"API 接口 '{method_name}' 未定义"
            }

        method = getattr(bridge, method_name)
        if not callable(method) or method_name.startswith('_'):
            response.status = 403
            return {
                "status": "error",
                "code": 403,
                "message": f"禁止直接访问内部方法"
            }

        # 3. Parse parameters
        args = []
        kwargs = {}
        if request.method in ['POST', 'PUT']:
            try:
                body = request.json
                if isinstance(body, dict):
                    if "args" in body and isinstance(body["args"], list):
                        args = body["args"]
                    else:
                        kwargs = body
                elif isinstance(body, list):
                    args = body
            except Exception:
                pass
        elif request.method == 'GET':
            for k in request.query.keys():
                kwargs[k] = request.query.get(k)

        # 4. Invoke API Bridge method
        try:
            if args:
                result = method(*args)
            elif kwargs:
                result = method(**kwargs)
            else:
                result = method()

            # Return response directly matching APIBridge contract
            if isinstance(result, dict):
                return result
            elif isinstance(result, (list, str, int, float, bool)) or result is None:
                return {"status": "success", "data": result}
            else:
                return {"status": "success", "data": str(result)}

        except Exception as e:
            logger.error(f"Error executing API method '{method_name}': {e}", exc_info=True)
            response.status = 500
            return {
                "status": "error",
                "code": 500,
                "message": f"后端处理异常: {str(e)}"
            }

    return app

def run_web_server(host: str = "0.0.0.0", port: int = 8080, config_path: Optional[str] = None):
    print(r"""
 __     __            ____  _            
 \ \   / /_   _ _ __ / ___|| |__  _   _ 
  \ \ / /| | | | '_ \\___ \| '_ \| | | |
   \ V / | |_| | | | |___) | | | | |_| |
    \_/   \__,_|_| |_|____/|_| |_|\__,_|
    云枢 (YunShu) - Web Edition · Apple Design
    """)

    config_mgr = ConfigManager(config_path) if config_path else ConfigManager()
    log_mgr = LogManager.get_instance(config_mgr=config_mgr)
    auth_mgr = AuthManager.get_instance()

    ssh_probe_mgr = SubsystemProbeManager(config_mgr)
    alert_engine = AlertEngine(config_mgr)
    ipmi_core = IPMICore(config_mgr)

    # Start background monitoring loops
    ipmi_core.start_monitoring()
    ssh_probe_mgr.start_monitoring()

    bridge = APIBridge(
        ipmi_core=ipmi_core,
        config_mgr=config_mgr,
        ssh_probe_mgr=ssh_probe_mgr,
        alert_engine=alert_engine,
        log_mgr=log_mgr
    )

    app = create_app(bridge, auth_mgr)

    logger.info("=" * 66)
    logger.info(" [Web] 云枢 (YunShu) Web 控制中心已启动")
    logger.info(f" [Host] 监听网络地址: http://{host}:{port}/")
    logger.info(f" [Local] 本地访问入口: http://127.0.0.1:{port}/")
    logger.info(" [Auth] 默认管理员: admin  |  初始密码: admin123")
    logger.info(" [Security] 安全防护状态: 未授权请求 100% 拦截 (HTTP 401)")
    logger.info("=" * 66)

    try:
        server = make_server(host, port, app, server_class=ThreadingWSGIServer)
    except OSError as e:
        logger.error(f"[错误] 绑定端口 {port} 失败: {e}")
        logger.error(f"[提示] 该端口可能已被其他程序占用，可尝试指定其他端口运行，例如: python run_web.py --port 8088")
        raise

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("正在安全退出 Web 服务...")
    finally:
        ipmi_core.stop_monitoring()
        ssh_probe_mgr.stop_monitoring()
        server.server_close()
        logger.info("云枢 Web 服务已停止。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YunShu Web Edition")
    parser.add_argument("--host", default="0.0.0.0", help="Binding host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Binding port (default: 8080)")
    parser.add_argument("--config", default=None, help="Custom path to config.ini")
    args = parser.parse_args()

    run_web_server(host=args.host, port=args.port, config_path=args.config)
