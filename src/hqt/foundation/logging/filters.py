"""
Custom logging filters for the HQT trading system.

This module provides filters for selective log record processing based on
module names, log levels, and keyword matching.
"""

import logging
import re
from typing import Pattern


class ModuleFilter(logging.Filter):
    """
    Filter log records by module name patterns.

    This filter allows or blocks log records based on whether their
    module name matches specified patterns. Useful for focusing logs
    on specific components or excluding verbose modules.

    Example:
        ```python
        # Only allow logs from trading modules
        filter = ModuleFilter(allow=["hqt.trading.*"], block=[])
        handler.addFilter(filter)

        # Block logs from a specific module
        filter = ModuleFilter(allow=[], block=["hqt.data.providers.mt5"])
        handler.addFilter(filter)
        ```
    """

    def __init__(self, allow: list[str] | None = None, block: list[str] | None = None) -> None:
        """
        Initialize the module filter.

        Args:
            allow: List of module name patterns to allow (glob-style with *)
            block: List of module name patterns to block (glob-style with *)

        Note:
            - If allow is empty, all modules are allowed by default
            - If both allow and block match, block takes precedence
            - Patterns use glob-style matching (* for any characters)
        """
        super().__init__()
        self.allow_patterns: list[Pattern[str]] = []
        self.block_patterns: list[Pattern[str]] = []

        # Convert glob patterns to regex
        if allow:
            for pattern in allow:
                regex = self._glob_to_regex(pattern)
                self.allow_patterns.append(re.compile(regex))

        if block:
            for pattern in block:
                regex = self._glob_to_regex(pattern)
                self.block_patterns.append(re.compile(regex))

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if the record should be logged.

        Args:
            record: Log record to filter

        Returns:
            True if record should be logged, False otherwise
        """
        module_name = record.name

        # Check if blocked
        for pattern in self.block_patterns:
            if pattern.match(module_name):
                return False

        # If no allow patterns, allow all (except blocked)
        if not self.allow_patterns:
            return True

        # Check if allowed
        for pattern in self.allow_patterns:
            if pattern.match(module_name):
                return True

        return False

    @staticmethod
    def _glob_to_regex(pattern: str) -> str:
        """
        Convert glob-style pattern to regex.

        Args:
            pattern: Glob pattern (e.g., "hqt.trading.*")

        Returns:
            Regex pattern string
        """
        # Escape special regex characters except *
        pattern = re.escape(pattern)
        # Convert escaped * back to regex .*
        pattern = pattern.replace(r"\*", ".*")
        # Add anchors
        return f"^{pattern}$"


class LevelRangeFilter(logging.Filter):
    """
    Filter log records by level range.

    This filter allows only log records within a specified level range.
    Useful for directing different log levels to different handlers.

    Example:
        ```python
        # Only WARNING and ERROR (not CRITICAL)
        filter = LevelRangeFilter(min_level=logging.WARNING, max_level=logging.ERROR)
        handler.addFilter(filter)

        # DEBUG and INFO only
        filter = LevelRangeFilter(min_level=logging.DEBUG, max_level=logging.INFO)
        handler.addFilter(filter)
        ```
    """

    def __init__(self, min_level: int = logging.DEBUG, max_level: int = logging.CRITICAL) -> None:
        """
        Initialize the level range filter.

        Args:
            min_level: Minimum log level (inclusive)
            max_level: Maximum log level (inclusive)
        """
        super().__init__()
        self.min_level = min_level
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if the record's level is within range.

        Args:
            record: Log record to filter

        Returns:
            True if record level is within range, False otherwise
        """
        return self.min_level <= record.levelno <= self.max_level


class KeywordFilter(logging.Filter):
    """
    Filter log records by keyword matching in messages.

    This filter allows or blocks log records based on whether their
    message contains specified keywords. Case-insensitive matching
    is supported.

    Example:
        ```python
        # Only log messages containing "order" or "trade"
        filter = KeywordFilter(
            keywords=["order", "trade"],
            mode="allow",
            case_sensitive=False
        )
        handler.addFilter(filter)

        # Block log messages containing sensitive terms
        filter = KeywordFilter(
            keywords=["password", "secret"],
            mode="block",
            case_sensitive=False
        )
        handler.addFilter(filter)
        ```
    """

    def __init__(
        self,
        keywords: list[str],
        mode: str = "allow",
        case_sensitive: bool = False,
    ) -> None:
        """
        Initialize the keyword filter.

        Args:
            keywords: List of keywords to match
            mode: Filter mode - "allow" or "block"
            case_sensitive: Whether keyword matching is case-sensitive

        Raises:
            ValueError: If mode is not "allow" or "block"
        """
        super().__init__()

        if mode not in ("allow", "block"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'allow' or 'block'")

        self.keywords = keywords if case_sensitive else [k.lower() for k in keywords]
        self.mode = mode
        self.case_sensitive = case_sensitive

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if the record matches keyword criteria.

        Args:
            record: Log record to filter

        Returns:
            True if record should be logged, False otherwise
        """
        message = record.getMessage()
        if not self.case_sensitive:
            message = message.lower()

        # Check if any keyword is in the message
        contains_keyword = any(keyword in message for keyword in self.keywords)

        if self.mode == "allow":
            return contains_keyword
        else:  # mode == "block"
            return not contains_keyword


class ThrottleFilter(logging.Filter):
    """
    Filter that throttles repeated log messages.

    This filter suppresses repeated identical log messages within a
    specified time window, preventing log spam while preserving the
    first occurrence of each message.

    Example:
        ```python
        # Suppress duplicate messages within 60 seconds
        filter = ThrottleFilter(window_seconds=60)
        handler.addFilter(filter)
        ```

    Note:
        The filter uses the message content as the deduplication key.
        Messages with different arguments are considered unique.
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        """
        Initialize the throttle filter.

        Args:
            window_seconds: Time window for deduplication in seconds
        """
        super().__init__()
        self.window_seconds = window_seconds
        self._message_times: dict[str, float] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if the record should be logged (not throttled).

        Args:
            record: Log record to filter

        Returns:
            True if record should be logged, False if throttled
        """
        import time

        current_time = time.time()
        message_key = f"{record.name}:{record.levelno}:{record.getMessage()}"

        # Check if we've seen this message recently
        if message_key in self._message_times:
            last_time = self._message_times[message_key]
            if current_time - last_time < self.window_seconds:
                # Throttle this message
                return False

        # Update the last seen time
        self._message_times[message_key] = current_time

        # Clean up old entries periodically
        if len(self._message_times) > 1000:
            cutoff_time = current_time - self.window_seconds
            self._message_times = {
                key: timestamp
                for key, timestamp in self._message_times.items()
                if timestamp >= cutoff_time
            }

        return True
