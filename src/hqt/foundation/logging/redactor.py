"""
Redaction filter for sensitive data in logs.

This module provides a filter that automatically masks sensitive information
such as API keys, passwords, tokens, and other secrets in log messages.
"""

import logging
import re
from typing import Pattern


class RedactionFilter(logging.Filter):
    """
    Filter that redacts sensitive information from log records.

    This filter automatically identifies and masks sensitive data patterns
    in log messages before they are written. It protects:
    - API keys and tokens
    - Passwords and secrets
    - Credit card numbers
    - Email addresses (optional)
    - Custom patterns

    The filter searches both the log message and any extra fields added
    to the log record.

    Example:
        ```python
        from hqt.foundation.logging.redactor import RedactionFilter

        handler = logging.StreamHandler()
        handler.addFilter(RedactionFilter())

        logger.info("User logged in", extra={"api_key": "sk-1234567890"})
        # Output: "User logged in" with api_key shown as "[REDACTED]"
        ```
    """

    # Default patterns for sensitive data
    DEFAULT_PATTERNS: dict[str, str] = {
        # API keys (various formats)
        "api_key": r"(?i)(api[_-]?key|apikey)[\s:=\"']+([a-zA-Z0-9_\-]{20,})",
        "bearer_token": r"(?i)(bearer|token)[\s:=\"']+([a-zA-Z0-9_\-\.]{20,})",
        # Passwords
        "password": r"(?i)(password|passwd|pwd)[\s:=\"']+([^\s\"']{4,})",
        # Secrets
        "secret": r"(?i)(secret|private[_-]?key)[\s:=\"']+([a-zA-Z0-9_\-+/=]{20,})",
        # AWS keys
        "aws_key": r"(AKIA[0-9A-Z]{16})",
        "aws_secret": r"(?i)(aws[_-]?secret)[\s:=\"']+([a-zA-Z0-9+/]{40})",
        # Credit cards (basic pattern)
        "credit_card": r"\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b",
        # JWT tokens
        "jwt": r"\b(eyJ[a-zA-Z0-9_\-]*\.eyJ[a-zA-Z0-9_\-]*\.[a-zA-Z0-9_\-]*)\b",
        # Authorization headers
        "auth_header": r"(?i)(authorization)[\s:]+([^\s\"']+)",
    }

    # Fields in log records that should be checked for sensitive data
    SENSITIVE_FIELD_NAMES: set[str] = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "api_key",
        "apikey",
        "token",
        "auth",
        "authorization",
        "bearer",
        "private_key",
        "access_key",
        "secret_key",
        "credit_card",
        "card_number",
        "cvv",
        "ssn",
    }

    def __init__(
        self,
        patterns: dict[str, str] | None = None,
        additional_patterns: dict[str, str] | None = None,
        redaction_text: str = "[REDACTED]",
        redact_emails: bool = False,
    ) -> None:
        """
        Initialize the redaction filter.

        Args:
            patterns: Custom patterns dict (overrides defaults if provided)
            additional_patterns: Additional patterns to add to defaults
            redaction_text: Text to use for redacted values
            redact_emails: Whether to redact email addresses

        Example:
            ```python
            # Add custom pattern
            filter = RedactionFilter(
                additional_patterns={
                    "custom_secret": r"SECRET_[A-Z0-9]{10}"
                }
            )

            # Custom redaction text
            filter = RedactionFilter(redaction_text="***HIDDEN***")
            ```
        """
        super().__init__()

        self.redaction_text = redaction_text

        # Use provided patterns or defaults
        if patterns is not None:
            self.patterns = patterns
        else:
            self.patterns = self.DEFAULT_PATTERNS.copy()

        # Add additional patterns if provided
        if additional_patterns:
            self.patterns.update(additional_patterns)

        # Add email pattern if requested
        if redact_emails:
            self.patterns["email"] = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

        # Compile patterns for performance
        self.compiled_patterns: dict[str, Pattern[str]] = {
            name: re.compile(pattern) for name, pattern in self.patterns.items()
        }

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Redact sensitive information from the log record.

        Args:
            record: Log record to filter

        Returns:
            Always True (record is modified in place, not blocked)
        """
        # Redact the message
        if isinstance(record.msg, str):
            record.msg = self._redact_text(record.msg)

        # Redact arguments if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact_value(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact_value(arg) for arg in record.args)

        # Redact extra fields
        for key in list(record.__dict__.keys()):
            # Check if field name suggests sensitive data
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELD_NAMES):
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
                }:
                    record.__dict__[key] = self.redaction_text

        return True

    def _redact_text(self, text: str) -> str:
        """
        Redact sensitive patterns from text.

        Args:
            text: Text to redact

        Returns:
            Text with sensitive patterns replaced
        """
        for pattern in self.compiled_patterns.values():
            text = pattern.sub(lambda m: self._replace_match(m), text)
        return text

    def _replace_match(self, match: re.Match[str]) -> str:
        """
        Replace a pattern match with redacted text.

        Args:
            match: Regex match object

        Returns:
            Replacement string with redaction
        """
        # If the pattern has groups, keep the first group (usually the field name)
        # and redact the value
        if match.lastindex and match.lastindex >= 2:
            return f"{match.group(1)} {self.redaction_text}"
        return self.redaction_text

    def _redact_value(self, value: any) -> any:
        """
        Redact a value if it's a string, otherwise return as-is.

        Args:
            value: Value to potentially redact

        Returns:
            Redacted value if string, original value otherwise
        """
        if isinstance(value, str):
            return self._redact_text(value)
        elif isinstance(value, dict):
            return {k: self._redact_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return type(value)(self._redact_value(item) for item in value)
        return value


def add_redaction_pattern(filter_instance: RedactionFilter, name: str, pattern: str) -> None:
    """
    Add a new redaction pattern to an existing filter.

    Args:
        filter_instance: RedactionFilter instance to modify
        name: Name for the pattern
        pattern: Regex pattern to match

    Example:
        ```python
        filter = RedactionFilter()
        add_redaction_pattern(filter, "custom_id", r"ID-\\d{10}")
        ```
    """
    filter_instance.patterns[name] = pattern
    filter_instance.compiled_patterns[name] = re.compile(pattern)
