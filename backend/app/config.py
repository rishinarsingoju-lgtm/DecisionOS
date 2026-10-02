from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str | None = None
    frontend_origins: str = "http://localhost:4000,http://127.0.0.1:4000"
    expiry_threshold_days: int = 60
    excess_cover_days: int = 180
    stockout_buffer_days: int = 2
    currency_tolerance: float = 1.0
    probability_tolerance: float = 0.0001

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


settings = Settings()