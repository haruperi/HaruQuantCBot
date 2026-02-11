"""
HQT Data Infrastructure.

This module provides data management infrastructure including:
- Data models (Tick, Bar, SymbolSpecification)
- Data validation pipeline
- Data providers (MT5, Dukascopy)
- Data storage (Parquet, HDF5)
- Data versioning and lineage tracking

[REQ: DAT-FR-001 through DAT-FR-029]
"""

from hqt.data.models import (
    BAR_DTYPE,
    TICK_DTYPE,
    Bar,
    SwapType,
    SymbolSpecification,
    Tick,
    Timeframe,
    TradeMode,
    array_to_bar,
    array_to_bars,
    array_to_tick,
    array_to_ticks,
    bar_to_array,
    bars_to_array,
    create_bar,
    create_tick,
    fixed_to_price,
    price_to_fixed,
    tick_to_array,
    ticks_to_array,
)

__all__ = [
    # Models
    "Tick",
    "Bar",
    "Timeframe",
    "SymbolSpecification",
    "SwapType",
    "TradeMode",
    # Factory functions
    "create_tick",
    "create_bar",
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
