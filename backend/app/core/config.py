from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """app settings, read from .env (names are not case sensitive)"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # local sqlite for now, phase 3 only changes this url to neon postgres
    database_url: str = "sqlite:///./echocampus.db"

    # seed passwords, an empty one means that account is skipped
    admin_seed_password: str = ""
    gm101_password: str = ""
    gm102_password: str = ""
    gm103_password: str = ""
    gm104_password: str = ""

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

    # redis cache + rate limits. no redis url = an in-memory cache inside the app (fine for one server)
    redis_url: str = ""
    rate_limit_complaints_per_hour: int = 5
    rate_limit_logins_per_15_min: int = 10

    # sla: hours a complaint may stay open before it is escalated
    sla_hours_critical: int = 4
    sla_hours_high: int = 48
    sla_hours_medium: int = 72
    sla_hours_low: int = 168
    run_scheduler: bool = True   # the 15 minute background job

    # student has this many days to say "fixed" or "not fixed", then it auto-confirms
    confirmation_window_days: int = 3

    def sla_hours(self, priority: str) -> int:
        return {"Critical": self.sla_hours_critical, "High": self.sla_hours_high,
                "Medium": self.sla_hours_medium}.get(str(priority), self.sla_hours_low)

    def seed_passwords(self) -> dict[str, str]:
        """staff user_id -> password from .env"""
        return {
            "AD100": self.admin_seed_password,
            "GM101": self.gm101_password,
            "GM102": self.gm102_password,
            "GM103": self.gm103_password,
            "GM104": self.gm104_password,
        }

    def email_domains(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]


settings = Settings()
