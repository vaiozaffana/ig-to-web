from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Instagram Article Automation"
    environment: str = "development"
    database_url: str = "sqlite:///./data/ig_automation.db"
    redis_url: str = "redis://localhost:6379/0"
    admin_api_key: str = "dev-admin-key"

    instagram_access_token: str = ""
    instagram_account_id: str = ""
    instagram_limit: int = 10
    use_fake_instagram: bool = False

    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""

    model: str = "gpt-4.1-mini"
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"

    publish_adapter: str = "mock"
    public_base_url: str = "http://localhost:8000"
    worker_concurrency: int = Field(default=1, ge=1, le=2)
    task_max_retries: int = Field(default=3, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
