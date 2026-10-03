import os
import json
import time
import secrets
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("AuthManager")

def _resolve_users_file() -> str:
    env_file = os.environ.get("YUNSHU_USERS_FILE")
    if env_file:
        return env_file
    candidates = [
        os.path.join(os.getcwd(), "data", "users.json"),
        os.path.join(os.getcwd(), "users.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    data_dir = os.path.join(os.getcwd(), "data")
    if os.path.isdir(data_dir):
        return os.path.join(data_dir, "users.json")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")

USERS_FILE = _resolve_users_file()
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SEC = 300  # 5 minutes
SESSION_EXPIRATION_SEC = 86400  # 24 hours

class AuthManager:
    _instance = None

    @classmethod
    def get_instance(cls, file_path: str = USERS_FILE):
        if cls._instance is None:
            cls._instance = cls(file_path)
        return cls._instance

    def __init__(self, file_path: str = USERS_FILE):
        self.file_path = file_path
        self._sessions: Dict[str, Dict[str, Any]] = {}  # token -> session_data
        self._failed_attempts: Dict[str, list] = {}     # ip -> [timestamp, ...]
        self._lockouts: Dict[str, float] = {}          # ip -> locked_until_ts
        self._load_or_init_users()

    def _hash_password(self, password: str, salt: Optional[str] = None) -> str:
        """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        pwd_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        key = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000)
        return f"pbkdf2_sha256${salt}${key.hex()}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored PBKDF2 hash."""
        try:
            parts = stored_hash.split('$')
            if len(parts) != 3 or parts[0] != "pbkdf2_sha256":
                return False
            salt = parts[1]
            expected_key = parts[2]
            pwd_bytes = password.encode('utf-8')
            salt_bytes = salt.encode('utf-8')
            actual_key = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000).hex()
            return secrets.compare_digest(actual_key, expected_key)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def _load_or_init_users(self):
        if not os.path.exists(self.file_path):
            # Create default administrator account
            default_admin = {
                "admin": {
                    "username": "admin",
                    "display_name": "系统管理员",
                    "role": "admin",
                    "password_hash": self._hash_password("admin123"),
                    "created_at": time.time(),
                    "last_login": None,
                    "require_password_change": True
                }
            }
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(default_admin, f, indent=2, ensure_ascii=False)
                logger.info(f"Initialized default user config at {self.file_path}")
            except Exception as e:
                logger.error(f"Failed to create default users file: {e}")
        else:
            logger.info(f"Loaded existing users configuration from {self.file_path}")

    def _read_users(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading users file: {e}")
            return {}

    def _save_users(self, users: Dict[str, Any]) -> bool:
        try:
            temp_path = self.file_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(users, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.file_path)
            return True
        except Exception as e:
            logger.error(f"Error saving users file: {e}")
            return False

    def is_ip_locked(self, client_ip: str) -> Tuple[bool, int]:
        """Check if client IP is locked due to excessive failed attempts."""
        now = time.time()
        lock_until = self._lockouts.get(client_ip, 0)
        if now < lock_until:
            remaining_seconds = int(lock_until - now)
            return True, remaining_seconds
        elif client_ip in self._lockouts:
            del self._lockouts[client_ip]
        return False, 0

    def record_failed_attempt(self, client_ip: str):
        now = time.time()
        attempts = self._failed_attempts.get(client_ip, [])
        # Filter attempts within the lockout window
        attempts = [t for t in attempts if now - t < LOCKOUT_DURATION_SEC]
        attempts.append(now)
        self._failed_attempts[client_ip] = attempts

        if len(attempts) >= MAX_FAILED_ATTEMPTS:
            self._lockouts[client_ip] = now + LOCKOUT_DURATION_SEC
            logger.warning(f"Client IP {client_ip} locked out for {LOCKOUT_DURATION_SEC}s due to {len(attempts)} failed attempts.")

    def clear_failed_attempts(self, client_ip: str):
        self._failed_attempts.pop(client_ip, None)
        self._lockouts.pop(client_ip, None)

    def authenticate(self, username: str, password: str, client_ip: str = "127.0.0.1") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Authenticate user with brute-force protection.
        Returns: (success: bool, message: str, user_dict_or_none)
        """
        is_locked, remaining = self.is_ip_locked(client_ip)
        if is_locked:
            return False, f"登录失败次数过多，IP已被锁定，请在 {remaining} 秒后再试", None

        users = self._read_users()
        user = users.get(username)
        if not user:
            self.record_failed_attempt(client_ip)
            return False, "用户名或密码错误", None

        if not self._verify_password(password, user.get("password_hash", "")):
            self.record_failed_attempt(client_ip)
            return False, "用户名或密码错误", None

        # Successful login
        self.clear_failed_attempts(client_ip)
        user["last_login"] = time.time()
        users[username] = user
        self._save_users(users)

        # Generate session
        token = secrets.token_hex(32)
        session_data = {
            "token": token,
            "username": user["username"],
            "display_name": user.get("display_name", user["username"]),
            "role": user.get("role", "admin"),
            "client_ip": client_ip,
            "created_at": time.time(),
            "expires_at": time.time() + SESSION_EXPIRATION_SEC,
            "require_password_change": user.get("require_password_change", False)
        }
        self._sessions[token] = session_data

        user_info = {
            "username": user["username"],
            "display_name": user.get("display_name", user["username"]),
            "role": user.get("role", "admin"),
            "require_password_change": user.get("require_password_change", False),
            "token": token
        }
        logger.info(f"User '{username}' authenticated successfully from {client_ip}")
        return True, "登录成功", user_info

    def validate_session(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """Validate session token and check expiration."""
        if not token:
            return None
        session = self._sessions.get(token)
        if not session:
            return None
        if time.time() > session["expires_at"]:
            self._sessions.pop(token, None)
            return None
        # Refresh expiration window on active request
        session["expires_at"] = time.time() + SESSION_EXPIRATION_SEC
        return session

    def destroy_session(self, token: Optional[str]) -> bool:
        if token and token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        success, msg, _ = self.update_account(
            current_username=username,
            old_password=old_password,
            new_password=new_password
        )
        return success, msg

    def update_account(
        self,
        current_username: str,
        old_password: str,
        new_username: Optional[str] = None,
        new_password: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Update user account credentials (username, password, display name).
        Requires verification of current password.
        """
        users = self._read_users()
        user = users.get(current_username)
        if not user:
            return False, "当前用户不存在", None

        if not self._verify_password(old_password, user.get("password_hash", "")):
            return False, "原密码验证错误，请重新输入", None

        target_username = current_username
        if new_username and new_username.strip():
            new_username = new_username.strip()
            if len(new_username) < 3 or len(new_username) > 32:
                return False, "新用户名长度需在 3 至 32 个字符之间", None
            import re
            if not re.match(r"^[a-zA-Z0-9_\-\u4e00-\u9fa5]+$", new_username):
                return False, "用户名仅支持字母、数字、下划线、短横线与中文", None
            if new_username != current_username and new_username in users:
                return False, f"用户名 '{new_username}' 已存在，请使用其他名称", None
            target_username = new_username

        if new_password and new_password.strip():
            new_password = new_password.strip()
            if len(new_password) < 6:
                return False, "新密码长度不得少于 6 位", None
            user["password_hash"] = self._hash_password(new_password)
            user["require_password_change"] = False

        if display_name and display_name.strip():
            user["display_name"] = display_name.strip()
        elif target_username != current_username and user.get("display_name") == current_username:
            user["display_name"] = target_username

        user["username"] = target_username
        user["updated_at"] = time.time()

        if target_username != current_username:
            users.pop(current_username, None)
            users[target_username] = user
            # Update any active sessions with new username
            for s in self._sessions.values():
                if s.get("username") == current_username:
                    s["username"] = target_username
                    s["display_name"] = user.get("display_name", target_username)
        else:
            users[current_username] = user

        if not self._save_users(users):
            return False, "保存用户配置失败", None

        logger.info(f"User account updated successfully: '{current_username}' -> '{target_username}'")
        user_info = {
            "username": user["username"],
            "display_name": user.get("display_name", user["username"]),
            "role": user.get("role", "admin")
        }
        return True, "账号设置更新成功", user_info
