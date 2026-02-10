"""
HQT Trading System Logging Framework.

This module provides a comprehensive logging system with:
- Rotating file handlers with automatic directory creation
- JSON structured logging
- Colored console output
- Flexible filtering (module, level, keyword)
- Automatic redaction of sensitive data
- C++ spdlog bridge (Phase 3)

Quick Start:
    ```python
    from hqt.foundation.logging import setup_logging, get_logger

    # Setup logging (call once at application start)
    setup_logging()

    # Get a logger
    logger = get_logger(__name__)

    # Use it
    logger.info("Application started")
    logger.debug("Debug info", extra={"user_id": 123})
    ```

Advanced Usage:
    ```python
    from hqt.foundation.logging import (
        setup_logging,
        get_logger,
        ConsoleFormatter,
        RedactionFilter,
    )

    # Custom configuration
    custom_config = {
        "version": 1,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "filters": ["redactor"],
            }
        },
        # ... more config
    }
    setup_logging(custom_config)
    ```
"""

# Configuration
from .config import (
    DEFAULT_LOG_CONFIG,
    get_logger,
    set_log_level,
    setup_logging,
    shutdown_logging,
)

# Filters
from .filters import KeywordFilter, LevelRangeFilter, ModuleFilter, ThrottleFilter

# Formatters
from .formatters import ConsoleFormatter, FileFormatter, JsonFormatter

# Handlers
from .handlers import (
    JsonFileHandler,
    RotatingFileHandlerWrapper,
    SpdlogBridgeHandler,
)

# Redaction
from .redactor import RedactionFilter, add_redaction_pattern

__all__ = [
    # Configuration
    "setup_logging",
    "get_logger",
    "set_log_level",
    "shutdown_logging",
    "DEFAULT_LOG_CONFIG",
    # Formatters
    "ConsoleFormatter",
    "FileFormatter",
    "JsonFormatter",
    # Handlers
    "RotatingFileHandlerWrapper",
    "JsonFileHandler",
    "SpdlogBridgeHandler",
    # Filters
    "ModuleFilter",
    "LevelRangeFilter",
    "KeywordFilter",
    "ThrottleFilter",
    # Redaction
    "RedactionFilter",
    "add_redaction_pattern",
]
