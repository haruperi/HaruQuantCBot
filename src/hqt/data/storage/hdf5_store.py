"""
HDF5 storage backend for HQT Trading System.

This module implements the DataStore interface using HDF5 format
with h5py for efficient chunked storage and retrieval.

[REQ: DAT-FR-021] HDF5 format storage
[SDD: §5.2] Data Storage Architecture
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd

from hqt.data.models.bar import Timeframe
from hqt.data.storage.base import DataStore
from hqt.foundation.exceptions.data import DataError


class HDF5Store(DataStore):
    """
    HDF5 storage backend.

    Stores tick and bar data in HDF5 format using h5py.
    Provides chunked storage, compression, and efficient I/O.

    Features:
        - Chunked storage for efficient partial reads
        - GZIP compression (level 4)
        - INT64 fixed-point encoding for prices
        - Memory-mapped file access support
        - Automatic directory structure

    File Organization:
        ```
        {base_path}/
        ├── EURUSD/
        │   ├── ticks/
        │   │   ├── 2024-01.h5
        │   │   └── 2024-02.h5
        │   ├── M1/
        │   │   ├── 2024.h5
        │   │   └── 2025.h5
        │   └── H1/
        │       └── 2024.h5
        └── GBPUSD/
            └── ...
        ```

    Example:
        ```python
        from hqt.data.storage import HDF5Store
        from hqt.data.models import Timeframe
        import pandas as pd

        store = HDF5Store("data/hdf5")

        # Write bars
        bars = pd.DataFrame({...})
        store.write_bars("EURUSD", Timeframe.H1, bars, partition="2024")

        # Read bars
        bars = store.read_bars("EURUSD", Timeframe.H1)

        # Read specific columns
        closes = store.read_bars(
            "EURUSD",
            Timeframe.H1,
            columns=["timestamp", "close"],
        )
        ```

    Note:
        HDF5 files support memory-mapped access via h5py's driver='core'
        parameter for zero-copy reads in C++.
    """

    # Price scaling factor (6 decimal places)
    PRICE_SCALE = 1_000_000

    # Chunk size (rows per chunk)
    CHUNK_SIZE = 10000

    def __init__(self, base_path: str | Path = "data/hdf5"):
        """
        Initialize HDF5 store.

        Args:
            base_path: Base directory for HDF5 files
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
        """Write bar data to HDF5 file."""
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
            filename = f"{partition}.h5"
        else:
            filename = "all.h5"

        file_path = symbol_dir / filename

        # Convert to structured array with fixed-point prices
        dtype = np.dtype(
            [
                ("timestamp", "i8"),
                ("open", "i8"),
                ("high", "i8"),
                ("low", "i8"),
                ("close", "i8"),
                ("tick_volume", "i8"),
                ("real_volume", "i8"),
                ("spread", "i4"),
            ]
        )

        array = np.zeros(len(data), dtype=dtype)
        array["timestamp"] = data["timestamp"].values
        array["open"] = (data["open"].values * self.PRICE_SCALE).astype("int64")
        array["high"] = (data["high"].values * self.PRICE_SCALE).astype("int64")
        array["low"] = (data["low"].values * self.PRICE_SCALE).astype("int64")
        array["close"] = (data["close"].values * self.PRICE_SCALE).astype("int64")
        array["tick_volume"] = data["tick_volume"].values
        array["real_volume"] = data["real_volume"].values
        array["spread"] = data["spread"].values

        # Write to HDF5
        try:
            with h5py.File(file_path, "w") as f:
                # Determine chunk size (can't be larger than data)
                chunk_size = min(len(array), self.CHUNK_SIZE)
                f.create_dataset(
                    "bars",
                    data=array,
                    chunks=(chunk_size,) if chunk_size > 0 else None,
                    compression="gzip",
                    compression_opts=4,
                )
                # Store metadata
                f.attrs["symbol"] = symbol
                f.attrs["timeframe"] = timeframe.name
                f.attrs["partition"] = partition if partition else "all"
                f.attrs["row_count"] = len(array)
        except Exception as e:
            raise DataError(
                error_code="DAT-032",
                module="data.storage.hdf5",
                message=f"Failed to write HDF5 file: {e}",
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
        """Write tick data to HDF5 file."""
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
            filename = f"{partition}.h5"
        else:
            filename = "all.h5"

        file_path = symbol_dir / filename

        # Convert to structured array
        dtype = np.dtype(
            [
                ("timestamp", "i8"),
                ("bid", "i8"),
                ("ask", "i8"),
                ("bid_volume", "i8"),
                ("ask_volume", "i8"),
            ]
        )

        array = np.zeros(len(data), dtype=dtype)
        array["timestamp"] = data["timestamp"].values
        array["bid"] = (data["bid"].values * self.PRICE_SCALE).astype("int64")
        array["ask"] = (data["ask"].values * self.PRICE_SCALE).astype("int64")
        array["bid_volume"] = data["bid_volume"].values
        array["ask_volume"] = data["ask_volume"].values

        # Write to HDF5
        try:
            with h5py.File(file_path, "w") as f:
                # Determine chunk size (can't be larger than data)
                chunk_size = min(len(array), self.CHUNK_SIZE)
                f.create_dataset(
                    "ticks",
                    data=array,
                    chunks=(chunk_size,) if chunk_size > 0 else None,
                    compression="gzip",
                    compression_opts=4,
                )
                # Store metadata
                f.attrs["symbol"] = symbol
                f.attrs["partition"] = partition if partition else "all"
                f.attrs["row_count"] = len(array)
        except Exception as e:
            raise DataError(
                error_code="DAT-032",
                module="data.storage.hdf5",
                message=f"Failed to write HDF5 file: {e}",
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
        """Read bar data from HDF5 file."""
        symbol_dir = self.base_path / symbol / timeframe.name

        if not symbol_dir.exists():
            raise FileNotFoundError(
                f"No data found for {symbol} {timeframe.name}"
            )

        # Determine files to read
        if partition:
            files = [symbol_dir / f"{partition}.h5"]
        else:
            files = sorted(symbol_dir.glob("*.h5"))

        if not files:
            raise FileNotFoundError(f"No HDF5 files found in {symbol_dir}")

        # Read files
        dfs = []
        for file_path in files:
            try:
                with h5py.File(file_path, "r") as f:
                    dataset = f["bars"]
                    data = dataset[:]

                    # Convert to DataFrame
                    df = pd.DataFrame(data)

                    # Filter by time if needed
                    if start:
                        start_us = int(start.timestamp() * 1_000_000)
                        df = df[df["timestamp"] >= start_us]
                    if end:
                        end_us = int(end.timestamp() * 1_000_000)
                        df = df[df["timestamp"] < end_us]

                    if len(df) > 0:
                        dfs.append(df)
            except Exception as e:
                raise DataError(
                    error_code="DAT-033",
                    module="data.storage.hdf5",
                    message=f"Failed to read HDF5 file: {e}",
                    file_path=str(file_path),
                )

        if not dfs:
            # Return empty DataFrame
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
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype("float64") / self.PRICE_SCALE

        # Select columns if specified
        if columns:
            df = df[columns]

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
        """Read tick data from HDF5 file."""
        symbol_dir = self.base_path / symbol / "ticks"

        if not symbol_dir.exists():
            raise FileNotFoundError(f"No tick data found for {symbol}")

        # Determine files to read
        if partition:
            files = [symbol_dir / f"{partition}.h5"]
        else:
            files = sorted(symbol_dir.glob("*.h5"))

        if not files:
            raise FileNotFoundError(f"No HDF5 files found in {symbol_dir}")

        # Read files
        dfs = []
        for file_path in files:
            try:
                with h5py.File(file_path, "r") as f:
                    dataset = f["ticks"]
                    data = dataset[:]

                    # Convert to DataFrame
                    df = pd.DataFrame(data)

                    # Filter by time if needed
                    if start:
                        start_us = int(start.timestamp() * 1_000_000)
                        df = df[df["timestamp"] >= start_us]
                    if end:
                        end_us = int(end.timestamp() * 1_000_000)
                        df = df[df["timestamp"] < end_us]

                    if len(df) > 0:
                        dfs.append(df)
            except Exception as e:
                raise DataError(
                    error_code="DAT-033",
                    module="data.storage.hdf5",
                    message=f"Failed to read HDF5 file: {e}",
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
            df[col] = df[col].astype("float64") / self.PRICE_SCALE

        # Select columns if specified
        if columns:
            df = df[columns]

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
        for file_path in data_dir.glob("*.h5"):
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
            file_path = data_dir / f"{partition}.h5"
            if file_path.exists():
                file_path.unlink()
                deleted = 1
        else:
            for file_path in data_dir.glob("*.h5"):
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
            dataset_name = "bars"
        else:
            data_dir = self.base_path / symbol / "ticks"
            dataset_name = "ticks"

        if partition:
            file_path = data_dir / f"{partition}.h5"
        else:
            file_path = data_dir / "all.h5"

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read HDF5 metadata
        with h5py.File(file_path, "r") as f:
            dataset = f[dataset_name]
            row_count = len(dataset)

            # Get timestamp range
            timestamps = dataset["timestamp"]
            min_ts = int(timestamps[0]) if row_count > 0 else None
            max_ts = int(timestamps[-1]) if row_count > 0 else None

            columns = list(dataset.dtype.names)

        return {
            "path": str(file_path),
            "size_bytes": file_path.stat().st_size,
            "row_count": row_count,
            "date_range": (min_ts, max_ts) if min_ts and max_ts else None,
            "columns": columns,
            "compression": "gzip",
            "chunk_size": self.CHUNK_SIZE,
        }
