from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    ENV: str = "dev"
    UVICORN_WORKERS: int = 2


settings = Settings()
