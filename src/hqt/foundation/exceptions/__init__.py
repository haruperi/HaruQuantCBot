"""
HQT Trading System Exception Hierarchy.

This module provides a comprehensive exception hierarchy for the entire
trading system, with standardized error codes, module tracking, and
structured error information.

Exception Hierarchy:
    HQTBaseError
    ├── DataError
    │   ├── ValidationError
    │   ├── PriceSanityError
    │   ├── GapError
    │   └── DuplicateError
    ├── TradingError
    │   ├── OrderError
    │   ├── MarginError
    │   └── StopOutError
    ├── BrokerError
    │   ├── ConnectionError
    │   ├── TimeoutError
    │   └── ReconnectError
    ├── EngineError
    ├── BridgeError
    ├── ConfigError
    │   ├── SchemaError
    │   └── SecretError

Usage:
    ```python
    from hqt.foundation.exceptions import ValidationError

    raise ValidationError(
        error_code="DAT-001",
        module="data.validation",
        message="Invalid price value",
        field="price",
        value=-100.0
    )
    ```
"""

# Base exception
from .base import HQTBaseError

# Broker exceptions
from .broker import BrokerError, ConnectionError, ReconnectError, TimeoutError

# Configuration exceptions
from .config import ConfigError, SchemaError, SecretError

# Data exceptions
from .data import (
    DataError,
    DuplicateError,
    GapError,
    PriceSanityError,
    ValidationError,
)

# Engine exceptions
from .engine import BridgeError, EngineError

# Trading exceptions
from .trading import MarginError, OrderError, StopOutError, TradingError

__all__ = [
    # Base
    "HQTBaseError",
    # Data
    "DataError",
    "ValidationError",
    "PriceSanityError",
    "GapError",
    "DuplicateError",
    # Trading
    "TradingError",
    "OrderError",
    "MarginError",
    "StopOutError",
    # Broker
    "BrokerError",
    "ConnectionError",
    "TimeoutError",
    "ReconnectError",
    # Engine
    "EngineError",
    "BridgeError",
    # Config
    "ConfigError",
    "SchemaError",
    "SecretError",
]
