"""
Orchestrator Configuration Module
Centralized configuration management with environment variable support
"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseSettings, Field
from functools import lru_cache


class DatabaseConfig(BaseSettings):
    """Database configuration settings"""
    host: str = Field("postgres", env="POSTGRES_HOST")
    port: int = Field(5432, env="POSTGRES_PORT")
    database: str = Field("agentic", env="POSTGRES_DB")
    user: str = Field("agentic", env="POSTGRES_USER")
    password: str = Field("agentic123", env="POSTGRES_PASSWORD")
    min_size: int = Field(5, env="DB_POOL_MIN_SIZE")
    max_size: int = Field(20, env="DB_POOL_MAX_SIZE")
    
    @property
    def dsn(self) -> str:
        """Get PostgreSQL DSN"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class RedisConfig(BaseSettings):
    """Redis configuration settings"""
    host: str = Field("redis", env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    db: int = Field(0, env="REDIS_DB")
    
    @property
    def url(self) -> str:
        """Get Redis URL"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class RabbitMQConfig(BaseSettings):
    """RabbitMQ configuration settings"""
    host: str = Field("rabbitmq", env="RABBITMQ_HOST")
    port: int = Field(5672, env="RABBITMQ_PORT")
    user: str = Field("agentic", env="RABBITMQ_USER")
    password: str = Field("agentic123", env="RABBITMQ_PASS")
    vhost: str = Field("/", env="RABBITMQ_VHOST")
    
    @property
    def url(self) -> str:
        """Get RabbitMQ URL"""
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}{self.vhost}"


class EtcdConfig(BaseSettings):
    """etcd configuration settings"""
    host: str = Field("etcd", env="ETCD_HOST")
    port: int = Field(2379, env="ETCD_PORT")
    
    @property
    def endpoint(self) -> str:
        """Get etcd endpoint"""
        return f"{self.host}:{self.port}"


class ConsulConfig(BaseSettings):
    """Consul configuration settings"""
    host: str = Field("consul", env="CONSUL_HOST")
    port: int = Field(8500, env="CONSUL_PORT")
    
    @property
    def url(self) -> str:
        """Get Consul URL"""
        return f"http://{self.host}:{self.port}"


class AgentConfig(BaseSettings):
    """Agent configuration settings"""
    planner_replicas: int = Field(3, env="PLANNER_REPLICAS")
    executor_replicas: int = Field(5, env="EXECUTOR_REPLICAS")
    coder_replicas: int = Field(4, env="CODER_REPLICAS")
    debugger_replicas: int = Field(2, env="DEBUGGER_REPLICAS")
    optimizer_replicas: int = Field(2, env="OPTIMIZER_REPLICAS")
    reflector_replicas: int = Field(1, env="REFLECTOR_REPLICAS")
    
    agent_timeout: int = Field(60, env="AGENT_TIMEOUT_SECONDS")
    max_queue_size: int = Field(1000, env="MAX_QUEUE_SIZE")


class LoggingConfig(BaseSettings):
    """Logging configuration settings"""
    level: str = Field("INFO", env="LOG_LEVEL")
    format: str = Field("json", env="LOG_FORMAT")
    file: str = Field("/app/logs/agentic-shell.log", env="LOG_FILE")


class OrchestratorConfig(BaseSettings):
    """Main orchestrator configuration"""
    
    # Server settings
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    debug: bool = Field(False, env="DEBUG")
    reload: bool = Field(False, env="RELOAD")
    
    # Component configs
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    etcd: EtcdConfig = EtcdConfig()
    consul: ConsulConfig = ConsulConfig()
    agents: AgentConfig = AgentConfig()
    logging: LoggingConfig = LoggingConfig()
    
    # Security
    jwt_secret: str = Field("change-me-in-production", env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiration: int = Field(3600, env="JWT_EXPIRATION")
    
    # Mistral AI
    mistral_api_key: Optional[str] = Field(None, env="MISTRAL_API_KEY")
    mistral_agent_id: str = Field("ag_019ca619014874dfbef495f2174d390d", env="AGENT_ID")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(100, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(60, env="RATE_LIMIT_PERIOD")
    
    # Feature flags
    enable_kubernetes: bool = Field(True, env="ENABLE_KUBERNETES")
    enable_docker: bool = Field(True, env="ENABLE_DOCKER")
    enable_aws: bool = Field(True, env="ENABLE_AWS")
    enable_github: bool = Field(True, env="ENABLE_GITHUB")
    enable_shell: bool = Field(True, env="ENABLE_SHELL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_config() -> OrchestratorConfig:
    """Get cached configuration"""
    return OrchestratorConfig()


config = get_config()