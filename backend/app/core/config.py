from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """app settings, read from .env (names are not case sensitive)"""

    # env_ignore_empty: an empty line like LLM_MODEL= means "use the default below"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

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

    # email. brevo key = send over https (render free blocks smtp ports),
    # else smtp host = send over smtp, else otp and mails are printed in the console
    brevo_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    # logo in emails. empty = the frontend's icon. set it for local runs, mail apps can't load localhost
    email_logo_url: str = ""
    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5
    # forgot details: recovery + login codes one student can ask for per day, after that they contact the tech team
    recovery_codes_per_day: int = 5
    # who students contact when they're stuck (shown in pages and emails). empty = the sender email
    support_email: str = ""

    # proof attachments
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

    # ai (gemini). no key = the app works without ai, keyword priority only.
    # model names checked against ai.google.dev/gemini-api/docs/models on 2026-11-01
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    llm_model: str = "gemini-3.5-flash-lite"
    embedding_model: str = "gemini-embedding-2"
    embedding_dim: int = 768        # fixed in the database column, changing it needs a migration
    llm_max_rpm: int = 8            # text model calls per minute, under the free tier limit
    embed_max_rpm: int = 30         # embedding calls per minute (a separate model with its own limit)
    llm_timeout_seconds: int = 20
    duplicate_threshold: float = 0.85
    rag_min_similarity: float = 0.45   # below this, the policy search says "not in the documents"
    ai_requests_per_hour: int = 20     # per user, for preview / assistant / reply drafts
    counsellor_contact: str = ("Student counselling (free, confidential): counsellor@echocampus.example, "
                               "Student Welfare Office")
    crisis_helpline: str = "Tele-MANAS 14416 (free, 24x7)"

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

    def support_contact(self) -> str:
        return self.support_email or self.smtp_from or "the admin office"

    def email_domains(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]


settings = Settings()
