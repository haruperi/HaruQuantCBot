"""
Comprehensive tests for the HQT logging system.

Tests cover configuration, handlers, formatters, filters, and redaction.
"""

import json
import logging
import tempfile
from pathlib import Path

import pytest

from hqt.foundation.logging import (
    ConsoleFormatter,
    FileFormatter,
    JsonFileHandler,
    JsonFormatter,
    KeywordFilter,
    LevelRangeFilter,
    ModuleFilter,
    RedactionFilter,
    RotatingFileHandlerWrapper,
    ThrottleFilter,
    add_redaction_pattern,
    get_logger,
    set_log_level,
    setup_logging,
)


class TestLoggingConfiguration:
    """Tests for logging configuration."""

    def test_setup_logging_default(self, tmp_path):
        """Test setup_logging with default configuration."""
        setup_logging(log_dir=tmp_path)

        logger = get_logger("hqt.test")
        # Logger inherits from parent, effective level should be DEBUG
        assert logger.getEffectiveLevel() == logging.DEBUG

    def test_setup_logging_custom(self, tmp_path):
        """Test setup_logging with custom configuration."""
        custom_config = {
            "version": 1,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                }
            },
            "loggers": {
                "test": {
                    "level": "WARNING",
                    "handlers": ["console"],
                }
            },
        }

        setup_logging(custom_config, log_dir=tmp_path)
        logger = get_logger("test")
        assert logger.level == logging.WARNING

    def test_get_logger(self):
        """Test get_logger returns a logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_set_log_level_string(self):
        """Test setting log level with string."""
        logger = get_logger("test.level.string")
        set_log_level("INFO", "test.level.string")
        assert logger.level == logging.INFO

    def test_set_log_level_int(self):
        """Test setting log level with integer."""
        logger = get_logger("test.level.int")
        set_log_level(logging.DEBUG, "test.level.int")
        assert logger.level == logging.DEBUG


class TestHandlers:
    """Tests for custom logging handlers."""

    def test_rotating_file_handler_creates_directory(self, tmp_path):
        """Test RotatingFileHandlerWrapper creates directories."""
        log_file = tmp_path / "subdir" / "test.log"
        handler = RotatingFileHandlerWrapper(
            filename=str(log_file),
            maxBytes=1024,
            backupCount=3,
        )

        assert log_file.parent.exists()
        handler.close()

    def test_rotating_file_handler_writes(self, tmp_path):
        """Test RotatingFileHandlerWrapper writes logs."""
        log_file = tmp_path / "test.log"
        handler = RotatingFileHandlerWrapper(filename=str(log_file))
        handler.setFormatter(logging.Formatter("%(message)s"))

        logger = logging.getLogger("test.rotating")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        logger.info("Test message")
        handler.flush()
        handler.close()

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_json_file_handler_writes_json(self, tmp_path):
        """Test JsonFileHandler writes valid JSON."""
        log_file = tmp_path / "test.json"
        handler = JsonFileHandler(filename=str(log_file))

        # Need to set a formatter for timestamp formatting
        handler.setFormatter(JsonFormatter())

        logger = logging.getLogger("test.json")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        logger.info("Test JSON message", extra={"user_id": 123})
        handler.flush()
        handler.close()

        assert log_file.exists()
        content = log_file.read_text().strip()

        # Parse JSON
        log_data = json.loads(content)
        assert log_data["message"] == "Test JSON message"
        assert log_data["level"] == "INFO"
        assert log_data["user_id"] == 123


class TestFormatters:
    """Tests for custom formatters."""

    def test_console_formatter_without_colors(self):
        """Test ConsoleFormatter with colors disabled."""
        formatter = ConsoleFormatter(
            fmt="%(levelname)s - %(message)s",
            use_colors=False,
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "INFO - Test message" in formatted
        assert "\033[" not in formatted  # No ANSI codes

    def test_console_formatter_with_colors(self):
        """Test ConsoleFormatter with colors enabled."""
        formatter = ConsoleFormatter(
            fmt="%(levelname)s - %(message)s",
            use_colors=True,
        )

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "ERROR" in formatted
        assert "\033[" in formatted  # Contains ANSI codes

    def test_file_formatter_precision(self):
        """Test FileFormatter includes milliseconds."""
        formatter = FileFormatter(fmt="%(asctime)s - %(message)s")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.created = 1704110400.123  # Fixed timestamp
        record.msecs = (record.created % 1) * 1000  # Set msecs explicitly

        formatted = formatter.format(record)
        # Check that milliseconds are included (any 3-digit number after dot)
        import re
        assert re.search(r"\.\d{3}", formatted), "Milliseconds should be included"

    def test_json_formatter_structure(self):
        """Test JsonFormatter creates proper structure."""
        formatter = JsonFormatter()

        record = logging.LogRecord(
            name="test.module",
            level=logging.WARNING,
            pathname="/path/test.py",
            lineno=42,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["level"] == "WARNING"
        assert data["logger"] == "test.module"
        assert data["message"] == "Warning message"
        assert data["line"] == 42
        assert data["function"] == "test_function"


class TestFilters:
    """Tests for custom filters."""

    def test_module_filter_allow(self):
        """Test ModuleFilter with allow patterns."""
        filter_obj = ModuleFilter(allow=["hqt.trading.*"], block=[])

        # Should allow
        record_allow = logging.LogRecord(
            name="hqt.trading.orders",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record_allow) is True

        # Should block
        record_block = logging.LogRecord(
            name="hqt.data.providers",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record_block) is False

    def test_module_filter_block(self):
        """Test ModuleFilter with block patterns."""
        filter_obj = ModuleFilter(allow=[], block=["hqt.debug.*"])

        # Should allow
        record_allow = logging.LogRecord(
            name="hqt.trading",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record_allow) is True

        # Should block
        record_block = logging.LogRecord(
            name="hqt.debug.verbose",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record_block) is False

    def test_level_range_filter(self):
        """Test LevelRangeFilter."""
        filter_obj = LevelRangeFilter(
            min_level=logging.WARNING,
            max_level=logging.ERROR,
        )

        # Below range
        record_debug = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record_debug) is False

        # In range
        record_warning = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record_warning) is True

        # Above range
        record_critical = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record_critical) is False

    def test_keyword_filter_allow(self):
        """Test KeywordFilter in allow mode."""
        filter_obj = KeywordFilter(
            keywords=["order", "trade"],
            mode="allow",
            case_sensitive=False,
        )

        # Contains keyword
        record_match = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Order executed successfully",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record_match) is True

        # No keyword
        record_no_match = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="System started",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record_no_match) is False

    def test_keyword_filter_block(self):
        """Test KeywordFilter in block mode."""
        filter_obj = KeywordFilter(
            keywords=["debug", "verbose"],
            mode="block",
            case_sensitive=False,
        )

        # Contains keyword (blocked)
        record_match = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Debug information",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record_match) is False

        # No keyword (allowed)
        record_no_match = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Normal message",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record_no_match) is True

    def test_throttle_filter(self):
        """Test ThrottleFilter suppresses duplicates."""
        filter_obj = ThrottleFilter(window_seconds=1.0)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Repeated message",
            args=(),
            exc_info=None,
        )

        # First message should pass
        assert filter_obj.filter(record) is True

        # Immediate duplicate should be blocked
        assert filter_obj.filter(record) is False


class TestRedaction:
    """Tests for sensitive data redaction."""

    def test_redaction_filter_api_key(self):
        """Test RedactionFilter masks API keys."""
        filter_obj = RedactionFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Connecting with api_key=sk-1234567890abcdefghij",
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)
        assert "[REDACTED]" in record.msg
        assert "sk-1234567890abcdefghij" not in record.msg

    def test_redaction_filter_password(self):
        """Test RedactionFilter masks passwords."""
        filter_obj = RedactionFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Login with password: mysecretpass123",
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)
        assert "[REDACTED]" in record.msg
        assert "mysecretpass123" not in record.msg

    def test_redaction_filter_extra_fields(self):
        """Test RedactionFilter masks extra fields."""
        filter_obj = RedactionFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="User logged in",
            args=(),
            exc_info=None,
        )
        record.api_key = "sk-secret123"
        record.password = "mypassword"

        filter_obj.filter(record)
        assert record.api_key == "[REDACTED]"
        assert record.password == "[REDACTED]"

    def test_add_redaction_pattern(self):
        """Test adding custom redaction patterns."""
        filter_obj = RedactionFilter()
        add_redaction_pattern(filter_obj, "custom_id", r"ID-\d{10}")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="User ID-1234567890 logged in",
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)
        assert "[REDACTED]" in record.msg
        assert "ID-1234567890" not in record.msg

    def test_redaction_filter_jwt(self):
        """Test RedactionFilter masks JWT tokens."""
        filter_obj = RedactionFilter()

        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"Token: {jwt_token}",
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)
        assert "[REDACTED]" in record.msg
        assert jwt_token not in record.msg
