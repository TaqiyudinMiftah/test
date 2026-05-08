import logging
import logging.handlers
import os
import sys
from datetime import datetime
from app.config import settings

# Buat folder logs jika belum ada
LOG_DIR = "/app/logs"
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    """Setup logging configuration untuk AutoClip AI."""
    
    # Get log level dari environment
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Format log yang detail
    log_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Hapus handler yang sudah ada untuk menghindari duplikasi
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler - untuk development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # File handler - untuk menyimpan log ke file
    # Log semua level
    main_log_file = os.path.join(LOG_DIR, "autoclip.log")
    file_handler = logging.handlers.RotatingFileHandler(
        main_log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
    
    # Error log file - hanya untuk ERROR ke atas
    error_log_file = os.path.join(LOG_DIR, "autoclip-error.log")
    error_file_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=10,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(log_format)
    root_logger.addHandler(error_file_handler)
    
    # API access log
    api_log_file = os.path.join(LOG_DIR, "api-access.log")
    api_file_handler = logging.handlers.RotatingFileHandler(
        api_log_file,
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    api_file_handler.setLevel(logging.INFO)
    api_file_handler.setFormatter(log_format)
    api_logger = logging.getLogger("api.access")
    api_logger.addHandler(api_file_handler)
    api_logger.setLevel(logging.INFO)
    
    # Celery task log
    celery_log_file = os.path.join(LOG_DIR, "celery-tasks.log")
    celery_file_handler = logging.handlers.RotatingFileHandler(
        celery_log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    celery_file_handler.setLevel(logging.INFO)
    celery_file_handler.setFormatter(log_format)
    celery_logger = logging.getLogger("celery.tasks")
    celery_logger.addHandler(celery_file_handler)
    celery_logger.setLevel(logging.INFO)
    
    # AI/ML processing log
    ai_log_file = os.path.join(LOG_DIR, "ai-processing.log")
    ai_file_handler = logging.handlers.RotatingFileHandler(
        ai_log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    ai_file_handler.setLevel(logging.INFO)
    ai_file_handler.setFormatter(log_format)
    ai_logger = logging.getLogger("ai.processing")
    ai_logger.addHandler(ai_file_handler)
    ai_logger.setLevel(logging.INFO)
    
    # Log startup info
    root_logger.info("="*60)
    root_logger.info("AutoClip AI Backend Starting...")
    root_logger.info(f"Environment: {settings.ENVIRONMENT}")
    root_logger.info(f"Log Level: {settings.LOG_LEVEL}")
    root_logger.info(f"Log Directory: {LOG_DIR}")
    root_logger.info("="*60)
    
    return root_logger

# Singleton logger instance
logger = setup_logging()

def get_logger(name: str) -> logging.Logger:
    """Get logger dengan nama tertentu."""
    return logging.getLogger(name)
