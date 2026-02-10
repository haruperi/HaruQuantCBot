"""
Trading-related exception classes for the HQT trading system.

This module provides exceptions for trading operations, order management,
margin calculations, and position handling.
"""

from typing import Any

from .base import HQTBaseError


class TradingError(HQTBaseError):
    """
    Base class for all trading-related errors.

    This is the parent exception for all trading operations,
    order management, and position handling errors.

    Example:
        ```python
        raise TradingError(
            error_code="TRD-000",
            module="trading.engine",
            message="Trading operation failed"
        )
        ```
    """

    def __init__(self, error_code: str, module: str, message: str, **context: Any) -> None:
        super().__init__(error_code=error_code, module=module, message=message, **context)


class OrderError(TradingError):
    """
    Raised when order operations fail.

    This exception covers order placement, modification, cancellation,
    and validation failures.

    Additional Context Fields:
        order_id: Order identifier
        symbol: Trading symbol
        order_type: Type of order (market, limit, stop, etc.)
        volume: Order volume
        price: Order price (if applicable)
        reason: Specific failure reason

    Example:
        ```python
        raise OrderError(
            error_code="TRD-001",
            module="trading.orders",
            message="Invalid order volume",
            order_id="ORD-12345",
            symbol="EURUSD",
            order_type="market",
            volume=-1.0,
            reason="Volume must be positive"
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        order_id: str | int | None = None,
        symbol: str | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            order_id=order_id,
            symbol=symbol,
            **context,
        )


class MarginError(TradingError):
    """
    Raised when margin requirements are not met.

    This exception indicates insufficient margin for trading operations,
    margin calculation errors, or margin requirement violations.

    Additional Context Fields:
        required_margin: Margin required for operation
        available_margin: Available free margin
        account_equity: Current account equity
        margin_level: Current margin level percentage
        operation: The operation that triggered the error

    Example:
        ```python
        raise MarginError(
            error_code="TRD-002",
            module="trading.margin",
            message="Insufficient margin for order",
            required_margin=1000.0,
            available_margin=500.0,
            account_equity=5000.0,
            margin_level=120.0
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        required_margin: float | None = None,
        available_margin: float | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            required_margin=required_margin,
            available_margin=available_margin,
            **context,
        )


class StopOutError(TradingError):
    """
    Raised when stop-out conditions are triggered.

    This exception indicates that the account has reached stop-out level
    and positions are being automatically closed by margin requirements.

    Additional Context Fields:
        margin_level: Current margin level percentage
        stop_out_level: Stop-out threshold level
        positions_closed: Number of positions closed
        closed_position_ids: List of position IDs that were closed
        remaining_equity: Equity after stop-out

    Example:
        ```python
        raise StopOutError(
            error_code="TRD-003",
            module="trading.margin",
            message="Stop-out triggered: margin level below threshold",
            margin_level=15.0,
            stop_out_level=20.0,
            positions_closed=3,
            closed_position_ids=["POS-001", "POS-002", "POS-003"]
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        margin_level: float | None = None,
        stop_out_level: float | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            margin_level=margin_level,
            stop_out_level=stop_out_level,
            **context,
        )
