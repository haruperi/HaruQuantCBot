"""
Data provider abstract base class for HQT Trading System.

This module defines the abstract DataProvider interface that all data providers
must implement. Providers fetch historical market data from various sources
(MetaTrader 5, Dukascopy, etc.) and return it in a standardized format.

[REQ: DAT-FR-018] Common DataProvider interface
[SDD: §5.4] Data Providers
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable

import pandas as pd

from hqt.data.models.bar import Timeframe


class DataProvider(ABC):
    """
    Abstract base class for data providers.

    Data providers fetch historical market data from external sources and
    return it as pandas DataFrames with standardized columns. All providers
    must implement the same interface to enable pluggable data sources.

    Implementations:
        - MT5DataProvider: Fetches data from MetaTrader 5 terminal
        - DukascopyProvider: Downloads tick data from Dukascopy public feeds

    Example:
        ```python
        from hqt.data.providers import MT5DataProvider
        from datetime import datetime, timedelta

        provider = MT5DataProvider()

        # Fetch daily bars
        end = datetime.now()
        start = end - timedelta(days=365)
        bars = provider.fetch_bars(
            symbol="EURUSD",
            timeframe=Timeframe.D1,
            start=start,
            end=end,
        )

        # Fetch ticks with progress callback
        def on_progress(current, total, eta):
            print(f"Progress: {current}/{total}, ETA: {eta:.1f}s")

        ticks = provider.fetch_ticks(
            symbol="EURUSD",
            start=start,
            end=end,
            progress_callback=on_progress,
        )
        ```
    """

    @abstractmethod
    def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        progress_callback: Callable[[int, int, float], None] | None = None,
    ) -> pd.DataFrame:
        """
        Fetch historical bar (OHLCV) data for a symbol and timeframe.

        Args:
            symbol: Trading symbol (e.g., "EURUSD", "BTCUSD")
            timeframe: Bar timeframe (M1, M5, H1, D1, etc.)
            start: Start datetime (UTC)
            end: End datetime (UTC)
            progress_callback: Optional callback(current, total, eta_seconds)

        Returns:
            DataFrame with columns:
                - timestamp: int64 (Unix timestamp in microseconds)
                - open: float64
                - high: float64
                - low: float64
                - close: float64
                - tick_volume: int64
                - real_volume: int64 (0 if not available)
                - spread: int32 (spread in points)

            Index: RangeIndex
            Sorted by timestamp ascending

        Raises:
            ConnectionError: Failed to connect to data source
            ValueError: Invalid symbol or timeframe
            TimeoutError: Request timed out
            DataError: Data quality issues detected

        Example:
            ```python
            bars = provider.fetch_bars(
                symbol="EURUSD",
                timeframe=Timeframe.H1,
                start=datetime(2024, 1, 1),
                end=datetime(2024, 12, 31),
            )
            print(f"Fetched {len(bars)} bars")
            ```
        """
        pass

    @abstractmethod
    def fetch_ticks(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        progress_callback: Callable[[int, int, float], None] | None = None,
    ) -> pd.DataFrame:
        """
        Fetch historical tick data for a symbol.

        Args:
            symbol: Trading symbol (e.g., "EURUSD", "BTCUSD")
            start: Start datetime (UTC)
            end: End datetime (UTC)
            progress_callback: Optional callback(current, total, eta_seconds)

        Returns:
            DataFrame with columns:
                - timestamp: int64 (Unix timestamp in microseconds)
                - bid: float64
                - ask: float64
                - bid_volume: int64 (0 if not available)
                - ask_volume: int64 (0 if not available)

            Index: RangeIndex
            Sorted by timestamp ascending

        Raises:
            ConnectionError: Failed to connect to data source
            ValueError: Invalid symbol
            TimeoutError: Request timed out
            DataError: Data quality issues detected

        Example:
            ```python
            ticks = provider.fetch_ticks(
                symbol="EURUSD",
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 2),
            )
            print(f"Fetched {len(ticks)} ticks")
            ```
        """
        pass

    @abstractmethod
    def get_available_symbols(self) -> list[str]:
        """
        Get list of symbols available from this provider.

        Returns:
            List of symbol names (e.g., ["EURUSD", "GBPUSD", "BTCUSD"])

        Raises:
            ConnectionError: Failed to connect to data source

        Example:
            ```python
            symbols = provider.get_available_symbols()
            print(f"Provider offers {len(symbols)} symbols")
            for symbol in symbols[:10]:
                print(f"  - {symbol}")
            ```
        """
        pass

    @abstractmethod
    def get_available_timeframes(self, symbol: str) -> list[Timeframe]:
        """
        Get list of timeframes available for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of available timeframes (e.g., [M1, M5, H1, D1])

        Raises:
            ConnectionError: Failed to connect to data source
            ValueError: Invalid symbol

        Example:
            ```python
            timeframes = provider.get_available_timeframes("EURUSD")
            print(f"EURUSD timeframes: {timeframes}")
            ```
        """
        pass

    def supports_incremental_download(self) -> bool:
        """
        Check if provider supports incremental downloads.

        Incremental downloads only fetch data newer than the latest stored
        timestamp, avoiding re-downloading historical data.

        Returns:
            True if provider supports incremental downloads

        Note:
            Default implementation returns True. Providers that don't support
            incremental downloads should override this to return False.
        """
        return True

    def get_provider_name(self) -> str:
        """
        Get human-readable provider name.

        Returns:
            Provider name (e.g., "MetaTrader 5", "Dukascopy")

        Note:
            Default implementation returns class name. Providers should
            override this to provide a better display name.
        """
        return self.__class__.__name__

    def close(self) -> None:
        """
        Close connection and release resources.

        This method is called when the provider is no longer needed.
        Providers should override this to clean up connections, close
        files, etc.

        Note:
            Default implementation does nothing. Use with context managers:
            ```python
            with provider:
                bars = provider.fetch_bars(...)
            # provider.close() called automatically
            ```
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure resources are released."""
        self.close()
        return False
