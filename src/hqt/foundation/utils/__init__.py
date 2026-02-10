"""
HQT Trading System Utility Functions.

This module provides comprehensive utility functions for datetime handling,
validation, financial calculations, and general helper functions.

Quick Start:
    ```python
    from hqt.foundation.utils import (
        # Datetime utilities
        utc_now, is_market_open, align_to_bar, Timeframe,

        # Validation utilities
        validate_symbol, validate_volume, validate_price,

        # Calculation utilities
        pip_value, profit_in_account_currency, position_size_from_risk,

        # Helper utilities
        deep_merge, generate_uuid, hash_file, sizeof_fmt,
    )

    # Check if market is open
    if is_market_open():
        print("Market is open for trading!")

    # Calculate position size
    lots = position_size_from_risk(
        account_balance=10000,
        risk_percent=1.0,
        stop_loss_pips=50,
    )
    ```
"""

# Datetime utilities
from .datetime_utils import (
    Timeframe,
    align_to_bar,
    get_session_name,
    is_dst,
    is_market_open,
    next_bar_time,
    trading_days_between,
    utc_now,
)

# Validation utilities
from .validation_utils import (
    sanitize_string,
    validate_integer,
    validate_positive,
    validate_price,
    validate_range,
    validate_symbol,
    validate_volume,
)

# Calculation utilities
from .calculation_utils import (
    CONTRACT_SIZE_CRYPTO,
    CONTRACT_SIZE_FOREX,
    CONTRACT_SIZE_INDICES,
    CONTRACT_SIZE_METALS_GOLD,
    CONTRACT_SIZE_METALS_SILVER,
    kelly_criterion,
    lot_to_units,
    max_drawdown,
    pip_value,
    points_to_price,
    position_size_from_risk,
    price_to_points,
    profit_in_account_currency,
    sharpe_ratio,
    units_to_lots,
)

# Helper utilities
from .helpers import (
    clamp,
    deep_merge,
    denormalize,
    flatten_dict,
    generate_uuid,
    hash_file,
    hash_string,
    lerp,
    normalize,
    safe_divide,
    sizeof_fmt,
    unflatten_dict,
)

__all__ = [
    # Datetime utilities
    "Timeframe",
    "utc_now",
    "is_market_open",
    "align_to_bar",
    "next_bar_time",
    "trading_days_between",
    "get_session_name",
    "is_dst",
    # Validation utilities
    "validate_symbol",
    "validate_volume",
    "validate_price",
    "validate_positive",
    "validate_range",
    "validate_integer",
    "sanitize_string",
    # Calculation utilities
    "CONTRACT_SIZE_FOREX",
    "CONTRACT_SIZE_METALS_GOLD",
    "CONTRACT_SIZE_METALS_SILVER",
    "CONTRACT_SIZE_INDICES",
    "CONTRACT_SIZE_CRYPTO",
    "lot_to_units",
    "units_to_lots",
    "pip_value",
    "points_to_price",
    "price_to_points",
    "profit_in_account_currency",
    "position_size_from_risk",
    "kelly_criterion",
    "sharpe_ratio",
    "max_drawdown",
    # Helper utilities
    "deep_merge",
    "flatten_dict",
    "unflatten_dict",
    "generate_uuid",
    "hash_file",
    "hash_string",
    "sizeof_fmt",
    "clamp",
    "safe_divide",
    "lerp",
    "normalize",
    "denormalize",
]
