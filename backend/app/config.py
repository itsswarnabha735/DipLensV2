from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # API Keys
    alpha_vantage_api_key: str = "your_key_here"
    gemini_api_key: str = ""
    
    # Cache settings
    cache_ttl_seconds: int = 30
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    
    # Logging
    log_level: str = "INFO"
    
    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
