"""
Base data storage interface for HQT Trading System.

This module defines the abstract DataStore interface that all storage backends
must implement (Parquet, HDF5, etc.).

[REQ: DAT-FR-021, DAT-FR-023] Data storage with columnar access
[SDD: §5.2] Data Storage Architecture
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from hqt.data.models.bar import Timeframe


class DataStore(ABC):
    """
    Abstract base class for data storage backends.

    Data stores provide persistent storage for tick and bar data with
    efficient columnar access. All stores must implement the same interface
    to enable pluggable storage backends.

    Implementations:
        - ParquetStore: Apache Parquet format with PyArrow
        - HDF5Store: HDF5 format with h5py

    Example:
        ```python
        from hqt.data.storage import ParquetStore
        import pandas as pd

        store = ParquetStore(base_path="data/parquet")

        # Write bars
        bars_df = pd.DataFrame(...)
        store.write_bars(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            data=bars_df,
            partition="2024",
        )

        # Read bars with time filter
        bars = store.read_bars(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
        )

        # Read specific columns only (columnar access)
        closes = store.read_bars(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            columns=["timestamp", "close"],
        )
        ```
    """

    @abstractmethod
    def write_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        data: pd.DataFrame,
        partition: str | None = None,
    ) -> Path:
        """
        Write bar data to storage.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe
            data: DataFrame with bar data (timestamp, OHLCV, spread)
            partition: Partition identifier (e.g., "2024", "2024-01")

        Returns:
            Path to written file

        Raises:
            ValueError: Invalid data format
            IOError: Write failed

        Note:
            Data must have columns: timestamp, open, high, low, close,
            tick_volume, real_volume, spread
        """
        pass

    @abstractmethod
    def write_ticks(
        self,
        symbol: str,
        data: pd.DataFrame,
        partition: str | None = None,
    ) -> Path:
        """
        Write tick data to storage.

        Args:
            symbol: Trading symbol
            data: DataFrame with tick data (timestamp, bid, ask, volumes)
            partition: Partition identifier (e.g., "2024-01")

        Returns:
            Path to written file

        Raises:
            ValueError: Invalid data format
            IOError: Write failed

        Note:
            Data must have columns: timestamp, bid, ask, bid_volume, ask_volume
        """
        pass

    @abstractmethod
    def read_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None = None,
        end: datetime | None = None,
        columns: list[str] | None = None,
        partition: str | None = None,
    ) -> pd.DataFrame:
        """
        Read bar data from storage.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe
            start: Start datetime (inclusive, UTC)
            end: End datetime (exclusive, UTC)
            columns: Columns to read (None = all columns)
            partition: Partition identifier (None = all partitions)

        Returns:
            DataFrame with requested bar data

        Raises:
            FileNotFoundError: Data not found
            ValueError: Invalid parameters

        Note:
            Columnar access: only specified columns are loaded from disk.
            Time filtering: predicate pushdown for efficient filtering.
        """
        pass

    @abstractmethod
    def read_ticks(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
        columns: list[str] | None = None,
        partition: str | None = None,
    ) -> pd.DataFrame:
        """
        Read tick data from storage.

        Args:
            symbol: Trading symbol
            start: Start datetime (inclusive, UTC)
            end: End datetime (exclusive, UTC)
            columns: Columns to read (None = all columns)
            partition: Partition identifier (None = all partitions)

        Returns:
            DataFrame with requested tick data

        Raises:
            FileNotFoundError: Data not found
            ValueError: Invalid parameters
        """
        pass

    @abstractmethod
    def list_symbols(self) -> list[str]:
        """
        List all symbols with stored data.

        Returns:
            List of symbol names
        """
        pass

    @abstractmethod
    def list_timeframes(self, symbol: str) -> list[Timeframe]:
        """
        List all timeframes available for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of available timeframes
        """
        pass

    @abstractmethod
    def list_partitions(
        self,
        symbol: str,
        timeframe: Timeframe | None = None,
    ) -> list[str]:
        """
        List all partitions for a symbol/timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (None for ticks)

        Returns:
            List of partition identifiers

        Example:
            ```python
            # List tick partitions
            partitions = store.list_partitions("EURUSD", None)
            # Returns: ["2024-01", "2024-02", ...]

            # List H1 bar partitions
            partitions = store.list_partitions("EURUSD", Timeframe.H1)
            # Returns: ["2024", "2025", ...]
            ```
        """
        pass

    @abstractmethod
    def delete_data(
        self,
        symbol: str,
        timeframe: Timeframe | None = None,
        partition: str | None = None,
    ) -> int:
        """
        Delete stored data.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (None for ticks)
            partition: Partition identifier (None = all partitions)

        Returns:
            Number of files deleted

        Raises:
            ValueError: Invalid parameters

        Warning:
            This permanently deletes data. Use with caution.
        """
        pass

    @abstractmethod
    def get_file_info(
        self,
        symbol: str,
        timeframe: Timeframe | None = None,
        partition: str | None = None,
    ) -> dict[str, Any]:
        """
        Get metadata about stored files.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (None for ticks)
            partition: Partition identifier

        Returns:
            Dictionary with file metadata:
                - path: File path
                - size_bytes: File size
                - row_count: Number of rows
                - date_range: (min_timestamp, max_timestamp)
                - columns: List of column names

        Raises:
            FileNotFoundError: Data not found
        """
        pass

    def close(self) -> None:
        """
        Close storage and release resources.

        Default implementation does nothing. Stores should override if
        they maintain open file handles or connections.
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure resources are released."""
        self.close()
        return False
