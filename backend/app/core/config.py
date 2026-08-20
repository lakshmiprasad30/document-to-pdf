from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Document to PDF API"
    REDIS_URL: str = "redis://redis:6379/0"
    MAX_CONVERSION_TIME: int = 300
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB limit
    TEMP_STORAGE_PATH: str = "/tmp/uploads"
    CONVERSION_TIMEOUT_SECONDS: int = 300  # 5 minutes

    # Security & Rate Limiting
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    RATE_LIMIT_CALLS: int = 10
    RATE_LIMIT_WINDOW: int = 60  # 60 seconds
    CLEANUP_TTL_SECONDS: int = 3600  # 1 hour

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
