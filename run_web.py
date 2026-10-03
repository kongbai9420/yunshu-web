#!python3.11
# -*- coding: utf-8 -*-
"""
云枢 (YunShu) - Web 服务启动器
运行此脚本即可在当前机器启动云枢 Web 版控制中心。
"""

import os
import sys
import subprocess

# 解决 Windows 控制台默认 GBK 编码导致的字符异常或崩溃
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 智能依赖检测与解释器重定向
# 如果当前启动的 Python (例如 Windows py.exe 默认拉起的 Python 3.13) 未安装 bottle，
# 自动寻找已安装好依赖的 Python (例如 Python 3.11) 无缝移交，防止闪退。
try:
    import bottle
except ImportError:
    candidate_commands = [
        ["py", "-3.11"],
        [os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\python.exe")],
        ["python3.11"],
        ["python3"]
    ]
    switched = False
    for cmd in candidate_commands:
        target = cmd[0]
        try:
            test_run = subprocess.run(
                cmd + ["-c", "import bottle"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            if test_run.returncode == 0:
                # 找到已就绪的 Python 解释器，无缝重定向执行当前脚本
                full_cmd = cmd + [os.path.abspath(__file__)] + sys.argv[1:]
                ret = subprocess.call(full_cmd)
                sys.exit(ret)
        except Exception:
            continue

    print("=" * 60)
    print("【错误】未在当前 Python 环境中检测到 bottle 依赖库！")
    print(f"当前运行的 Python: {sys.executable}")
    print("请使用已安装依赖的 Python 环境运行，或执行：")
    print("    pip install bottle paramiko cryptography bcrypt")
    print("=" * 60)
    input("\n按回车键退出...")
    sys.exit(1)

import argparse

# 确保当前目录和 src 目录在模块搜索路径中
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from web_server import run_web_server

    if __name__ == "__main__":
        parser = argparse.ArgumentParser(description="启动云枢 Web 端控制中心")
        parser.add_argument("--host", default="0.0.0.0", help="监听地址 (默认: 0.0.0.0 允许局域网访问)")
        parser.add_argument("--port", type=int, default=8080, help="监听端口 (默认: 8080)")
        parser.add_argument("--config", default=None, help="自定义配置文件路径 (可选)")
        args = parser.parse_args()

        run_web_server(host=args.host, port=args.port, config_path=args.config)

except KeyboardInterrupt:
    print("\n已退出服务。")
except Exception as e:
    import traceback
    print("\n" + "=" * 60)
    print("【服务运行异常】详细错误堆栈如下：")
    traceback.print_exc()
    print("=" * 60)
    input("\n按回车键退出...")
    sys.exit(1)
