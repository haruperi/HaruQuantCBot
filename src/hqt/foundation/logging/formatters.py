"""
Custom logging formatters for the HQT trading system.

This module provides formatters for console output with colors,
file output with detailed context, and structured JSON output.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Level colors
    DEBUG = "\033[36m"  # Cyan
    INFO = "\033[32m"  # Green
    WARNING = "\033[33m"  # Yellow
    ERROR = "\033[31m"  # Red
    CRITICAL = "\033[35m\033[1m"  # Bold Magenta

    # Component colors
    TIMESTAMP = "\033[90m"  # Gray
    LOGGER = "\033[94m"  # Light Blue
    MESSAGE = "\033[0m"  # Default


class ConsoleFormatter(logging.Formatter):
    """
    Formatter that adds colors to console output.

    This formatter colorizes log levels and uses different colors for
    different components (timestamp, logger name, message) to improve
    readability in terminal output.

    Color support is automatically detected and disabled on non-TTY outputs
    (e.g., when piping to files).

    Example:
        ```python
        handler = logging.StreamHandler()
        handler.setFormatter(ConsoleFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ))
        ```
    """

    # Level to color mapping
    LEVEL_COLORS = {
        logging.DEBUG: Colors.DEBUG,
        logging.INFO: Colors.INFO,
        logging.WARNING: Colors.WARNING,
        logging.ERROR: Colors.ERROR,
        logging.CRITICAL: Colors.CRITICAL,
    }

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: str = "%",
        use_colors: bool | None = None,
    ) -> None:
        """
        Initialize the console formatter.

        Args:
            fmt: Log format string
            datefmt: Date format string
            style: Format style ('%', '{', or '$')
            use_colors: Force color usage (None = auto-detect TTY)
        """
        super().__init__(fmt, datefmt, style)

        # Auto-detect color support if not specified
        if use_colors is None:
            self.use_colors = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        else:
            self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with colors.

        Args:
            record: Log record to format

        Returns:
            Formatted and colorized log string
        """
        if not self.use_colors:
            return super().format(record)

        # Save original values
        levelname_orig = record.levelname
        msg_orig = record.msg

        # Colorize level name
        level_color = self.LEVEL_COLORS.get(record.levelno, "")
        record.levelname = f"{level_color}{record.levelname}{Colors.RESET}"

        # Format the record
        formatted = super().format(record)

        # Restore original values
        record.levelname = levelname_orig
        record.msg = msg_orig

        return formatted

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """
        Format timestamp with color.

        Args:
            record: Log record
            datefmt: Date format string

        Returns:
            Formatted and colorized timestamp
        """
        timestamp = super().formatTime(record, datefmt)
        if self.use_colors:
            return f"{Colors.TIMESTAMP}{timestamp}{Colors.RESET}"
        return timestamp


class FileFormatter(logging.Formatter):
    """
    Formatter for file output with detailed context.

    This formatter includes more detailed information suitable for log files:
    - Precise timestamps with milliseconds
    - Module and function information
    - Line numbers
    - Thread information (optional)

    Example:
        ```python
        handler = logging.FileHandler("app.log")
        handler.setFormatter(FileFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
        ))
        ```
    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: str = "%",
    ) -> None:
        """
        Initialize the file formatter.

        Args:
            fmt: Log format string
            datefmt: Date format string
            style: Format style ('%', '{', or '$')
        """
        super().__init__(fmt, datefmt, style)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """
        Format timestamp with millisecond precision.

        Args:
            record: Log record
            datefmt: Date format string

        Returns:
            Formatted timestamp with milliseconds
        """
        ct = datetime.fromtimestamp(record.created, tz=timezone.utc)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.strftime("%Y-%m-%d %H:%M:%S")
        return f"{s}.{int(record.msecs):03d}"


class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs log records as JSON objects.

    Each log record is formatted as a structured JSON object containing
    all relevant fields. Useful for log aggregation and analysis tools.

    Example:
        ```python
        handler = logging.FileHandler("app.json")
        handler.setFormatter(JsonFormatter())
        ```

    Output format:
        ```json
        {
            "timestamp": "2024-01-01T10:00:00.123Z",
            "level": "INFO",
            "logger": "hqt.trading",
            "message": "Order executed",
            "extra_field": "extra_value"
        }
        ```
    """

    def __init__(self, datefmt: str | None = None) -> None:
        """
        Initialize the JSON formatter.

        Args:
            datefmt: Date format string (default: ISO 8601)
        """
        super().__init__()
        self.datefmt = datefmt

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Build base log data
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Add process/thread info
        if record.processName:
            log_data["process"] = record.processName
        if record.threadName and record.threadName != "MainThread":
            log_data["thread"] = record.threadName

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

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
                "message",
            }:
                try:
                    # Only include JSON-serializable extra fields
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        return json.dumps(log_data, default=str)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """
        Format timestamp in ISO 8601 format.

        Args:
            record: Log record
            datefmt: Date format string (ignored, always uses ISO 8601)

        Returns:
            ISO 8601 formatted timestamp with timezone
        """
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.isoformat()
