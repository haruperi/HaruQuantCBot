"""
MetaTrader 5 data provider for HQT Trading System.

This module implements the DataProvider interface for MetaTrader 5, enabling
historical data fetching directly from the MT5 terminal using the official
MetaTrader5 Python package.

[REQ: DAT-FR-016] MT5 data provider
[REQ: DAT-FR-019] Incremental downloads
[REQ: DAT-FR-020] Progress callbacks
[SDD: §5.4] Data Providers
"""

import time
from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from hqt.data.models.bar import Timeframe
from hqt.data.providers.base import DataProvider
from hqt.foundation.exceptions.broker import BrokerError, ConnectionError

# MetaTrader5 import with fallback for systems without MT5 installed
try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None  # type: ignore


class MT5DataProvider(DataProvider):
    """
    MetaTrader 5 data provider implementation.

    Fetches historical bars and ticks from a connected MetaTrader 5 terminal.
    Requires the MetaTrader5 Python package and a running MT5 terminal.

    Features:
        - Downloads historical bars for any symbol/timeframe available in MT5
        - Downloads tick data with bid/ask/volume
        - Supports incremental downloads (only fetch new data)
        - Progress callbacks for UI integration
        - Automatic connection management
        - Error handling and retry logic

    Connection:
        The provider automatically connects to MT5 on first use and maintains
        the connection until close() is called or the context manager exits.

    Example:
        ```python
        from hqt.data.providers import MT5DataProvider
        from hqt.data.models import Timeframe
        from datetime import datetime, timedelta

        # Use as context manager
        with MT5DataProvider() as provider:
            # Check available symbols
            symbols = provider.get_available_symbols()
            print(f"Available: {len(symbols)} symbols")

            # Fetch daily bars
            end = datetime.now()
            start = end - timedelta(days=365)
            bars = provider.fetch_bars(
                symbol="EURUSD",
                timeframe=Timeframe.D1,
                start=start,
                end=end,
            )
            print(f"Fetched {len(bars)} daily bars")

            # Fetch ticks with progress
            def progress(current, total, eta):
                pct = 100 * current / total
                print(f"\\rProgress: {pct:.1f}% (ETA: {eta:.0f}s)", end="")

            ticks = provider.fetch_ticks(
                symbol="EURUSD",
                start=start,
                end=start + timedelta(days=1),
                progress_callback=progress,
            )
            print(f"\\nFetched {len(ticks)} ticks")
        ```

    Note:
        Requires MetaTrader 5 terminal to be installed and running.
        The terminal must be logged in to a broker account (demo or live).
    """

    # MT5 timeframe mapping
    # Only include timeframes that exist in our Timeframe enum
    _TIMEFRAME_MAP = {
        Timeframe.M1: mt5.TIMEFRAME_M1 if MT5_AVAILABLE else 1,
        Timeframe.M5: mt5.TIMEFRAME_M5 if MT5_AVAILABLE else 5,
        Timeframe.M15: mt5.TIMEFRAME_M15 if MT5_AVAILABLE else 15,
        Timeframe.M30: mt5.TIMEFRAME_M30 if MT5_AVAILABLE else 30,
        Timeframe.H1: mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 60,
        Timeframe.H4: mt5.TIMEFRAME_H4 if MT5_AVAILABLE else 240,
        Timeframe.D1: mt5.TIMEFRAME_D1 if MT5_AVAILABLE else 1440,
        Timeframe.W1: mt5.TIMEFRAME_W1 if MT5_AVAILABLE else 10080,
        Timeframe.MN1: mt5.TIMEFRAME_MN1 if MT5_AVAILABLE else 43200,
    }

    def __init__(self, path: str | None = None, login: int | None = None, password: str | None = None, server: str | None = None):
        """
        Initialize MT5 data provider.

        Args:
            path: Path to MT5 terminal executable (optional, auto-detected)
            login: Trading account login (optional, uses current login)
            password: Trading account password (optional)
            server: Trading server name (optional)

        Raises:
            ImportError: MetaTrader5 package not installed
            ConnectionError: Failed to connect to MT5 terminal

        Note:
            If login credentials are not provided, the provider will use
            the currently logged-in account in the MT5 terminal.
        """
        if not MT5_AVAILABLE:
            raise ImportError(
                "MetaTrader5 package not installed. "
                "Install with: pip install MetaTrader5"
            )

        self._path = path
        self._login = login
        self._password = password
        self._server = server
        self._connected = False

        # Connect immediately to fail fast if MT5 unavailable
        self._ensure_connected()

    def _ensure_connected(self) -> None:
        """
        Ensure MT5 connection is established.

        Raises:
            ConnectionError: Failed to connect to MT5
        """
        if self._connected:
            return

        # Initialize MT5 connection
        if self._path:
            if not mt5.initialize(self._path):
                error = mt5.last_error()
                raise ConnectionError(
                    error_code="BRK-001",
                    module="data.providers.mt5",
                    message=f"Failed to initialize MT5: {error}",
                    broker="MT5",
                    path=self._path,
                    error_details=error,
                )
        else:
            if not mt5.initialize():
                error = mt5.last_error()
                raise ConnectionError(
                    error_code="BRK-001",
                    module="data.providers.mt5",
                    message=f"Failed to initialize MT5: {error}",
                    broker="MT5",
                    error_details=error,
                )

        # Login if credentials provided
        if self._login and self._password and self._server:
            if not mt5.login(self._login, self._password, self._server):
                error = mt5.last_error()
                mt5.shutdown()
                raise ConnectionError(
                    error_code="BRK-002",
                    module="data.providers.mt5",
                    message=f"Failed to login to MT5: {error}",
                    broker="MT5",
                    login=self._login,
                    server=self._server,
                    error_details=error,
                )

        self._connected = True

    def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        progress_callback: Callable[[int, int, float], None] | None = None,
    ) -> pd.DataFrame:
        """
        Fetch historical bar data from MT5.

        Args:
            symbol: MT5 symbol name (e.g., "EURUSD", "BTCUSD")
            timeframe: Bar timeframe
            start: Start datetime (UTC)
            end: End datetime (UTC)
            progress_callback: Optional callback(current, total, eta_seconds)

        Returns:
            DataFrame with standardized bar columns

        Raises:
            ConnectionError: Failed to connect to MT5
            ValueError: Invalid symbol or timeframe
            BrokerError: MT5 API error

        Note:
            MT5 copy_rates_range() is fast and doesn't provide granular
            progress. The callback is called once at start (0%) and once
            at end (100%).
        """
        self._ensure_connected()

        # Get MT5 timeframe constant
        mt5_timeframe = self._TIMEFRAME_MAP.get(timeframe)
        if mt5_timeframe is None:
            raise ValueError(f"Timeframe {timeframe} not supported by MT5")

        # Check symbol exists
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            error = mt5.last_error()
            raise ValueError(
                f"Symbol {symbol} not found in MT5. Error: {error}"
            )

        # Enable symbol for trading (required to access historical data)
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                error = mt5.last_error()
                raise BrokerError(
                    error_code="BRK-010",
                    module="data.providers.mt5",
                    message=f"Failed to enable symbol {symbol}: {error}",
                    symbol=symbol,
                    error_details=error,
                )

        # Call progress callback at start
        if progress_callback:
            progress_callback(0, 100, 0.0)

        # Convert datetimes to UTC if needed
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # Fetch rates from MT5
        start_time = time.time()
        rates = mt5.copy_rates_range(symbol, mt5_timeframe, start, end)

        if rates is None or len(rates) == 0:
            error = mt5.last_error()
            # Empty result might be valid (no data in range)
            if error and error[0] != 1:  # 1 = RES_S_OK
                raise BrokerError(
                    error_code="BRK-011",
                    module="data.providers.mt5",
                    message=f"Failed to fetch bars for {symbol}: {error}",
                    symbol=symbol,
                    timeframe=timeframe.name,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    error_details=error,
                )
            # Return empty DataFrame with correct structure
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "tick_volume",
                    "real_volume",
                    "spread",
                ]
            )

        # Convert to DataFrame
        df = pd.DataFrame(rates)

        # Standardize columns and types
        # MT5 returns: time, open, high, low, close, tick_volume, spread, real_volume
        result = pd.DataFrame(
            {
                "timestamp": (df["time"].astype("int64") * 1_000_000),  # seconds to microseconds
                "open": df["open"].astype("float64"),
                "high": df["high"].astype("float64"),
                "low": df["low"].astype("float64"),
                "close": df["close"].astype("float64"),
                "tick_volume": df["tick_volume"].astype("int64"),
                "real_volume": df["real_volume"].astype("int64"),
                "spread": df["spread"].astype("int32"),
            }
        )

        # Call progress callback at end
        if progress_callback:
            elapsed = time.time() - start_time
            progress_callback(100, 100, 0.0)

        return result

    def fetch_ticks(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        progress_callback: Callable[[int, int, float], None] | None = None,
    ) -> pd.DataFrame:
        """
        Fetch historical tick data from MT5.

        Args:
            symbol: MT5 symbol name
            start: Start datetime (UTC)
            end: End datetime (UTC)
            progress_callback: Optional callback(current, total, eta_seconds)

        Returns:
            DataFrame with standardized tick columns

        Raises:
            ConnectionError: Failed to connect to MT5
            ValueError: Invalid symbol
            BrokerError: MT5 API error

        Note:
            MT5 copy_ticks_range() is fast and doesn't provide granular
            progress. The callback is called once at start (0%) and once
            at end (100%).
        """
        self._ensure_connected()

        # Check symbol exists
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            error = mt5.last_error()
            raise ValueError(
                f"Symbol {symbol} not found in MT5. Error: {error}"
            )

        # Enable symbol for trading
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                error = mt5.last_error()
                raise BrokerError(
                    error_code="BRK-010",
                    module="data.providers.mt5",
                    message=f"Failed to enable symbol {symbol}: {error}",
                    symbol=symbol,
                    error_details=error,
                )

        # Call progress callback at start
        if progress_callback:
            progress_callback(0, 100, 0.0)

        # Convert datetimes to UTC if needed
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # Fetch ticks from MT5 (all ticks including bid/ask/last)
        start_time = time.time()
        ticks = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_ALL)

        if ticks is None or len(ticks) == 0:
            error = mt5.last_error()
            # Empty result might be valid
            if error and error[0] != 1:  # 1 = RES_S_OK
                raise BrokerError(
                    error_code="BRK-012",
                    module="data.providers.mt5",
                    message=f"Failed to fetch ticks for {symbol}: {error}",
                    symbol=symbol,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    error_details=error,
                )
            # Return empty DataFrame
            return pd.DataFrame(
                columns=["timestamp", "bid", "ask", "bid_volume", "ask_volume"]
            )

        # Convert to DataFrame
        df = pd.DataFrame(ticks)

        # Standardize columns and types
        # MT5 returns: time, bid, ask, last, volume, time_msc, flags, volume_real
        result = pd.DataFrame(
            {
                "timestamp": df["time_msc"].astype("int64") * 1000,  # milliseconds to microseconds
                "bid": df["bid"].astype("float64"),
                "ask": df["ask"].astype("float64"),
                "bid_volume": df.get("volume_real", pd.Series(0, index=df.index)).astype("int64"),
                "ask_volume": pd.Series(0, index=df.index, dtype="int64"),  # MT5 doesn't separate bid/ask volume
            }
        )

        # Call progress callback at end
        if progress_callback:
            elapsed = time.time() - start_time
            progress_callback(100, 100, 0.0)

        return result

    def get_available_symbols(self) -> list[str]:
        """
        Get list of all symbols available in MT5.

        Returns:
            List of symbol names

        Raises:
            ConnectionError: Failed to connect to MT5
        """
        self._ensure_connected()

        symbols = mt5.symbols_get()
        if symbols is None:
            error = mt5.last_error()
            raise BrokerError(
                error_code="BRK-013",
                module="data.providers.mt5",
                message=f"Failed to get symbols: {error}",
                error_details=error,
            )

        return [s.name for s in symbols]

    def get_available_timeframes(self, symbol: str) -> list[Timeframe]:
        """
        Get list of timeframes available for a symbol in MT5.

        Args:
            symbol: MT5 symbol name

        Returns:
            List of available timeframes

        Raises:
            ConnectionError: Failed to connect to MT5
            ValueError: Invalid symbol

        Note:
            MT5 supports all standard timeframes for all symbols.
            This method returns all timeframes defined in the Timeframe enum.
        """
        self._ensure_connected()

        # Check symbol exists
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            error = mt5.last_error()
            raise ValueError(
                f"Symbol {symbol} not found in MT5. Error: {error}"
            )

        # MT5 supports all standard timeframes
        return list(self._TIMEFRAME_MAP.keys())

    def get_provider_name(self) -> str:
        """Get provider display name."""
        return "MetaTrader 5"

    def close(self) -> None:
        """Close MT5 connection and release resources."""
        if self._connected:
            mt5.shutdown()
            self._connected = False
