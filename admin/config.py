"""后台配置：全部来自环境变量，secret 一律不进 git。"""

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Settings:
    def __init__(self) -> None:
        self.admin_path = os.getenv("ADMIN_PATH", "admin").strip("/")
        self.db_path = Path(os.getenv("DB_PATH", str(ROOT / "data" / "blog.db")))
        self.content_root = Path(os.getenv("CONTENT_ROOT", str(ROOT / "content")))
        self.config_root = Path(os.getenv("CONFIG_ROOT", str(ROOT / "config")))
        self.output_root = Path(os.getenv("OUTPUT_ROOT", str(ROOT / "output")))
        self.preview_root = Path(os.getenv("PREVIEW_ROOT", str(ROOT / ".preview-out")))
        self.beacon_log = os.getenv("BEACON_LOG", str(ROOT / "data" / "beacon.log"))
        self.import_max_files = int(os.getenv("IMPORT_MAX_FILES", "200"))
        self.import_max_file_bytes = int(os.getenv("IMPORT_MAX_FILE_BYTES", str(2 * 1024 * 1024)))
        self.import_max_zip_bytes = int(os.getenv("IMPORT_MAX_ZIP_BYTES", str(20 * 1024 * 1024)))
        self.restore_max_files = int(os.getenv("RESTORE_MAX_FILES", "5000"))
        self.restore_max_bytes = int(os.getenv("RESTORE_MAX_BYTES", str(100 * 1024 * 1024)))
        self.revision_max = int(os.getenv("REVISION_MAX", "50"))
        self.cookie_secure = os.getenv("COOKIE_SECURE", "0") == "1"
        self.session_ttl = int(os.getenv("SESSION_TTL", "43200"))
        self.session_secret = self._resolve_session_secret()
        self.lipass_issuer = os.getenv("LIPASS_ISSUER", "").rstrip("/")
        self.lipass_client_id = os.getenv("LIPASS_CLIENT_ID", "")
        self.lipass_client_secret = os.getenv("LIPASS_CLIENT_SECRET", "")
        self.lipass_redirect_uri = os.getenv("LIPASS_REDIRECT_URI", "")
        self.ip_whitelist = [
            x.strip() for x in os.getenv("ADMIN_IP_WHITELIST", "").split(",") if x.strip()
        ]

    @staticmethod
    def _resolve_session_secret() -> str:
        """会话密钥优先读环境变量；缺失时使用 DB 同目录 secret 文件持久化。

        避免每次进程启动随机生成导致重启后全部会话失效，
        也避免多 worker 各自持有不同密钥。
        """
        env_secret = os.getenv("ADMIN_SESSION_SECRET")
        if env_secret:
            return env_secret
        db_path = Path(os.getenv("DB_PATH", str(ROOT / "data" / "blog.db")))
        secret_path = db_path.parent / ".session_secret"
        try:
            if secret_path.exists():
                stored = secret_path.read_text(encoding="utf-8").strip()
                if len(stored) >= 32:
                    return stored
            value = secrets.token_hex(32)
            secret_path.parent.mkdir(parents=True, exist_ok=True)
            secret_path.write_text(value, encoding="utf-8")
            try:
                os.chmod(secret_path, 0o600)
            except OSError:
                pass
            return value
        except OSError:
            # 极端只读场景兜底：会话无法跨重启保持，但应用仍可启动
            return secrets.token_hex(32)


settings = Settings()
