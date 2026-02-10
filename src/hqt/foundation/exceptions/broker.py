"""
Broker-related exception classes for the HQT trading system.

This module provides exceptions for broker connectivity, communication,
and broker-specific error conditions.
"""

from typing import Any

from .base import HQTBaseError


class BrokerError(HQTBaseError):
    """
    Base class for all broker-related errors.

    This is the parent exception for all broker connectivity,
    communication, and broker-specific errors.

    Example:
        ```python
        raise BrokerError(
            error_code="BRK-000",
            module="broker.gateway",
            message="Broker operation failed"
        )
        ```
    """

    def __init__(self, error_code: str, module: str, message: str, **context: Any) -> None:
        super().__init__(error_code=error_code, module=module, message=message, **context)


class ConnectionError(BrokerError):
    """
    Raised when broker connection fails or is lost.

    This exception indicates connectivity issues with the broker,
    including initial connection failures and lost connections.

    Additional Context Fields:
        broker: Broker name/identifier
        endpoint: Connection endpoint (host:port)
        retry_count: Number of retry attempts made
        last_error: Last underlying error message
        connection_state: Current connection state

    Example:
        ```python
        raise ConnectionError(
            error_code="BRK-001",
            module="broker.mt5",
            message="Failed to connect to MT5 terminal",
            broker="MT5",
            endpoint="localhost:5555",
            retry_count=3,
            last_error="Connection refused"
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        broker: str | None = None,
        endpoint: str | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            broker=broker,
            endpoint=endpoint,
            **context,
        )


class TimeoutError(BrokerError):
    """
    Raised when broker operations time out.

    This exception indicates that a broker operation exceeded
    the allowed time limit without completing.

    Additional Context Fields:
        operation: The operation that timed out
        timeout_seconds: Timeout threshold in seconds
        elapsed_seconds: Actual elapsed time
        broker: Broker name/identifier

    Example:
        ```python
        raise TimeoutError(
            error_code="BRK-002",
            module="broker.gateway",
            message="Order placement timed out",
            operation="place_order",
            timeout_seconds=30.0,
            elapsed_seconds=35.2,
            broker="MT5"
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        operation: str | None = None,
        timeout_seconds: float | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            operation=operation,
            timeout_seconds=timeout_seconds,
            **context,
        )


class ReconnectError(BrokerError):
    """
    Raised when broker reconnection attempts fail.

    This exception indicates that automatic reconnection attempts
    have been exhausted without successfully re-establishing the connection.

    Additional Context Fields:
        broker: Broker name/identifier
        attempts: Total reconnection attempts made
        max_attempts: Maximum allowed attempts
        backoff_seconds: Current backoff delay
        last_error: Error from the last attempt
        disconnect_time: When the connection was lost

    Example:
        ```python
        raise ReconnectError(
            error_code="BRK-003",
            module="broker.gateway",
            message="Failed to reconnect after 5 attempts",
            broker="MT5",
            attempts=5,
            max_attempts=5,
            backoff_seconds=32.0,
            last_error="Connection refused"
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        broker: str | None = None,
        attempts: int | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            broker=broker,
            attempts=attempts,
            **context,
        )
