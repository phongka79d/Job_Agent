import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs log records as structured JSON strings.
    """
    def format(self, record: logging.LogRecord) -> str:
        import json
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        # Add custom extra fields if they exist and do not overwrite standard keys
        extra_keys = set(record.__dict__.keys()) - {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName", "processName", "process"
        }
        for key in extra_keys:
            log_record[key] = record.__dict__[key]
            
        return json.dumps(log_record)


class SecretMaskingFilter(logging.Filter):
    """
    A logging filter that masks sensitive values (API keys, secrets) to prevent
    them from being exposed in log outputs.
    """
    def __init__(self, name: str = "", secrets: Optional[List[str]] = None) -> None:
        super().__init__(name)
        self.secrets = []
        if secrets:
            for s in secrets:
                # Mask only values with significant length to avoid masking common single characters.
                # Skip known non-secret defaults to keep configuration logs readable.
                if s and len(s) > 4 and not any(p in s.lower() for p in ["your-openai-api-key", "your-tavily-api-key", "your-qdrant-api-key"]):
                    self.secrets.append(s)

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._mask(record.msg)
        if record.args:
            record.args = tuple(
                self._mask(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True

    def _mask(self, val: str) -> str:
        for secret in self.secrets:
            val = val.replace(secret, "********")
        # Regex safety fallback for standard key formats (allowing letters, digits, and hyphens)
        val = re.sub(r"sk-[a-zA-Z0-9\-]{15,}", "sk-********", val)
        val = re.sub(r"tvly-[a-zA-Z0-9\-]{15,}", "tvly-********", val)
        return val


def setup_logging() -> None:
    """
    Configures standard Python logging for the backend application.
    Integrates with development settings, formats logs, and applies secret masking.
    """
    secrets_to_mask = []
    log_level = "INFO"
    is_dev = True
    
    try:
        from app.core.config import settings
        
        # Collect secrets from loaded configuration
        for key in ["OPENAI_API_KEY", "TAVILY_API_KEY", "QDRANT_API_KEY"]:
            val = getattr(settings, key, None)
            if val:
                if hasattr(val, "get_secret_value"):
                    secrets_to_mask.append(val.get_secret_value())
                else:
                    secrets_to_mask.append(str(val))
                    
        is_dev = settings.ENV == "development"
    except Exception:
        # Graceful fallback if settings module fails to load or is not yet initialized
        pass

    # Check environment override for log level
    env_log_level = os.getenv("LOG_LEVEL")
    if env_log_level:
        log_level = env_log_level.upper()
    else:
        log_level = "DEBUG" if is_dev else "INFO"

    # Assign appropriate formatter
    if is_dev:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        formatter = JSONFormatter()

    mask_filter = SecretMaskingFilter(secrets=secrets_to_mask)

    # Configure root logger
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level, logging.INFO)
    root_logger.setLevel(numeric_level)

    # Clean existing handlers and register new standard stream handler
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(mask_filter)
    root_logger.addHandler(console_handler)

    # Apply the mask filter to common external libraries/servers
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy"]:
        logger = logging.getLogger(logger_name)
        logger.addFilter(mask_filter)
        for handler in logger.handlers:
            handler.addFilter(mask_filter)
