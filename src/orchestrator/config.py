"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "agentic-shell"
    app_env: str = "development"
    app_port: int = 8000
    debug: bool = True
    secret_key: str = "change-me-in-production"

    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/agenticdb"
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    etcd_host: str = "localhost"
    etcd_port: int = 2379

    consul_host: str = "localhost"
    consul_port: int = 8500

    cors_origins: list[str] = ["*"]

    openai_api_key: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
