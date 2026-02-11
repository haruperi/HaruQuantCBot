"""
Data models for HQT Trading System.

This module exports all data model classes and related enums for
tick data, bar (OHLCV) data, and symbol specifications.

[REQ: DAT-FR-001 through DAT-FR-005] Complete data model implementation.
"""

from hqt.data.models.bar import Bar, Timeframe, create_bar
from hqt.data.models.dtypes import (
    BAR_DTYPE,
    TICK_DTYPE,
    array_to_bar,
    array_to_bars,
    array_to_tick,
    array_to_ticks,
    bar_to_array,
    bars_to_array,
    fixed_to_price,
    price_to_fixed,
    tick_to_array,
    ticks_to_array,
)
from hqt.data.models.symbol_spec import (
    SwapType,
    SymbolSpecification,
    TradeMode,
)
from hqt.data.models.tick import Tick, create_tick

__all__ = [
    # Tick model
    "Tick",
    "create_tick",
    # Bar model
    "Bar",
    "Timeframe",
    "create_bar",
    # Symbol specification
    "SymbolSpecification",
    "SwapType",
    "TradeMode",
    # NumPy dtypes
    "TICK_DTYPE",
    "BAR_DTYPE",
    # Conversion functions
    "price_to_fixed",
    "fixed_to_price",
    "tick_to_array",
    "array_to_tick",
    "ticks_to_array",
    "array_to_ticks",
    "bar_to_array",
    "array_to_bar",
    "bars_to_array",
    "array_to_bars",
]
