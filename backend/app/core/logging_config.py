"""Structured logging configuration for production."""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

from config import get_settings

settings = get_settings()


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        
        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Colored console formatter for development."""
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, "")
        
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        formatted = f"{color}{timestamp} [{record.levelname:8}] {record.name}: {record.getMessage()}{self.RESET}"
        
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


class ExtraLogAdapter(logging.LoggerAdapter):
    """Logger adapter that supports extra fields."""
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process the logging call to add extra data."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_file: Optional[str] = None
) -> None:
    """
    Configure logging for the application.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('console' or 'json')
        log_file: Optional file path for logging
    """
    level = log_level or settings.log_level
    fmt = log_format or settings.log_format
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    root_logger.handlers.clear()
    
    if fmt == "json":
        formatter = JSONFormatter()
    else:
        formatter = ConsoleFormatter()
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.WARNING)
    logging.getLogger("deepface").setLevel(logging.WARNING)
    logging.getLogger("whisper").setLevel(logging.WARNING)


def get_logger(name: str, **extra) -> ExtraLogAdapter:
    """
    Get a logger with optional extra fields.
    
    Args:
        name: Logger name
        **extra: Extra fields to include in all log messages
    
    Returns:
        Logger adapter with extra fields
    """
    logger = logging.getLogger(name)
    return ExtraLogAdapter(logger, extra)


class RequestLogger:
    """Context manager for request logging."""
    
    def __init__(self, request_id: str, method: str, path: str):
        self.request_id = request_id
        self.method = method
        self.path = path
        self.logger = get_logger("request", request_id=request_id)
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.info(f"Request started: {self.method} {self.path}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        if exc_type:
            self.logger.error(
                f"Request failed: {self.method} {self.path}",
                exc_info=(exc_type, exc_val, exc_tb),
                extra={"extra_data": {"duration_ms": duration_ms}}
            )
        else:
            self.logger.info(
                f"Request completed: {self.method} {self.path}",
                extra={"extra_data": {"duration_ms": duration_ms}}
            )
        
        return False
