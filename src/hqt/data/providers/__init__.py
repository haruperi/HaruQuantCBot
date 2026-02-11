"""
Data providers for HQT Trading System.

This module provides data providers for fetching historical market data
from various sources (MetaTrader 5, Dukascopy, etc.).

[REQ: DAT-FR-016 through DAT-FR-020]
[SDD: §5.4] Data Providers
"""

from hqt.data.providers.base import DataProvider
from hqt.data.providers.dukascopy_provider import DukascopyProvider
from hqt.data.providers.factory import (
    download_with_progress,
    get_available_providers,
    get_provider,
    with_retry,
)

# MT5DataProvider is optional (requires MetaTrader5 package)
try:
    from hqt.data.providers.mt5_provider import MT5DataProvider

    _MT5_AVAILABLE = True
except ImportError:
    _MT5_AVAILABLE = False
    MT5DataProvider = None  # type: ignore

__all__ = [
    # Base class
    "DataProvider",
    # Providers
    "MT5DataProvider",
    "DukascopyProvider",
    # Factory
    "get_provider",
    "get_available_providers",
    "download_with_progress",
    # Utilities
    "with_retry",
]
