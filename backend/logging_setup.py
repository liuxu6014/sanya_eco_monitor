import logging
import logging.config
from pathlib import Path

from config import settings


def _ensure_log_dir() -> Path:
    log_dir = Path(settings.LOG_DIR).expanduser()
    if not log_dir.is_absolute():
        log_dir = (Path(__file__).resolve().parent / log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def build_logging_config() -> dict:
    log_dir = _ensure_log_dir()

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(asctime)s [%(levelprefix)s] %(name)s: %(message)s",
                "use_colors": False,
            },
            "access": {
                "class": "logging.Formatter",
                "fmt": '%(asctime)s [%(levelname)s] %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": str(log_dir / "app.log"),
                "maxBytes": settings.LOG_FILE_MAX_BYTES,
                "backupCount": settings.LOG_FILE_BACKUP_COUNT,
                "encoding": "utf-8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": str(log_dir / "error.log"),
                "maxBytes": settings.LOG_FILE_MAX_BYTES,
                "backupCount": settings.LOG_FILE_BACKUP_COUNT,
                "encoding": "utf-8",
                "level": "WARNING",
            },
            "access_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "access",
                "filename": str(log_dir / "access.log"),
                "maxBytes": settings.LOG_FILE_MAX_BYTES,
                "backupCount": settings.LOG_FILE_BACKUP_COUNT,
                "encoding": "utf-8",
            },
        },
        "root": {
            "handlers": ["console", "app_file", "error_file"],
            "level": settings.LOG_LEVEL.upper(),
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["console", "app_file", "error_file"],
                "level": settings.LOG_LEVEL.upper(),
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console", "app_file", "error_file"],
                "level": settings.LOG_LEVEL.upper(),
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console", "access_file"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }


def configure_logging() -> None:
    logging.config.dictConfig(build_logging_config())
