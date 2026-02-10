"""
Base exception classes for the HQT trading system.

This module provides the foundation exception hierarchy with standardized
error codes, module tracking, timestamps, and serialization support.
"""

from datetime import datetime, timezone
from typing import Any


class HQTBaseError(Exception):
    """
    Base exception class for all HQT system errors.

    All custom exceptions in the HQT system inherit from this base class,
    providing consistent error handling with error codes, module tracking,
    timestamps, and structured serialization.

    Attributes:
        error_code: Unique error code identifier (e.g., "DATA-001", "TRD-042")
        module: Module or component where the error originated
        timestamp: UTC timestamp when the error was created
        message: Human-readable error message
        context: Additional context data specific to the error type

    Example:
        ```python
        try:
            raise HQTBaseError(
                error_code="SYS-001",
                module="engine",
                message="System initialization failed"
            )
        except HQTBaseError as e:
            print(e.to_dict())
            # {'error_code': 'SYS-001', 'module': 'engine', ...}
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        **context: Any,
    ) -> None:
        """
        Initialize the base error.

        Args:
            error_code: Unique error code (e.g., "DATA-001")
            module: Module name where error occurred
            message: Human-readable error description
            **context: Additional context fields (stored as-is)
        """
        super().__init__(message)
        self.error_code = error_code
        self.module = module
        self.message = message
        self.timestamp = datetime.now(timezone.utc)
        self.context = context

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the exception to a dictionary for serialization.

        Returns:
            Dictionary containing all error fields including:
            - error_code: The error code
            - module: The module name
            - message: The error message
            - timestamp: ISO 8601 formatted timestamp
            - All additional context fields

        Example:
            ```python
            error = HQTBaseError("E001", "data", "Invalid data")
            error_dict = error.to_dict()
            # {'error_code': 'E001', 'module': 'data', ...}
            ```
        """
        return {
            "error_code": self.error_code,
            "module": self.module,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            **self.context,
        }

    def __str__(self) -> str:
        """
        Return a formatted string representation of the error.

        Returns:
            Formatted string: "[module] error_code: message"

        Example:
            ```python
            error = HQTBaseError("E001", "data", "Invalid input")
            str(error)  # "[data] E001: Invalid input"
            ```
        """
        return f"[{self.module}] {self.error_code}: {self.message}"

    def __repr__(self) -> str:
        """
        Return a detailed representation of the error.

        Returns:
            String representation suitable for debugging
        """
        context_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        if context_str:
            return (
                f"{self.__class__.__name__}("
                f"error_code={self.error_code!r}, "
                f"module={self.module!r}, "
                f"message={self.message!r}, "
                f"{context_str})"
            )
        return (
            f"{self.__class__.__name__}("
            f"error_code={self.error_code!r}, "
            f"module={self.module!r}, "
            f"message={self.message!r})"
        )
