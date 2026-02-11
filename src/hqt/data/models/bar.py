"""
Bar (OHLCV) data model for HQT Trading System.

This module defines the Bar data structure representing aggregated price
data over a time period (candlestick/OHLCV bar), and the Timeframe enum
for standard trading timeframes.

[REQ: DAT-FR-002] Bar data model with OHLCV data and timeframe specification.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Timeframe(str, Enum):
    """
    Standard trading timeframes.

    Each timeframe is represented by its duration in minutes.
    This allows for easy arithmetic operations and comparison.

    Attributes:
        M1: 1-minute bars
        M5: 5-minute bars
        M15: 15-minute bars
        M30: 30-minute bars
        H1: 1-hour bars (60 minutes)
        H4: 4-hour bars (240 minutes)
        D1: Daily bars (1440 minutes)
        W1: Weekly bars (10080 minutes)
        MN1: Monthly bars (43200 minutes, approximate)

    Example:
        ```python
        tf = Timeframe.H1
        print(tf.minutes)  # 60
        print(tf.name)     # "H1"
        print(tf.value)    # "H1"
        ```
    """

    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"

    @property
    def minutes(self) -> int:
        """Return the timeframe duration in minutes."""
        return _TIMEFRAME_MINUTES[self]

    @property
    def seconds(self) -> int:
        """Return the timeframe duration in seconds."""
        return self.minutes * 60

    def __lt__(self, other: "Timeframe") -> bool:
        """Compare timeframes by their duration."""
        if not isinstance(other, Timeframe):
            return NotImplemented
        return self.minutes < other.minutes

    def __le__(self, other: "Timeframe") -> bool:
        """Compare timeframes by their duration."""
        if not isinstance(other, Timeframe):
            return NotImplemented
        return self.minutes <= other.minutes

    def __gt__(self, other: "Timeframe") -> bool:
        """Compare timeframes by their duration."""
        if not isinstance(other, Timeframe):
            return NotImplemented
        return self.minutes > other.minutes

    def __ge__(self, other: "Timeframe") -> bool:
        """Compare timeframes by their duration."""
        if not isinstance(other, Timeframe):
            return NotImplemented
        return self.minutes >= other.minutes


# Timeframe duration mapping in minutes
_TIMEFRAME_MINUTES: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 5,
    Timeframe.M15: 15,
    Timeframe.M30: 30,
    Timeframe.H1: 60,
    Timeframe.H4: 240,
    Timeframe.D1: 1440,
    Timeframe.W1: 10080,
    Timeframe.MN1: 43200,  # Approximate (30 days)
}


class Bar(BaseModel):
    """
    Represents an OHLCV (candlestick) bar.

    A bar aggregates tick data over a specific timeframe, capturing the
    open, high, low, and close prices along with volume information.

    All prices are stored as floating-point values. For high-performance
    C++ engine integration, these will be converted to fixed-point int64
    values using NumPy dtypes.

    Attributes:
        symbol: Trading symbol (e.g., "EURUSD", "XAUUSD")
        timeframe: Bar timeframe (M1, M5, H1, etc.)
        timestamp: UTC timestamp of bar open in microseconds since epoch
        open: Opening price of the period
        high: Highest price during the period
        low: Lowest price during the period
        close: Closing price of the period
        tick_volume: Number of price changes (ticks) during the period
        real_volume: Actual traded volume (if available, otherwise 0)
        spread: Average spread during the period (optional)

    Example:
        ```python
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,  # 2024-01-01 00:00:00 UTC
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
            tick_volume=15234,
            real_volume=125000000.0,
            spread=0.00003,
        )
        ```

    Validation:
        - high must be >= max(open, close)
        - low must be <= min(open, close)
        - All prices must be positive
        - timestamp must be positive
    """

    model_config = ConfigDict(
        frozen=True,  # Make instances immutable
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    symbol: str = Field(..., min_length=1, description="Trading symbol")
    timeframe: Timeframe = Field(..., description="Bar timeframe")
    timestamp: int = Field(..., gt=0, description="UTC timestamp in microseconds since epoch")
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="Highest price")
    low: float = Field(..., gt=0, description="Lowest price")
    close: float = Field(..., gt=0, description="Closing price")
    tick_volume: int = Field(default=0, ge=0, description="Number of ticks")
    real_volume: float = Field(default=0.0, ge=0, description="Actual traded volume")
    spread: float = Field(default=0.0, ge=0, description="Average spread")

    @model_validator(mode="after")
    def validate_ohlc(self) -> "Bar":
        """Validate OHLC relationships after all fields are set."""
        # Validate high >= max(open, close)
        max_price = max(self.open, self.close)
        if self.high < max_price:
            raise ValueError(
                f"high ({self.high}) must be >= max(open, close) ({max_price})"
            )

        # Validate low <= min(open, close)
        min_price = min(self.open, self.close)
        if self.low > min_price:
            raise ValueError(
                f"low ({self.low}) must be <= min(open, close) ({min_price})"
            )

        return self

    @property
    def datetime(self) -> datetime:
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(self.timestamp / 1_000_000.0)

    @property
    def range(self) -> float:
        """Calculate bar range (high - low)."""
        return self.high - self.low

    @property
    def body(self) -> float:
        """Calculate bar body size (abs(close - open))."""
        return abs(self.close - self.open)

    @property
    def upper_wick(self) -> float:
        """Calculate upper wick size."""
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        """Calculate lower wick size."""
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        """Check if bar is bullish (close > open)."""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Check if bar is bearish (close < open)."""
        return self.close < self.open

    @property
    def is_doji(self) -> bool:
        """Check if bar is a doji (open == close)."""
        return self.open == self.close

    def to_dict(self) -> dict[str, Any]:
        """
        Convert bar to dictionary representation.

        Returns:
            Dictionary with all bar fields.
        """
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe.value,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "tick_volume": self.tick_volume,
            "real_volume": self.real_volume,
            "spread": self.spread,
        }

    def __repr__(self) -> str:
        """Return string representation of the bar."""
        return (
            f"Bar(symbol={self.symbol!r}, timeframe={self.timeframe.value}, "
            f"timestamp={self.timestamp}, OHLC=[{self.open:.5f}, {self.high:.5f}, "
            f"{self.low:.5f}, {self.close:.5f}])"
        )

    @classmethod
    def from_mt5(
        cls,
        mt5_bar: Any,
        symbol: str,
        timeframe: Timeframe | str,
    ) -> "Bar":
        """
        Create a Bar from MetaTrader 5 bar/rate data.

        MT5 bar structure (from MetaTrader5 package):
        - time: int (seconds since epoch, bar open time)
        - open: float
        - high: float
        - low: float
        - close: float
        - tick_volume: int (number of ticks)
        - spread: int (spread in points)
        - real_volume: int (real traded volume)

        Args:
            mt5_bar: MT5 bar object (namedtuple from MetaTrader5.copy_rates_*)
            symbol: Symbol name
            timeframe: Timeframe enum or string

        Returns:
            Bar instance

        Example:
            ```python
            import MetaTrader5 as mt5
            from datetime import datetime

            mt5.initialize()
            rates = mt5.copy_rates_from("EURUSD", mt5.TIMEFRAME_H1, datetime(2024, 1, 1), 100)

            bar = Bar.from_mt5(rates[0], symbol="EURUSD", timeframe=Timeframe.H1)
            print(bar.open, bar.high, bar.low, bar.close)
            ```
        """
        # Convert timeframe string to enum if needed
        if isinstance(timeframe, str):
            timeframe = Timeframe(timeframe)

        # Convert timestamp from seconds to microseconds
        timestamp_us = mt5_bar.time * 1_000_000

        # Get OHLC prices
        open_price = float(mt5_bar.open)
        high_price = float(mt5_bar.high)
        low_price = float(mt5_bar.low)
        close_price = float(mt5_bar.close)

        # Get volumes
        tick_volume = int(mt5_bar.tick_volume) if hasattr(mt5_bar, "tick_volume") else 0
        real_volume = float(mt5_bar.real_volume) if hasattr(mt5_bar, "real_volume") else 0.0

        # Get spread (in points, need to convert to price if needed)
        # For now, store as-is since we don't have digit information here
        spread = float(mt5_bar.spread) if hasattr(mt5_bar, "spread") else 0.0

        return cls(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp_us,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            tick_volume=tick_volume,
            real_volume=real_volume,
            spread=spread,
        )


def create_bar(
    symbol: str,
    timeframe: Timeframe | str,
    timestamp: int | datetime,
    open: float,
    high: float,
    low: float,
    close: float,
    tick_volume: int = 0,
    real_volume: float = 0.0,
    spread: float = 0.0,
) -> Bar:
    """
    Factory function to create a Bar instance.

    This is a convenience function that handles timestamp and timeframe
    conversion.

    Args:
        symbol: Trading symbol
        timeframe: Either Timeframe enum or string ("M1", "H1", etc.)
        timestamp: Either microseconds (int) or datetime object
        open: Opening price
        high: Highest price
        low: Lowest price
        close: Closing price
        tick_volume: Number of ticks (default: 0)
        real_volume: Actual volume (default: 0.0)
        spread: Average spread (default: 0.0)

    Returns:
        Validated Bar instance

    Example:
        ```python
        from datetime import datetime, timezone

        bar = create_bar(
            symbol="EURUSD",
            timeframe="H1",  # Can use string
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
            tick_volume=15234,
        )
        ```
    """
    # Convert timeframe string to enum if needed
    if isinstance(timeframe, str):
        timeframe = Timeframe(timeframe)

    # Convert datetime to microseconds if needed
    if isinstance(timestamp, datetime):
        timestamp_us = int(timestamp.timestamp() * 1_000_000)
    else:
        timestamp_us = timestamp

    return Bar(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp_us,
        open=open,
        high=high,
        low=low,
        close=close,
        tick_volume=tick_volume,
        real_volume=real_volume,
        spread=spread,
    )
