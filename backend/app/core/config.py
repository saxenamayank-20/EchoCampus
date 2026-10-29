from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """app settings, read from .env (names are not case sensitive)"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # local sqlite for now, phase 3 only changes this url to neon postgres
    database_url: str = "sqlite:///./echocampus.db"

    # seed passwords, an empty one means that account is skipped
    admin_seed_password: str = ""
    gm001_password: str = ""
    gm002_password: str = ""
    gm003_password: str = ""
    gm004_password: str = ""

    # login tokens. empty secret = a random one each start (fine for dev, logs everyone out on restart)
    jwt_secret: str = ""
    jwt_expire_minutes: int = 30

    # comma separated, e.g. "college.edu,gla.ac.in". empty = any domain (dev mode)
    allowed_email_domains: str = ""
    frontend_origin: str = "http://localhost:5173"

    # email. no smtp host = otp and mails are printed in the console instead
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5

    # proof attachments
    upload_dir: str = "uploads"
    max_upload_mb: int = 5
    max_files_per_complaint: int = 5

    def seed_passwords(self) -> dict[str, str]:
        """staff user_id -> password from .env"""
        return {
            "ADMIN001": self.admin_seed_password,
            "GM001": self.gm001_password,
            "GM002": self.gm002_password,
            "GM003": self.gm003_password,
            "GM004": self.gm004_password,
        }

    def email_domains(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]


settings = Settings()
