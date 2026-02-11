"""
NumPy dtype definitions and conversion functions for HQT Trading System.

This module defines NumPy structured array dtypes that match the C++ core
engine data structures. It provides efficient conversion between Pydantic
models and NumPy arrays for high-performance processing.

The dtypes use fixed-point integer representation for prices to avoid
floating-point precision issues and to match the C++ implementation.

[REQ: DAT-FR-004] NumPy dtypes for C++ interoperability.
"""

from typing import Any, Sequence

import numpy as np
from numpy.typing import NDArray

from hqt.data.models.bar import Bar, Timeframe
from hqt.data.models.tick import Tick


# NumPy dtype for Tick data (matches C++ struct layout)
TICK_DTYPE = np.dtype(
    [
        ("timestamp", np.int64),  # Microseconds since epoch
        ("symbol_id", np.uint32),  # Symbol lookup index (0 for Python-only usage)
        ("bid", np.int64),  # Fixed-point: value × 10^digits
        ("ask", np.int64),  # Fixed-point: value × 10^digits
        ("bid_volume", np.int64),  # Volume at bid
        ("ask_volume", np.int64),  # Volume at ask
        ("spread_points", np.int32),  # Spread in points
    ],
    align=True,  # Align to C struct boundaries
)

# NumPy dtype for Bar data (matches C++ struct layout)
BAR_DTYPE = np.dtype(
    [
        ("timestamp", np.int64),  # Microseconds since epoch
        ("symbol_id", np.uint32),  # Symbol lookup index (0 for Python-only usage)
        ("open", np.int64),  # Fixed-point OHLC
        ("high", np.int64),
        ("low", np.int64),
        ("close", np.int64),
        ("tick_volume", np.int64),
        ("real_volume", np.int64),
        ("spread_points", np.int32),
        ("timeframe", np.uint16),  # Timeframe in minutes (uint16 to support D1=1440, W1=10080)
    ],
    align=True,  # Align to C struct boundaries
)


def price_to_fixed(price: float, digits: int) -> int:
    """
    Convert floating-point price to fixed-point integer.

    Args:
        price: Floating-point price value
        digits: Number of decimal digits (precision)

    Returns:
        Fixed-point integer representation

    Example:
        ```python
        # EURUSD with 5 digits
        fixed = price_to_fixed(1.10523, 5)
        # Returns: 110523

        # XAUUSD with 2 digits
        fixed = price_to_fixed(2350.50, 2)
        # Returns: 235050
        ```
    """
    multiplier = 10**digits
    return int(round(price * multiplier))


def fixed_to_price(fixed: int, digits: int) -> float:
    """
    Convert fixed-point integer to floating-point price.

    Args:
        fixed: Fixed-point integer value
        digits: Number of decimal digits (precision)

    Returns:
        Floating-point price

    Example:
        ```python
        # EURUSD with 5 digits
        price = fixed_to_price(110523, 5)
        # Returns: 1.10523

        # XAUUSD with 2 digits
        price = fixed_to_price(235050, 2)
        # Returns: 2350.50
        ```
    """
    divisor = 10**digits
    return fixed / divisor


def tick_to_array(
    tick: Tick,
    digits: int = 5,
    symbol_id: int = 0,
) -> NDArray[Any]:
    """
    Convert a Tick model to NumPy structured array.

    Args:
        tick: Tick Pydantic model
        digits: Price precision (default: 5 for major forex pairs)
        symbol_id: Symbol lookup ID for C++ engine (default: 0)

    Returns:
        NumPy structured array with TICK_DTYPE

    Example:
        ```python
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
        )
        arr = tick_to_array(tick, digits=5)
        print(arr["bid"])  # 110520
        ```
    """
    arr = np.zeros(1, dtype=TICK_DTYPE)
    arr["timestamp"] = tick.timestamp
    arr["symbol_id"] = symbol_id
    arr["bid"] = price_to_fixed(tick.bid, digits)
    arr["ask"] = price_to_fixed(tick.ask, digits)
    arr["bid_volume"] = int(tick.bid_volume)
    arr["ask_volume"] = int(tick.ask_volume)
    arr["spread_points"] = price_to_fixed(tick.spread, digits)
    return arr[0]


def array_to_tick(
    arr: NDArray[Any],
    symbol: str,
    digits: int = 5,
) -> Tick:
    """
    Convert NumPy structured array to Tick model.

    Args:
        arr: NumPy structured array with TICK_DTYPE
        symbol: Symbol name (not stored in array)
        digits: Price precision (default: 5)

    Returns:
        Tick Pydantic model

    Example:
        ```python
        arr = np.zeros(1, dtype=TICK_DTYPE)
        arr["timestamp"] = 1704067200000000
        arr["bid"] = 110520
        arr["ask"] = 110523

        tick = array_to_tick(arr[0], symbol="EURUSD", digits=5)
        print(tick.bid)  # 1.10520
        ```
    """
    return Tick(
        symbol=symbol,
        timestamp=int(arr["timestamp"]),
        bid=fixed_to_price(int(arr["bid"]), digits),
        ask=fixed_to_price(int(arr["ask"]), digits),
        bid_volume=float(arr["bid_volume"]),
        ask_volume=float(arr["ask_volume"]),
    )


def ticks_to_array(
    ticks: Sequence[Tick],
    digits: int = 5,
    symbol_id: int = 0,
) -> NDArray[Any]:
    """
    Convert a sequence of Tick models to NumPy structured array.

    Args:
        ticks: Sequence of Tick models
        digits: Price precision (default: 5)
        symbol_id: Symbol lookup ID for C++ engine (default: 0)

    Returns:
        NumPy structured array with TICK_DTYPE and shape (n,)

    Example:
        ```python
        ticks = [
            Tick(symbol="EURUSD", timestamp=t, bid=1.105, ask=1.106)
            for t in range(100)
        ]
        arr = ticks_to_array(ticks, digits=5)
        print(arr.shape)  # (100,)
        ```
    """
    n = len(ticks)
    arr = np.zeros(n, dtype=TICK_DTYPE)

    for i, tick in enumerate(ticks):
        arr[i]["timestamp"] = tick.timestamp
        arr[i]["symbol_id"] = symbol_id
        arr[i]["bid"] = price_to_fixed(tick.bid, digits)
        arr[i]["ask"] = price_to_fixed(tick.ask, digits)
        arr[i]["bid_volume"] = int(tick.bid_volume)
        arr[i]["ask_volume"] = int(tick.ask_volume)
        arr[i]["spread_points"] = price_to_fixed(tick.spread, digits)

    return arr


def array_to_ticks(
    arr: NDArray[Any],
    symbol: str,
    digits: int = 5,
) -> list[Tick]:
    """
    Convert NumPy structured array to list of Tick models.

    Args:
        arr: NumPy structured array with TICK_DTYPE
        symbol: Symbol name (not stored in array)
        digits: Price precision (default: 5)

    Returns:
        List of Tick Pydantic models

    Example:
        ```python
        arr = np.zeros(10, dtype=TICK_DTYPE)
        # ... populate array ...

        ticks = array_to_ticks(arr, symbol="EURUSD", digits=5)
        print(len(ticks))  # 10
        ```
    """
    return [array_to_tick(arr[i], symbol=symbol, digits=digits) for i in range(len(arr))]


def bar_to_array(
    bar: Bar,
    digits: int = 5,
    symbol_id: int = 0,
) -> NDArray[Any]:
    """
    Convert a Bar model to NumPy structured array.

    Args:
        bar: Bar Pydantic model
        digits: Price precision (default: 5)
        symbol_id: Symbol lookup ID for C++ engine (default: 0)

    Returns:
        NumPy structured array with BAR_DTYPE

    Example:
        ```python
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )
        arr = bar_to_array(bar, digits=5)
        print(arr["close"])  # 110550
        ```
    """
    arr = np.zeros(1, dtype=BAR_DTYPE)
    arr["timestamp"] = bar.timestamp
    arr["symbol_id"] = symbol_id
    arr["open"] = price_to_fixed(bar.open, digits)
    arr["high"] = price_to_fixed(bar.high, digits)
    arr["low"] = price_to_fixed(bar.low, digits)
    arr["close"] = price_to_fixed(bar.close, digits)
    arr["tick_volume"] = bar.tick_volume
    arr["real_volume"] = int(bar.real_volume)
    arr["spread_points"] = price_to_fixed(bar.spread, digits)
    arr["timeframe"] = bar.timeframe.minutes
    return arr[0]


def array_to_bar(
    arr: NDArray[Any],
    symbol: str,
    digits: int = 5,
) -> Bar:
    """
    Convert NumPy structured array to Bar model.

    Args:
        arr: NumPy structured array with BAR_DTYPE
        symbol: Symbol name (not stored in array)
        digits: Price precision (default: 5)

    Returns:
        Bar Pydantic model

    Example:
        ```python
        arr = np.zeros(1, dtype=BAR_DTYPE)
        arr["timestamp"] = 1704067200000000
        arr["open"] = 110520
        arr["high"] = 110580
        arr["low"] = 110500
        arr["close"] = 110550
        arr["timeframe"] = 60  # H1

        bar = array_to_bar(arr[0], symbol="EURUSD", digits=5)
        print(bar.timeframe)  # Timeframe.H1
        ```
    """
    # Convert timeframe minutes back to enum
    tf_minutes = int(arr["timeframe"])
    timeframe_map = {tf.minutes: tf for tf in Timeframe}
    timeframe = timeframe_map.get(tf_minutes, Timeframe.M1)

    return Bar(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=int(arr["timestamp"]),
        open=fixed_to_price(int(arr["open"]), digits),
        high=fixed_to_price(int(arr["high"]), digits),
        low=fixed_to_price(int(arr["low"]), digits),
        close=fixed_to_price(int(arr["close"]), digits),
        tick_volume=int(arr["tick_volume"]),
        real_volume=float(arr["real_volume"]),
        spread=fixed_to_price(int(arr["spread_points"]), digits),
    )


def bars_to_array(
    bars: Sequence[Bar],
    digits: int = 5,
    symbol_id: int = 0,
) -> NDArray[Any]:
    """
    Convert a sequence of Bar models to NumPy structured array.

    Args:
        bars: Sequence of Bar models
        digits: Price precision (default: 5)
        symbol_id: Symbol lookup ID for C++ engine (default: 0)

    Returns:
        NumPy structured array with BAR_DTYPE and shape (n,)

    Example:
        ```python
        bars = [
            Bar(
                symbol="EURUSD",
                timeframe=Timeframe.H1,
                timestamp=t,
                open=1.105, high=1.106, low=1.104, close=1.105
            )
            for t in range(100)
        ]
        arr = bars_to_array(bars, digits=5)
        print(arr.shape)  # (100,)
        ```
    """
    n = len(bars)
    arr = np.zeros(n, dtype=BAR_DTYPE)

    for i, bar in enumerate(bars):
        arr[i]["timestamp"] = bar.timestamp
        arr[i]["symbol_id"] = symbol_id
        arr[i]["open"] = price_to_fixed(bar.open, digits)
        arr[i]["high"] = price_to_fixed(bar.high, digits)
        arr[i]["low"] = price_to_fixed(bar.low, digits)
        arr[i]["close"] = price_to_fixed(bar.close, digits)
        arr[i]["tick_volume"] = bar.tick_volume
        arr[i]["real_volume"] = int(bar.real_volume)
        arr[i]["spread_points"] = price_to_fixed(bar.spread, digits)
        arr[i]["timeframe"] = bar.timeframe.minutes

    return arr


def array_to_bars(
    arr: NDArray[Any],
    symbol: str,
    digits: int = 5,
) -> list[Bar]:
    """
    Convert NumPy structured array to list of Bar models.

    Args:
        arr: NumPy structured array with BAR_DTYPE
        symbol: Symbol name (not stored in array)
        digits: Price precision (default: 5)

    Returns:
        List of Bar Pydantic models

    Example:
        ```python
        arr = np.zeros(10, dtype=BAR_DTYPE)
        # ... populate array ...

        bars = array_to_bars(arr, symbol="EURUSD", digits=5)
        print(len(bars))  # 10
        ```
    """
    return [array_to_bar(arr[i], symbol=symbol, digits=digits) for i in range(len(arr))]
