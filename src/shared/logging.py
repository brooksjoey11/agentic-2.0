"""
Structured Logging Configuration
Provides consistent logging format across all services.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any

from .correlation import CorrelationIdFilter


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs:
    {
        "timestamp": "2024-01-01T00:00:00.000Z",
        "level": "INFO",
        "service": "orchestrator",
        "correlation_id": "abc-123",
        "message": "...",
        "extra_field": "..."
    }
    """
    
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add correlation ID if available
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        
        # Add message
        if record.msg:
            log_entry["message"] = record.getMessage()
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add any extra attributes
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text",
                          "filename", "funcName", "id", "levelname", "levelno",
                          "lineno", "module", "msecs", "message", "msg",
                          "name", "pathname", "process", "processName",
                          "relativeCreated", "stack_info", "thread", "threadName"]:
                log_entry[key] = value
        
        return json.dumps(log_entry)


def configure_logging(service_name: str, log_level: str = "INFO"):
    """
    Configure structured logging for a service.
    
    Args:
        service_name: Name of the service (orchestrator, agent, etc.)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Remove any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set level
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JsonFormatter(service_name))
    
    # Add correlation ID filter
    console_handler.addFilter(CorrelationIdFilter())
    
    root_logger.addHandler(console_handler)
    
    # Disable noisy third-party loggers
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
    logging.getLogger("aiormq").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured for {service_name} at level {log_level}")
