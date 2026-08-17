"""后台配置：全部来自环境变量，secret 一律不进 git。"""

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Settings:
    def __init__(self) -> None:
        self.admin_path = os.getenv("ADMIN_PATH", "admin-xxxx").strip("/")
        self.db_path = Path(os.getenv("DB_PATH", str(ROOT / "data" / "blog.db")))
        self.content_root = Path(os.getenv("CONTENT_ROOT", str(ROOT / "content")))
        self.config_root = Path(os.getenv("CONFIG_ROOT", str(ROOT / "config")))
        self.output_root = Path(os.getenv("OUTPUT_ROOT", str(ROOT / "output")))
        self.preview_root = Path(os.getenv("PREVIEW_ROOT", str(ROOT / ".preview-out")))
        self.beacon_log = os.getenv("BEACON_LOG", str(ROOT / "data" / "beacon.log"))
        self.cookie_secure = os.getenv("COOKIE_SECURE", "0") == "1"
        self.session_ttl = int(os.getenv("SESSION_TTL", "43200"))
        self.session_secret = os.getenv("ADMIN_SESSION_SECRET", secrets.token_hex(32))
        self.lipass_issuer = os.getenv("LIPASS_ISSUER", "").rstrip("/")
        self.lipass_client_id = os.getenv("LIPASS_CLIENT_ID", "")
        self.lipass_client_secret = os.getenv("LIPASS_CLIENT_SECRET", "")
        self.lipass_redirect_uri = os.getenv("LIPASS_REDIRECT_URI", "")
        self.ip_whitelist = [
            x.strip() for x in os.getenv("ADMIN_IP_WHITELIST", "").split(",") if x.strip()
        ]


settings = Settings()
