"""
Tick data model for HQT Trading System.

This module defines the Tick data structure representing a single market
tick (price update) with bid/ask quotes and volumes.

[REQ: DAT-FR-001] Tick data model with symbol, timestamp, bid, ask, volumes.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Tick(BaseModel):
    """
    Represents a single market tick with bid/ask quotes.

    A tick is the most granular level of market data, capturing the best
    bid and ask prices at a specific moment in time, along with their
    respective volumes.

    All prices are stored as floating-point values. For high-performance
    C++ engine integration, these will be converted to fixed-point int64
    values using NumPy dtypes.

    Attributes:
        symbol: Trading symbol (e.g., "EURUSD", "XAUUSD")
        timestamp: UTC timestamp in microseconds since epoch
        bid: Best bid price (must be positive)
        ask: Best ask price (must be positive and >= bid)
        bid_volume: Volume available at bid price (optional, default 0.0)
        ask_volume: Volume available at ask price (optional, default 0.0)
        spread: Spread in price points (ask - bid), computed automatically

    Example:
        ```python
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,  # 2024-01-01 00:00:00 UTC
            bid=1.10520,
            ask=1.10523,
            bid_volume=1000000.0,
            ask_volume=1500000.0,
        )
        print(tick.spread)  # 0.00003
        ```

    Validation:
        - bid must be positive
        - ask must be positive
        - ask must be >= bid
        - timestamp must be positive
    """

    model_config = ConfigDict(
        frozen=True,  # Make instances immutable
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    symbol: str = Field(..., min_length=1, description="Trading symbol")
    timestamp: int = Field(..., gt=0, description="UTC timestamp in microseconds since epoch")
    bid: float = Field(..., gt=0, description="Best bid price")
    ask: float = Field(..., gt=0, description="Best ask price")
    bid_volume: float = Field(default=0.0, ge=0, description="Volume at bid price")
    ask_volume: float = Field(default=0.0, ge=0, description="Volume at ask price")

    @field_validator("ask")
    @classmethod
    def validate_ask_gte_bid(cls, ask: float, info) -> float:
        """Validate that ask price is greater than or equal to bid price."""
        # Access bid from the validation context
        if "bid" in info.data:
            bid = info.data["bid"]
            if ask < bid:
                raise ValueError(f"ask ({ask}) must be >= bid ({bid})")
        return ask

    @property
    def spread(self) -> float:
        """Calculate spread as ask - bid."""
        return self.ask - self.bid

    @property
    def mid_price(self) -> float:
        """Calculate mid price as (bid + ask) / 2."""
        return (self.bid + self.ask) / 2.0

    @property
    def datetime(self) -> datetime:
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(self.timestamp / 1_000_000.0)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert tick to dictionary representation.

        Returns:
            Dictionary with all tick fields including computed spread.
        """
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "bid": self.bid,
            "ask": self.ask,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
            "spread": self.spread,
        }

    def __repr__(self) -> str:
        """Return string representation of the tick."""
        return (
            f"Tick(symbol={self.symbol!r}, timestamp={self.timestamp}, "
            f"bid={self.bid:.5f}, ask={self.ask:.5f}, spread={self.spread:.5f})"
        )

    @classmethod
    def from_mt5(cls, mt5_tick: Any, symbol: str | None = None) -> "Tick":
        """
        Create a Tick from MetaTrader 5 tick data.

        MT5 tick structure (from MetaTrader5 package):
        - time: int (seconds since epoch)
        - bid: float
        - ask: float
        - last: float (last deal price, optional)
        - volume: int (tick volume, optional)
        - time_msc: int (milliseconds since epoch, optional)
        - flags: int (tick flags, optional)
        - volume_real: float (real volume, optional)

        Args:
            mt5_tick: MT5 tick object (namedtuple from MetaTrader5.copy_ticks_*)
            symbol: Symbol name (required if not in mt5_tick)

        Returns:
            Tick instance

        Example:
            ```python
            import MetaTrader5 as mt5

            mt5.initialize()
            ticks = mt5.copy_ticks_from("EURUSD", datetime(2024, 1, 1), 100, mt5.COPY_TICKS_ALL)

            tick = Tick.from_mt5(ticks[0], symbol="EURUSD")
            print(tick.bid, tick.ask)
            ```

        Raises:
            ValueError: If symbol is not provided and not in mt5_tick
        """
        # Get symbol
        if symbol is None:
            if hasattr(mt5_tick, "symbol"):
                symbol = mt5_tick.symbol
            else:
                raise ValueError("symbol must be provided when mt5_tick has no symbol attribute")

        # Get timestamp (prefer time_msc if available, otherwise time in seconds)
        if hasattr(mt5_tick, "time_msc"):
            timestamp_us = mt5_tick.time_msc * 1000  # Convert ms to us
        else:
            timestamp_us = mt5_tick.time * 1_000_000  # Convert seconds to us

        # Get bid and ask
        bid = float(mt5_tick.bid)
        ask = float(mt5_tick.ask)

        # Get volumes (may not be available for all tick types)
        bid_volume = 0.0
        ask_volume = 0.0
        if hasattr(mt5_tick, "volume_real"):
            # Use real volume if available
            bid_volume = float(mt5_tick.volume_real) if mt5_tick.volume_real > 0 else 0.0
        elif hasattr(mt5_tick, "volume"):
            # Fall back to tick volume
            bid_volume = float(mt5_tick.volume) if mt5_tick.volume > 0 else 0.0

        return cls(
            symbol=symbol,
            timestamp=timestamp_us,
            bid=bid,
            ask=ask,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
        )


def create_tick(
    symbol: str,
    timestamp: int | datetime,
    bid: float,
    ask: float,
    bid_volume: float = 0.0,
    ask_volume: float = 0.0,
) -> Tick:
    """
    Factory function to create a Tick instance.

    This is a convenience function that handles timestamp conversion
    from datetime objects.

    Args:
        symbol: Trading symbol
        timestamp: Either microseconds (int) or datetime object
        bid: Bid price
        ask: Ask price
        bid_volume: Volume at bid (default: 0.0)
        ask_volume: Volume at ask (default: 0.0)

    Returns:
        Validated Tick instance

    Example:
        ```python
        from datetime import datetime, timezone

        # Using microseconds
        tick1 = create_tick("EURUSD", 1704067200000000, 1.10520, 1.10523)

        # Using datetime
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        tick2 = create_tick("EURUSD", dt, 1.10520, 1.10523)
        ```
    """
    if isinstance(timestamp, datetime):
        timestamp_us = int(timestamp.timestamp() * 1_000_000)
    else:
        timestamp_us = timestamp

    return Tick(
        symbol=symbol,
        timestamp=timestamp_us,
        bid=bid,
        ask=ask,
        bid_volume=bid_volume,
        ask_volume=ask_volume,
    )
