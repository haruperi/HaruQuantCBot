"""
Storage manager for HQT Trading System.

This module orchestrates the complete data storage pipeline: downloading
from providers, validation, storage, and catalog registration.

[REQ: DAT-FR-025] Data compaction
[SDD: §5.2] Data Storage Architecture
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from hqt.data.models.bar import Timeframe
from hqt.data.providers.base import DataProvider
from hqt.data.storage.base import DataStore
from hqt.data.storage.catalog import DataCatalog
from hqt.data.validation.pipeline import ValidationPipeline
from hqt.foundation.logging import get_logger

logger = get_logger(__name__)


class PartitionStrategy:
    """
    Partition strategy for data storage.

    Determines partition naming based on timeframe:
        - Ticks: Monthly partitions (2024-01, 2024-02, ...)
        - M1: Yearly partitions (2024, 2025, ...)
        - M5-M30: Yearly partitions
        - H1-H12: Yearly partitions
        - D1+: Single partition (all)

    Example:
        ```python
        strategy = PartitionStrategy()

        # Tick data
        partition = strategy.get_partition(None, datetime(2024, 3, 15))
        # Returns: "2024-03"

        # M1 bars
        partition = strategy.get_partition(Timeframe.M1, datetime(2024, 6, 20))
        # Returns: "2024"

        # D1 bars
        partition = strategy.get_partition(Timeframe.D1, datetime(2024, 6, 20))
        # Returns: "all"
        ```
    """

    @staticmethod
    def get_partition(timeframe: Timeframe | None, timestamp: datetime) -> str:
        """
        Get partition identifier for a timestamp.

        Args:
            timeframe: Bar timeframe (None for ticks)
            timestamp: Data timestamp

        Returns:
            Partition identifier string
        """
        if timeframe is None:
            # Ticks: monthly partitions
            return timestamp.strftime("%Y-%m")
        elif timeframe.minutes <= 30:  # M1-M30
            # Intraday bars: yearly partitions
            return timestamp.strftime("%Y")
        elif timeframe.minutes < 1440:  # H1-H12
            # Hourly bars: yearly partitions
            return timestamp.strftime("%Y")
        else:  # D1+
            # Daily and higher: single partition
            return "all"

    @staticmethod
    def parse_partition_range(partition: str) -> tuple[datetime, datetime]:
        """
        Parse partition string to datetime range.

        Args:
            partition: Partition identifier

        Returns:
            (start_datetime, end_datetime) tuple

        Example:
            ```python
            start, end = PartitionStrategy.parse_partition_range("2024-03")
            # Returns: (2024-03-01 00:00:00, 2024-04-01 00:00:00)
            ```
        """
        if partition == "all":
            # No time bounds for "all" partition
            return (datetime.min, datetime.max)
        elif "-" in partition and len(partition) == 7:  # YYYY-MM
            year, month = map(int, partition.split("-"))
            start = datetime(year, month, 1)
            # End of month
            if month == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month + 1, 1)
            return (start, end)
        elif len(partition) == 4:  # YYYY
            year = int(partition)
            start = datetime(year, 1, 1)
            end = datetime(year + 1, 1, 1)
            return (start, end)
        else:
            raise ValueError(f"Invalid partition format: {partition}")


class StorageManager:
    """
    Storage manager orchestrating the data pipeline.

    Integrates data providers, validation, storage, and catalog to provide
    a complete data management solution.

    Pipeline:
        Provider → Validation → Storage → Catalog → Hash

    Features:
        - Download and store with full validation
        - Incremental downloads
        - Data compaction (merge files)
        - Catalog-based queries
        - Version tracking with SHA-256 hashes
        - Automatic partitioning

    Example:
        ```python
        from hqt.data.storage import StorageManager, ParquetStore, DataCatalog
        from hqt.data.providers import MT5DataProvider
        from hqt.data.models import Timeframe
        from datetime import datetime, timedelta

        # Initialize manager
        store = ParquetStore("data/parquet")
        catalog = DataCatalog("data/catalog.db")
        manager = StorageManager(store, catalog)

        # Download and store
        provider = MT5DataProvider()
        end = datetime.now()
        start = end - timedelta(days=365)

        manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=start,
            end=end,
            validate=True,
        )

        # Compact incremental files
        manager.compact(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
        )

        # Query data
        bars = manager.read_bars(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
        )
        ```
    """

    def __init__(
        self,
        store: DataStore,
        catalog: DataCatalog | None = None,
        validation_pipeline: ValidationPipeline | None = None,
    ):
        """
        Initialize storage manager.

        Args:
            store: Data storage backend (Parquet or HDF5)
            catalog: Data catalog (optional, creates default if None)
            validation_pipeline: Validation pipeline (optional, creates default if None)
        """
        self.store = store
        self.catalog = catalog if catalog else DataCatalog()
        self.validation_pipeline = (
            validation_pipeline if validation_pipeline else ValidationPipeline()
        )
        self.partition_strategy = PartitionStrategy()

    def download_and_store(
        self,
        provider: DataProvider,
        symbol: str,
        timeframe: Timeframe | None,
        start: datetime,
        end: datetime,
        validate: bool = True,
        validate_critical_only: bool = True,
        data_source: str | None = None,
        progress_callback: Callable[[int, int, float], None] | None = None,
    ) -> dict[str, Any]:
        """
        Download data and store with full pipeline.

        Pipeline:
            1. Download from provider
            2. Validate data (optional)
            3. Write to storage
            4. Compute version hash
            5. Register in catalog

        Args:
            provider: Data provider
            symbol: Trading symbol
            timeframe: Bar timeframe (None for ticks)
            start: Start datetime (UTC)
            end: End datetime (UTC)
            validate: Run validation pipeline
            validate_critical_only: Only fail on critical issues
            data_source: Data source name (optional, defaults to provider name)
            progress_callback: Progress callback for downloads

        Returns:
            Dictionary with results:
                - partitions: List of partition identifiers stored
                - total_rows: Total rows downloaded
                - validation_report: Validation report (if validate=True)
                - version_hash: SHA-256 content hash

        Raises:
            DataError: Critical validation issues found
        """
        logger.info(
            f"Download and store: {symbol} {timeframe} "
            f"{start.date()} to {end.date()}"
        )

        # Download data
        if timeframe:
            data = provider.fetch_bars(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
                progress_callback=progress_callback,
            )
        else:
            data = provider.fetch_ticks(
                symbol=symbol,
                start=start,
                end=end,
                progress_callback=progress_callback,
            )

        if len(data) == 0:
            logger.warning("No data downloaded")
            return {
                "partitions": [],
                "total_rows": 0,
                "validation_report": None,
                "version_hash": None,
            }

        logger.info(f"Downloaded {len(data)} rows")

        # Validate data
        validation_report = None
        if validate:
            logger.info("Validating data...")
            if timeframe:
                validation_report = self.validation_pipeline.validate_bars(
                    data, symbol
                )
            else:
                validation_report = self.validation_pipeline.validate_ticks(
                    data, symbol
                )

            if validation_report.has_critical_issues() and validate_critical_only:
                raise DataError(
                    error_code="DAT-040",
                    module="data.storage.manager",
                    message=f"Critical validation issues found for {symbol}",
                    symbol=symbol,
                    issue_count=len(validation_report.critical_issues),
                )

            logger.info(
                f"Validation: {validation_report.total_issues} issues "
                f"({validation_report.critical_count} critical)"
            )

        # Group by partition
        partitions_data = self._partition_data(data, timeframe)

        # Store each partition
        stored_partitions = []
        for partition, partition_df in partitions_data.items():
            logger.info(f"Storing partition {partition}: {len(partition_df)} rows")

            # Write to storage
            if timeframe:
                file_path = self.store.write_bars(
                    symbol=symbol,
                    timeframe=timeframe,
                    data=partition_df,
                    partition=partition,
                )
            else:
                file_path = self.store.write_ticks(
                    symbol=symbol,
                    data=partition_df,
                    partition=partition,
                )

            # Compute version hash
            version_hash = self._compute_hash(partition_df)

            # Register in catalog
            min_ts = int(partition_df["timestamp"].min())
            max_ts = int(partition_df["timestamp"].max())

            # Determine storage format from file extension
            storage_format = "parquet" if file_path.suffix == ".parquet" else "hdf5"

            # Get data source name
            source = data_source if data_source else provider.get_provider_name()

            self.catalog.register_file(
                symbol=symbol,
                timeframe=timeframe,
                partition=partition,
                file_path=str(file_path),
                storage_format=storage_format,
                row_count=len(partition_df),
                min_timestamp=min_ts,
                max_timestamp=max_ts,
                data_source=source,
                version_hash=version_hash,
            )

            stored_partitions.append(partition)
            logger.info(f"Partition {partition} stored and cataloged")

        return {
            "partitions": stored_partitions,
            "total_rows": len(data),
            "validation_report": validation_report,
            "version_hash": version_hash if len(stored_partitions) == 1 else None,
        }

    def _partition_data(
        self,
        data: pd.DataFrame,
        timeframe: Timeframe | None,
    ) -> dict[str, pd.DataFrame]:
        """
        Partition data by strategy.

        Args:
            data: DataFrame to partition
            timeframe: Bar timeframe (None for ticks)

        Returns:
            Dictionary mapping partition ID to DataFrame
        """
        # Convert timestamps to datetime for partitioning
        data["_partition_dt"] = pd.to_datetime(data["timestamp"], unit="us")

        # Group by partition
        partitions = {}
        for dt, group in data.groupby(
            data["_partition_dt"].apply(
                lambda x: self.partition_strategy.get_partition(timeframe, x)
            )
        ):
            partitions[dt] = group.drop("_partition_dt", axis=1).copy()

        return partitions

    def _compute_hash(self, data: pd.DataFrame) -> str:
        """
        Compute SHA-256 hash of DataFrame content.

        Args:
            data: DataFrame

        Returns:
            Hexadecimal hash string
        """
        # Convert to bytes for hashing (use timestamp + close/ask as signature)
        if "close" in data.columns:
            signature = data[["timestamp", "close"]].to_numpy().tobytes()
        elif "ask" in data.columns:
            signature = data[["timestamp", "ask"]].to_numpy().tobytes()
        else:
            signature = data["timestamp"].to_numpy().tobytes()

        return hashlib.sha256(signature).hexdigest()

    def compact(
        self,
        symbol: str,
        timeframe: Timeframe | None,
        partition: str,
    ) -> dict[str, Any]:
        """
        Compact data files by merging and rewriting.

        Merges all incremental files for a partition into a single optimized
        file. Useful after multiple incremental downloads.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (None for ticks)
            partition: Partition to compact

        Returns:
            Dictionary with results:
                - rows_before: Row count before compaction
                - rows_after: Row count after compaction
                - files_merged: Number of files merged
                - new_file_path: Path to compacted file

        Example:
            ```python
            # After multiple incremental downloads to 2024 partition
            result = manager.compact("EURUSD", Timeframe.H1, "2024")
            print(f"Merged {result['files_merged']} files")
            ```
        """
        logger.info(f"Compacting {symbol} {timeframe} partition {partition}")

        # Read all data for partition
        if timeframe:
            data = self.store.read_bars(
                symbol=symbol, timeframe=timeframe, partition=partition
            )
        else:
            data = self.store.read_ticks(symbol=symbol, partition=partition)

        rows_before = len(data)

        # Remove duplicates and sort
        data = data.drop_duplicates(subset=["timestamp"], keep="last")
        data = data.sort_values("timestamp").reset_index(drop=True)

        rows_after = len(data)

        # Delete old data
        files_deleted = self.store.delete_data(symbol, timeframe, partition)

        # Write compacted data
        if timeframe:
            file_path = self.store.write_bars(
                symbol=symbol, timeframe=timeframe, data=data, partition=partition
            )
        else:
            file_path = self.store.write_ticks(symbol=symbol, data=data, partition=partition)

        # Update catalog
        version_hash = self._compute_hash(data)
        min_ts = int(data["timestamp"].min())
        max_ts = int(data["timestamp"].max())

        storage_format = "parquet" if file_path.suffix == ".parquet" else "hdf5"

        self.catalog.register_file(
            symbol=symbol,
            timeframe=timeframe,
            partition=partition,
            file_path=str(file_path),
            storage_format=storage_format,
            row_count=rows_after,
            min_timestamp=min_ts,
            max_timestamp=max_ts,
            version_hash=version_hash,
        )

        logger.info(
            f"Compacted {symbol} {timeframe} {partition}: "
            f"{rows_before} → {rows_after} rows ({files_deleted} files merged)"
        )

        return {
            "rows_before": rows_before,
            "rows_after": rows_after,
            "files_merged": files_deleted,
            "new_file_path": str(file_path),
        }

    def read_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None = None,
        end: datetime | None = None,
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """
        Read bar data from storage.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe
            start: Start datetime (UTC, inclusive)
            end: End datetime (UTC, exclusive)
            columns: Columns to read (None = all)

        Returns:
            DataFrame with bar data
        """
        return self.store.read_bars(symbol, timeframe, start, end, columns)

    def read_ticks(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """
        Read tick data from storage.

        Args:
            symbol: Trading symbol
            start: Start datetime (UTC, inclusive)
            end: End datetime (UTC, exclusive)
            columns: Columns to read (None = all)

        Returns:
            DataFrame with tick data
        """
        return self.store.read_ticks(symbol, start, end, columns)

    def delete(
        self,
        symbol: str,
        timeframe: Timeframe | None = None,
        partition: str | None = None,
    ) -> dict[str, Any]:
        """
        Delete data and catalog entries.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (None for ticks)
            partition: Partition identifier (None = all partitions)

        Returns:
            Dictionary with deletion results
        """
        # Delete from storage
        files_deleted = self.store.delete_data(symbol, timeframe, partition)

        # Delete from catalog
        if partition:
            self.catalog.delete_entry(symbol, timeframe, partition)
            entries_deleted = 1
        else:
            # Delete all partitions
            partitions = self.catalog.list_partitions(symbol, timeframe)
            entries_deleted = 0
            for p in partitions:
                if self.catalog.delete_entry(symbol, timeframe, p):
                    entries_deleted += 1

        logger.info(
            f"Deleted {symbol} {timeframe} {partition}: "
            f"{files_deleted} files, {entries_deleted} catalog entries"
        )

        return {
            "files_deleted": files_deleted,
            "entries_deleted": entries_deleted,
        }

    def get_stats(self) -> dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with statistics from catalog
        """
        return self.catalog.get_stats()
