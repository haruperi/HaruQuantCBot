"""
Logging configuration for the HQT trading system.

This module provides centralized logging configuration using Python's
logging.config.dictConfig() with support for multiple handlers, formatters,
and filters.
"""

import logging
import logging.config
from pathlib import Path
from typing import Any

# Default logging configuration
DEFAULT_LOG_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "()": "hqt.foundation.logging.formatters.ConsoleFormatter",
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "file": {
            "()": "hqt.foundation.logging.formatters.FileFormatter",
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            "()": "hqt.foundation.logging.formatters.JsonFormatter",
        },
    },
    "filters": {
        "redactor": {
            "()": "hqt.foundation.logging.redactor.RedactionFilter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "console",
            "filters": ["redactor"],
            "stream": "ext://sys.stdout",
        },
        "file": {
            "()": "hqt.foundation.logging.handlers.RotatingFileHandlerWrapper",
            "level": "DEBUG",
            "formatter": "file",
            "filters": ["redactor"],
            "filename": "logs/hqt.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "json_file": {
            "()": "hqt.foundation.logging.handlers.JsonFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filters": ["redactor"],
            "filename": "logs/hqt.json",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "hqt": {
            "level": "DEBUG",
            "handlers": ["console", "file", "json_file"],
            "propagate": False,
        },
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}


def setup_logging(config: dict[str, Any] | None = None, log_dir: str | Path = "logs") -> None:
    """
    Configure the logging system using dictConfig.

    This function sets up the logging system with the provided configuration
    or uses the default configuration. It ensures the log directory exists
    and configures all handlers, formatters, and filters.

    Args:
        config: Logging configuration dictionary compatible with logging.config.dictConfig().
            If None, uses DEFAULT_LOG_CONFIG.
        log_dir: Directory for log files. Created if it doesn't exist.

    Example:
        ```python
        # Use default configuration
        from hqt.foundation.logging import setup_logging
        setup_logging()

        # Use custom configuration
        custom_config = {
            "version": 1,
            "handlers": {...},
            "loggers": {...}
        }
        setup_logging(custom_config, log_dir="custom_logs")
        ```

    Note:
        - Console output level can be controlled via config
        - File handlers automatically rotate when size limit is reached
        - All sensitive data is automatically redacted
    """
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Use provided config or default
    if config is None:
        config = DEFAULT_LOG_CONFIG.copy()

    # Update file paths with log_dir
    for handler_config in config.get("handlers", {}).values():
        if "filename" in handler_config:
            filename = Path(handler_config["filename"])
            if not filename.is_absolute():
                handler_config["filename"] = str(log_path / filename.name)

    # Apply logging configuration
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    This is a convenience wrapper around logging.getLogger() that ensures
    the logger is properly configured according to the system's logging setup.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        Configured logger instance

    Example:
        ```python
        from hqt.foundation.logging import get_logger

        logger = get_logger(__name__)
        logger.info("Application started")
        logger.debug("Debug information", extra={"user_id": 123})
        ```
    """
    return logging.getLogger(name)


def set_log_level(level: str | int, logger_name: str | None = None) -> None:
    """
    Change the log level for a specific logger or the root logger.

    Args:
        level: Log level as string ("DEBUG", "INFO", etc.) or int (logging.DEBUG, etc.)
        logger_name: Name of the logger to modify. If None, modifies root logger.

    Example:
        ```python
        from hqt.foundation.logging import set_log_level

        # Set root logger to DEBUG
        set_log_level("DEBUG")

        # Set specific logger to INFO
        set_log_level("INFO", "hqt.trading")
        ```
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper())

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)


def shutdown_logging() -> None:
    """
    Shutdown the logging system gracefully.

    This function flushes all buffers and closes all file handles.
    Should be called before application exit.

    Example:
        ```python
        from hqt.foundation.logging import shutdown_logging
        import atexit

        # Register shutdown on exit
        atexit.register(shutdown_logging)
        ```
    """
    logging.shutdown()
