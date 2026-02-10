"""
Custom logging handlers for the HQT trading system.

This module provides specialized handlers for file rotation, JSON logging,
and bridging to the C++ spdlog library.
"""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class RotatingFileHandlerWrapper(RotatingFileHandler):
    """
    Wrapper around RotatingFileHandler with automatic directory creation.

    This handler extends the standard RotatingFileHandler to automatically
    create the directory structure for log files if it doesn't exist.

    Attributes:
        Inherits all attributes from logging.handlers.RotatingFileHandler

    Example:
        ```python
        handler = RotatingFileHandlerWrapper(
            filename="logs/app.log",
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        ```
    """

    def __init__(
        self,
        filename: str,
        mode: str = "a",
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: str | None = None,
        delay: bool = False,
    ) -> None:
        """
        Initialize the rotating file handler.

        Args:
            filename: Path to the log file
            mode: File opening mode (default: 'a' for append)
            maxBytes: Maximum file size before rotation (0 = no rotation)
            backupCount: Number of backup files to keep
            encoding: Text encoding (default: None = platform default)
            delay: Defer file opening until first emit() call
        """
        # Ensure directory exists
        log_path = Path(filename)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize parent class
        super().__init__(
            filename=filename,
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
        )


class JsonFileHandler(RotatingFileHandler):
    """
    Handler that writes log records as JSON objects to a file.

    Each log record is written as a single-line JSON object, making
    it easy to parse and analyze logs programmatically.

    Example:
        ```python
        handler = JsonFileHandler(
            filename="logs/app.json",
            maxBytes=10485760
        )
        logger.addHandler(handler)
        ```

    Output format:
        ```json
        {"timestamp": "2024-01-01T10:00:00Z", "level": "INFO", "logger": "hqt.trading", ...}
        ```
    """

    def __init__(
        self,
        filename: str,
        mode: str = "a",
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: str = "utf-8",
        delay: bool = False,
    ) -> None:
        """
        Initialize the JSON file handler.

        Args:
            filename: Path to the JSON log file
            mode: File opening mode (default: 'a' for append)
            maxBytes: Maximum file size before rotation
            backupCount: Number of backup files to keep
            encoding: Text encoding (default: 'utf-8')
            delay: Defer file opening until first emit() call
        """
        # Ensure directory exists
        log_path = Path(filename)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize parent class (no formatter needed, we format in emit())
        super().__init__(
            filename=filename,
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
        )

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record as a JSON object.

        Args:
            record: Log record to emit
        """
        try:
            # Build JSON object from record
            log_data: dict[str, Any] = {
                "timestamp": self.formatter.formatTime(record, self.formatter.datefmt)
                if self.formatter
                else self.format_time_default(record),
                "level": record.levelname,
                "logger": record.name,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "message": record.getMessage(),
            }

            # Add exception info if present
            if record.exc_info and not record.exc_text:
                record.exc_text = self.formatter.formatException(record.exc_info) if self.formatter else None

            if record.exc_text:
                log_data["exception"] = record.exc_text

            # Add extra fields
            for key, value in record.__dict__.items():
                if key not in {
                    "name",
                    "msg",
                    "args",
                    "created",
                    "msecs",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "processName",
                    "process",
                    "threadName",
                    "thread",
                    "relativeCreated",
                    "getMessage",
                }:
                    log_data[key] = value

            # Write JSON line
            json_line = json.dumps(log_data, default=str)
            self.stream.write(json_line + "\n")
            self.flush()

        except Exception:
            self.handleError(record)

    def format_time_default(self, record: logging.LogRecord) -> str:
        """Format timestamp in ISO 8601 format."""
        from datetime import datetime, timezone

        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.isoformat()


class SpdlogBridgeHandler(logging.Handler):
    """
    Handler that bridges Python logging to C++ spdlog.

    This is a placeholder handler that will be implemented in Phase 3
    when the C++ engine is integrated. It will forward Python log messages
    to the spdlog logging system in the C++ core.

    Note:
        Currently a no-op handler. Will be implemented with Nanobind bridge in Phase 3.

    Example:
        ```python
        # Will be functional in Phase 3
        handler = SpdlogBridgeHandler()
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        ```
    """

    def __init__(self, level: int = logging.NOTSET) -> None:
        """
        Initialize the spdlog bridge handler.

        Args:
            level: Logging level threshold
        """
        super().__init__(level)
        self._bridge_initialized = False

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to spdlog (placeholder).

        Args:
            record: Log record to emit

        Note:
            Implementation will be added in Phase 3 with C++ bridge.
        """
        # TODO: Phase 3 - Forward to C++ spdlog via Nanobind
        # For now, this is a no-op
        pass

    def initialize_bridge(self) -> bool:
        """
        Initialize the C++ spdlog bridge (placeholder).

        Returns:
            True if bridge initialized successfully

        Note:
            Implementation will be added in Phase 3.
        """
        # TODO: Phase 3 - Initialize Nanobind bridge to spdlog
        return False

    def close(self) -> None:
        """Close the handler and cleanup resources."""
        super().close()
        self._bridge_initialized = False
