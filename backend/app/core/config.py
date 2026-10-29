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

    def seed_passwords(self) -> dict[str, str]:
        """staff user_id -> password from .env"""
        return {
            "ADMIN001": self.admin_seed_password,
            "GM001": self.gm001_password,
            "GM002": self.gm002_password,
            "GM003": self.gm003_password,
            "GM004": self.gm004_password,
        }


settings = Settings()
