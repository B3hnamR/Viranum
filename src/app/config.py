from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    BOT_TOKEN: str = Field(..., description="Telegram bot token")
    ADMIN_IDS: str = Field("", description="Comma separated telegram user IDs")
    NUMBERLAND_API_KEY: str = Field("", description="Numberland API key")
    FIVESIM_API_KEY: str = Field("", description="5SIM API key")

    DB_DSN: str = Field("postgresql+asyncpg://viranum:viranum@db:5432/viranum")
    REDIS_DSN: str = Field("redis://redis:6379/0")

    BASE_MARKUP_PERCENT: float = 20.0
    MARKUP_ROUND_TO: int = 100

    BOT_MODE: str = "polling"
    LOCALE_DEFAULT: str = "fa"

    # Providers
    ENABLED_PROVIDERS: str = Field(
        "numberland", description="Comma separated provider keys (e.g., numberland,5sim)"
    )
    PROVIDERS_DISPLAY: str = Field(
        "numberland:Numberland", description="Display names map e.g. key:name|key2:name2"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
