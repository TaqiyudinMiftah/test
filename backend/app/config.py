from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/autoclip"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "autoclip"
    MINIO_SECURE: bool = False
    
    # Auth
    SECRET_KEY: str = "change-this-to-32-char-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    
    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"
    
    # App
    MAX_UPLOAD_SIZE: int = 4294967296  # 4GB
    MAX_CONCURRENT_JOBS: int = 3
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Video Processing
    WHISPER_MODEL: str = "base"
    SCENE_DETECT_THRESHOLD: float = 27.0
    MIN_SCENE_DURATION: int = 3
    MAX_SCENES: int = 150
    TOP_N_CLIPS: int = 10
    OUTPUT_FORMATS: str = "9:16,16:9,1:1"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Parse output formats
OUTPUT_FORMATS_LIST: List[str] = [f.strip() for f in settings.OUTPUT_FORMATS.split(",")]
