from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 安全敏感字段：无默认值，必须在 .env 中配置
    secret_key: str
    admin_username: str
    admin_password: str
    fernet_key: str
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    log_level: str = "INFO"
    dashscope_api_key: str = ""  # 阿里云通义千问 API key，用于 AI 摘要生成


settings = Settings()
