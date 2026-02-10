"""
Data-related exception classes for the HQT trading system.

This module provides exceptions for data handling, validation,
quality issues, and data pipeline errors.
"""

from typing import Any

from .base import HQTBaseError


class DataError(HQTBaseError):
    """
    Base class for all data-related errors.

    This is the parent exception for all data pipeline, validation,
    and quality issues in the system.

    Example:
        ```python
        raise DataError(
            error_code="DAT-000",
            module="data.pipeline",
            message="Data processing failed"
        )
        ```
    """

    def __init__(self, error_code: str, module: str, message: str, **context: Any) -> None:
        super().__init__(error_code=error_code, module=module, message=message, **context)


class ValidationError(DataError):
    """
    Raised when data fails validation checks.

    This exception is raised when data does not meet expected constraints,
    schemas, or business rules.

    Additional Context Fields:
        field: The field that failed validation
        value: The invalid value
        constraint: The constraint that was violated
        expected: Expected value or format

    Example:
        ```python
        raise ValidationError(
            error_code="DAT-001",
            module="data.validation",
            message="Price cannot be negative",
            field="price",
            value=-100.0,
            constraint="price > 0"
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        field: str | None = None,
        value: Any = None,
        constraint: str | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            field=field,
            value=value,
            constraint=constraint,
            **context,
        )


class PriceSanityError(DataError):
    """
    Raised when price data fails sanity checks.

    This exception indicates unrealistic or impossible price values,
    such as negative prices, zero prices where not allowed, or
    prices outside reasonable bounds.

    Additional Context Fields:
        symbol: Trading symbol
        timestamp: When the invalid price occurred
        bid: Bid price (if applicable)
        ask: Ask price (if applicable)
        price: The problematic price value
        reason: Specific reason for the sanity check failure

    Example:
        ```python
        raise PriceSanityError(
            error_code="DAT-002",
            module="data.validation",
            message="Bid price exceeds ask price",
            symbol="EURUSD",
            bid=1.1000,
            ask=1.0900,
            reason="bid > ask"
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        symbol: str | None = None,
        price: float | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            symbol=symbol,
            price=price,
            **context,
        )


class GapError(DataError):
    """
    Raised when data contains unexpected gaps in time series.

    This exception indicates missing data points or timestamps
    that violate continuity expectations.

    Additional Context Fields:
        symbol: Trading symbol
        expected_time: Expected timestamp
        actual_time: Actual next timestamp
        gap_size: Size of the gap (e.g., in seconds)
        timeframe: Timeframe of the data

    Example:
        ```python
        raise GapError(
            error_code="DAT-003",
            module="data.pipeline",
            message="Missing 2 hours of data",
            symbol="EURUSD",
            expected_time="2024-01-01T10:00:00Z",
            actual_time="2024-01-01T12:00:00Z",
            gap_size=7200
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        symbol: str | None = None,
        gap_size: int | float | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            symbol=symbol,
            gap_size=gap_size,
            **context,
        )


class DuplicateError(DataError):
    """
    Raised when duplicate data is detected where uniqueness is required.

    This exception indicates duplicate timestamps, duplicate bar data,
    or other violations of uniqueness constraints.

    Additional Context Fields:
        symbol: Trading symbol
        timestamp: Duplicate timestamp
        duplicate_count: Number of duplicates found
        key: The key that was duplicated

    Example:
        ```python
        raise DuplicateError(
            error_code="DAT-004",
            module="data.storage",
            message="Duplicate bar data detected",
            symbol="EURUSD",
            timestamp="2024-01-01T10:00:00Z",
            duplicate_count=3
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        key: str | None = None,
        duplicate_count: int | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            key=key,
            duplicate_count=duplicate_count,
            **context,
        )
