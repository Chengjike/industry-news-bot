from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    secret_key: str = "dev-secret-key-change-in-production"
    admin_username: str = "admin"
    admin_password: str = "admin123"
    fernet_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    log_level: str = "INFO"
    anthropic_api_key: str = ""  # Claude API key for AI summary generation


settings = Settings()
