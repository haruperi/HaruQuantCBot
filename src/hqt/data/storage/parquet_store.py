"""
Apache Parquet storage backend for HQT Trading System.

This module implements the DataStore interface using Apache Parquet format
with PyArrow for efficient columnar storage and retrieval.

[REQ: DAT-FR-021] Parquet format storage
[REQ: DAT-FR-023] Columnar access
[SDD: §5.2] Data Storage Architecture
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from hqt.data.models.bar import Timeframe
from hqt.data.storage.base import DataStore
from hqt.foundation.exceptions.data import DataError


class ParquetStore(DataStore):
    """
    Apache Parquet storage backend.

    Stores tick and bar data in Apache Parquet format using PyArrow.
    Provides efficient columnar access, compression, and predicate pushdown.

    Features:
        - INT64 fixed-point encoding for prices (6 decimal places)
        - DELTA_BINARY_PACKED compression for timestamps and prices
        - RLE encoding for spread
        - Columnar access (read only needed columns)
        - Predicate pushdown (filter at read time)
        - Automatic directory structure

    File Organization:
        ```
        {base_path}/
        ├── EURUSD/
        │   ├── ticks/
        │   │   ├── 2024-01.parquet
        │   │   └── 2024-02.parquet
        │   ├── M1/
        │   │   ├── 2024.parquet
        │   │   └── 2025.parquet
        │   └── H1/
        │       └── 2024.parquet
        └── GBPUSD/
            └── ...
        ```

    Example:
        ```python
        from hqt.data.storage import ParquetStore
        from hqt.data.models import Timeframe
        from datetime import datetime
        import pandas as pd

        store = ParquetStore("data/parquet")

        # Write bars
        bars = pd.DataFrame({
            'timestamp': [...],
            'open': [...],
            'high': [...],
            'low': [...],
            'close': [...],
            'tick_volume': [...],
            'real_volume': [...],
            'spread': [...],
        })
        store.write_bars("EURUSD", Timeframe.H1, bars, partition="2024")

        # Read all bars
        all_bars = store.read_bars("EURUSD", Timeframe.H1)

        # Read time range (predicate pushdown)
        bars_2024 = store.read_bars(
            "EURUSD",
            Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
        )

        # Read specific columns only (columnar access)
        closes = store.read_bars(
            "EURUSD",
            Timeframe.H1,
            columns=["timestamp", "close"],
        )
        ```

    Note:
        Prices are stored as INT64 with 6 decimal places (multiply by 1,000,000).
        This provides exact precision for forex pairs and avoids floating-point errors.
    """

    # Price scaling factor (6 decimal places)
    PRICE_SCALE = 1_000_000

    def __init__(self, base_path: str | Path = "data/parquet"):
        """
        Initialize Parquet store.

        Args:
            base_path: Base directory for Parquet files

        Note:
            Directory is created automatically if it doesn't exist.
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        data: pd.DataFrame,
        partition: str | None = None,
    ) -> Path:
        """
        Write bar data to Parquet file.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe
            data: DataFrame with bar columns
            partition: Partition identifier (e.g., "2024")

        Returns:
            Path to written Parquet file

        Raises:
            ValueError: Missing required columns
            DataError: Write failed
        """
        # Validate columns
        required_cols = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
            "real_volume",
            "spread",
        ]
        missing = set(required_cols) - set(data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        if len(data) == 0:
            raise ValueError("Cannot write empty DataFrame")

        # Create directory structure
        symbol_dir = self.base_path / symbol / timeframe.name
        symbol_dir.mkdir(parents=True, exist_ok=True)

        # Determine filename
        if partition:
            filename = f"{partition}.parquet"
        else:
            filename = "all.parquet"

        file_path = symbol_dir / filename

        # Convert prices to fixed-point INT64
        df_scaled = data.copy()
        for col in ["open", "high", "low", "close"]:
            df_scaled[col] = (df_scaled[col] * self.PRICE_SCALE).astype("int64")

        # Create PyArrow table with optimized schema
        schema = pa.schema(
            [
                pa.field(
                    "timestamp",
                    pa.int64(),
                    metadata={"encoding": "DELTA_BINARY_PACKED"},
                ),
                pa.field(
                    "open", pa.int64(), metadata={"encoding": "DELTA_BINARY_PACKED"}
                ),
                pa.field(
                    "high", pa.int64(), metadata={"encoding": "DELTA_BINARY_PACKED"}
                ),
                pa.field(
                    "low", pa.int64(), metadata={"encoding": "DELTA_BINARY_PACKED"}
                ),
                pa.field(
                    "close", pa.int64(), metadata={"encoding": "DELTA_BINARY_PACKED"}
                ),
                pa.field("tick_volume", pa.int64()),
                pa.field("real_volume", pa.int64()),
                pa.field("spread", pa.int32(), metadata={"encoding": "RLE"}),
            ]
        )

        table = pa.Table.from_pandas(df_scaled, schema=schema, preserve_index=False)

        # Write with compression
        try:
            pq.write_table(
                table,
                file_path,
                compression="snappy",
                use_dictionary=True,
                write_statistics=True,
            )
        except Exception as e:
            raise DataError(
                error_code="DAT-030",
                module="data.storage.parquet",
                message=f"Failed to write Parquet file: {e}",
                file_path=str(file_path),
                symbol=symbol,
                timeframe=timeframe.name,
            )

        return file_path

    def write_ticks(
        self,
        symbol: str,
        data: pd.DataFrame,
        partition: str | None = None,
    ) -> Path:
        """
        Write tick data to Parquet file.

        Args:
            symbol: Trading symbol
            data: DataFrame with tick columns
            partition: Partition identifier (e.g., "2024-01")

        Returns:
            Path to written Parquet file

        Raises:
            ValueError: Missing required columns
            DataError: Write failed
        """
        # Validate columns
        required_cols = ["timestamp", "bid", "ask", "bid_volume", "ask_volume"]
        missing = set(required_cols) - set(data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        if len(data) == 0:
            raise ValueError("Cannot write empty DataFrame")

        # Create directory structure
        symbol_dir = self.base_path / symbol / "ticks"
        symbol_dir.mkdir(parents=True, exist_ok=True)

        # Determine filename
        if partition:
            filename = f"{partition}.parquet"
        else:
            filename = "all.parquet"

        file_path = symbol_dir / filename

        # Convert prices to fixed-point INT64
        df_scaled = data.copy()
        df_scaled["bid"] = (df_scaled["bid"] * self.PRICE_SCALE).astype("int64")
        df_scaled["ask"] = (df_scaled["ask"] * self.PRICE_SCALE).astype("int64")

        # Create PyArrow table
        schema = pa.schema(
            [
                pa.field(
                    "timestamp",
                    pa.int64(),
                    metadata={"encoding": "DELTA_BINARY_PACKED"},
                ),
                pa.field(
                    "bid", pa.int64(), metadata={"encoding": "DELTA_BINARY_PACKED"}
                ),
                pa.field(
                    "ask", pa.int64(), metadata={"encoding": "DELTA_BINARY_PACKED"}
                ),
                pa.field("bid_volume", pa.int64()),
                pa.field("ask_volume", pa.int64()),
            ]
        )

        table = pa.Table.from_pandas(df_scaled, schema=schema, preserve_index=False)

        # Write with compression
        try:
            pq.write_table(
                table,
                file_path,
                compression="snappy",
                use_dictionary=True,
                write_statistics=True,
            )
        except Exception as e:
            raise DataError(
                error_code="DAT-030",
                module="data.storage.parquet",
                message=f"Failed to write Parquet file: {e}",
                file_path=str(file_path),
                symbol=symbol,
            )

        return file_path

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
        Read bar data from Parquet file.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe
            start: Start datetime (UTC, inclusive)
            end: End datetime (UTC, exclusive)
            columns: Columns to read (None = all)
            partition: Partition identifier (None = all partitions)

        Returns:
            DataFrame with bar data (prices as float64)

        Raises:
            FileNotFoundError: Data not found
        """
        symbol_dir = self.base_path / symbol / timeframe.name

        if not symbol_dir.exists():
            raise FileNotFoundError(
                f"No data found for {symbol} {timeframe.name}"
            )

        # Determine files to read
        if partition:
            files = [symbol_dir / f"{partition}.parquet"]
        else:
            files = sorted(symbol_dir.glob("*.parquet"))

        if not files:
            raise FileNotFoundError(
                f"No Parquet files found in {symbol_dir}"
            )

        # Build time filter
        filters = []
        if start:
            start_us = int(start.timestamp() * 1_000_000)
            filters.append(("timestamp", ">=", start_us))
        if end:
            end_us = int(end.timestamp() * 1_000_000)
            filters.append(("timestamp", "<", end_us))

        # Read files
        dfs = []
        for file_path in files:
            try:
                df = pq.read_table(
                    file_path,
                    columns=columns,
                    filters=filters if filters else None,
                ).to_pandas()
                if len(df) > 0:
                    dfs.append(df)
            except Exception as e:
                raise DataError(
                    error_code="DAT-031",
                    module="data.storage.parquet",
                    message=f"Failed to read Parquet file: {e}",
                    file_path=str(file_path),
                )

        if not dfs:
            # Return empty DataFrame with correct columns
            cols = columns if columns else [
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "tick_volume",
                "real_volume",
                "spread",
            ]
            return pd.DataFrame(columns=cols)

        # Combine files
        df = pd.concat(dfs, ignore_index=True)

        # Convert fixed-point back to float
        price_cols = [c for c in ["open", "high", "low", "close"] if c in df.columns]
        for col in price_cols:
            df[col] = df[col].astype("float64") / self.PRICE_SCALE

        # Sort by timestamp
        df = df.sort_values("timestamp").reset_index(drop=True)

        return df

    def read_ticks(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
        columns: list[str] | None = None,
        partition: str | None = None,
    ) -> pd.DataFrame:
        """
        Read tick data from Parquet file.

        Args:
            symbol: Trading symbol
            start: Start datetime (UTC, inclusive)
            end: End datetime (UTC, exclusive)
            columns: Columns to read (None = all)
            partition: Partition identifier (None = all partitions)

        Returns:
            DataFrame with tick data (prices as float64)

        Raises:
            FileNotFoundError: Data not found
        """
        symbol_dir = self.base_path / symbol / "ticks"

        if not symbol_dir.exists():
            raise FileNotFoundError(f"No tick data found for {symbol}")

        # Determine files to read
        if partition:
            files = [symbol_dir / f"{partition}.parquet"]
        else:
            files = sorted(symbol_dir.glob("*.parquet"))

        if not files:
            raise FileNotFoundError(
                f"No Parquet files found in {symbol_dir}"
            )

        # Build time filter
        filters = []
        if start:
            start_us = int(start.timestamp() * 1_000_000)
            filters.append(("timestamp", ">=", start_us))
        if end:
            end_us = int(end.timestamp() * 1_000_000)
            filters.append(("timestamp", "<", end_us))

        # Read files
        dfs = []
        for file_path in files:
            try:
                df = pq.read_table(
                    file_path,
                    columns=columns,
                    filters=filters if filters else None,
                ).to_pandas()
                if len(df) > 0:
                    dfs.append(df)
            except Exception as e:
                raise DataError(
                    error_code="DAT-031",
                    module="data.storage.parquet",
                    message=f"Failed to read Parquet file: {e}",
                    file_path=str(file_path),
                )

        if not dfs:
            # Return empty DataFrame
            cols = columns if columns else [
                "timestamp",
                "bid",
                "ask",
                "bid_volume",
                "ask_volume",
            ]
            return pd.DataFrame(columns=cols)

        # Combine files
        df = pd.concat(dfs, ignore_index=True)

        # Convert fixed-point back to float
        for col in ["bid", "ask"]:
            if col in df.columns:
                df[col] = df[col].astype("float64") / self.PRICE_SCALE

        # Sort by timestamp
        df = df.sort_values("timestamp").reset_index(drop=True)

        return df

    def list_symbols(self) -> list[str]:
        """List all symbols with stored data."""
        if not self.base_path.exists():
            return []

        symbols = []
        for item in self.base_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                symbols.append(item.name)

        return sorted(symbols)

    def list_timeframes(self, symbol: str) -> list[Timeframe]:
        """List all timeframes available for a symbol."""
        symbol_dir = self.base_path / symbol

        if not symbol_dir.exists():
            return []

        timeframes = []
        for item in symbol_dir.iterdir():
            if item.is_dir() and item.name != "ticks":
                try:
                    tf = Timeframe[item.name]
                    timeframes.append(tf)
                except KeyError:
                    pass

        return sorted(timeframes, key=lambda x: x.value)

    def list_partitions(
        self,
        symbol: str,
        timeframe: Timeframe | None = None,
    ) -> list[str]:
        """List all partitions for a symbol/timeframe."""
        if timeframe:
            data_dir = self.base_path / symbol / timeframe.name
        else:
            data_dir = self.base_path / symbol / "ticks"

        if not data_dir.exists():
            return []

        partitions = []
        for file_path in data_dir.glob("*.parquet"):
            # Extract partition from filename (remove .parquet extension)
            partition = file_path.stem
            if partition != "all":
                partitions.append(partition)

        return sorted(partitions)

    def delete_data(
        self,
        symbol: str,
        timeframe: Timeframe | None = None,
        partition: str | None = None,
    ) -> int:
        """Delete stored data."""
        if timeframe:
            data_dir = self.base_path / symbol / timeframe.name
        else:
            data_dir = self.base_path / symbol / "ticks"

        if not data_dir.exists():
            return 0

        deleted = 0

        if partition:
            # Delete specific partition
            file_path = data_dir / f"{partition}.parquet"
            if file_path.exists():
                file_path.unlink()
                deleted = 1
        else:
            # Delete all files in directory
            for file_path in data_dir.glob("*.parquet"):
                file_path.unlink()
                deleted += 1

            # Remove empty directory
            if deleted > 0 and not any(data_dir.iterdir()):
                data_dir.rmdir()

        return deleted

    def get_file_info(
        self,
        symbol: str,
        timeframe: Timeframe | None = None,
        partition: str | None = None,
    ) -> dict[str, Any]:
        """Get metadata about stored file."""
        if timeframe:
            data_dir = self.base_path / symbol / timeframe.name
        else:
            data_dir = self.base_path / symbol / "ticks"

        if partition:
            file_path = data_dir / f"{partition}.parquet"
        else:
            file_path = data_dir / "all.parquet"

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read Parquet metadata
        parquet_file = pq.ParquetFile(file_path)
        metadata = parquet_file.metadata

        # Get timestamp range
        schema = parquet_file.schema_arrow
        timestamp_stats = metadata.row_group(0).column(0).statistics
        min_ts = timestamp_stats.min if timestamp_stats else None
        max_ts = timestamp_stats.max if timestamp_stats else None

        return {
            "path": str(file_path),
            "size_bytes": file_path.stat().st_size,
            "row_count": metadata.num_rows,
            "date_range": (min_ts, max_ts) if min_ts and max_ts else None,
            "columns": schema.names,
            "num_row_groups": metadata.num_row_groups,
            "compression": str(metadata.row_group(0).column(0).compression),
        }
