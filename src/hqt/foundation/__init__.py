"""
HQT Trading System Foundation Layer.

This module provides the foundational infrastructure for the HQT trading system,
including exception handling, logging, configuration management, and utility functions.

Quick Start:
    ```python
    from hqt.foundation import (
        # Configuration
        ConfigManager, AppConfig, SecretsManager,

        # Logging
        setup_logging,

        # Exceptions
        HQTBaseError, DataError, TradingError, BrokerError,

        # Utilities
        utc_now, is_market_open, validate_symbol, pip_value,
    )

    # Setup logging
    setup_logging()

    # Load configuration
    manager = ConfigManager()
    config = manager.load(env="development")

    # Use utilities
    if is_market_open():
        print("Market is open!")
    ```
"""

# Configuration Management
from .config import (
    AppConfig,
    BrokerConfig,
    BrokerType,
    ConfigManager,
    DataConfig,
    DataProviderType,
    DatabaseConfig,
    EngineConfig,
    LoggingConfig,
    LogLevel,
    NotificationChannel,
    NotificationConfig,
    OptimizationConfig,
    OptimizationMethod,
    PositionSizingMethod,
    RiskConfig,
    SecretsManager,
    UIConfig,
)

# Exception Handling
from .exceptions import (
    BridgeError,
    BrokerError,
    ConfigError,
    ConnectionError,
    DataError,
    DuplicateError,
    EngineError,
    GapError,
    HQTBaseError,
    MarginError,
    OrderError,
    PriceSanityError,
    ReconnectError,
    SchemaError,
    SecretError,
    StopOutError,
    TimeoutError,
    TradingError,
    ValidationError,
)

# Logging System
from .logging import setup_logging

# Database Layer
from .database import (
    Base,
    DatabaseManager,
    User,
    Strategy,
    Backtest,
    BacktestRepository,
    BacktestTrade,
    NotificationRepository,
    OptimizationRepository,
    OptimizationResult,
    OptimizationResultRepository,
    StrategyRepository,
    TradeRepository,
    UserRepository,
)

# Utility Functions - Datetime
from .utils import (
    Timeframe,
    align_to_bar,
    get_session_name,
    is_dst,
    is_market_open,
    next_bar_time,
    trading_days_between,
    utc_now,
)

# Utility Functions - Validation
from .utils import (
    sanitize_string,
    validate_integer,
    validate_positive,
    validate_price,
    validate_range,
    validate_symbol,
    validate_volume,
)

# Utility Functions - Calculation
from .utils import (
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

# Utility Functions - Helpers
from .utils import (
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
    # Configuration
    "ConfigManager",
    "AppConfig",
    "SecretsManager",
    "EngineConfig",
    "DataConfig",
    "DataProviderType",
    "BrokerConfig",
    "BrokerType",
    "RiskConfig",
    "PositionSizingMethod",
    "NotificationConfig",
    "NotificationChannel",
    "LoggingConfig",
    "LogLevel",
    "UIConfig",
    "DatabaseConfig",
    "OptimizationConfig",
    "OptimizationMethod",
    # Exceptions
    "HQTBaseError",
    "DataError",
    "ValidationError",
    "PriceSanityError",
    "GapError",
    "DuplicateError",
    "TradingError",
    "OrderError",
    "MarginError",
    "StopOutError",
    "BrokerError",
    "ConnectionError",
    "TimeoutError",
    "ReconnectError",
    "EngineError",
    "BridgeError",
    "ConfigError",
    "SchemaError",
    "SecretError",
    # Logging
    "setup_logging",
    # Database
    "DatabaseManager",
    "Base",
    "User",
    "Strategy",
    "Backtest",
    "BacktestTrade",
    "BacktestRepository",
    "StrategyRepository",
    "UserRepository",
    "TradeRepository",
    "OptimizationRepository",
    "OptimizationResult",
    "OptimizationResultRepository",
    "NotificationRepository",
    # Utility Functions - Datetime
    "Timeframe",
    "utc_now",
    "is_market_open",
    "align_to_bar",
    "next_bar_time",
    "trading_days_between",
    "get_session_name",
    "is_dst",
    # Utility Functions - Validation
    "validate_symbol",
    "validate_volume",
    "validate_price",
    "validate_positive",
    "validate_range",
    "validate_integer",
    "sanitize_string",
    # Utility Functions - Calculation
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
    # Utility Functions - Helpers
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
