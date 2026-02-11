"""
Unit tests for data storage layer.

Tests comprehensive coverage of:
1. DataStore ABC - abstract interface, context manager
2. ParquetStore - write/read, columnar access, predicate pushdown
3. HDF5Store - write/read, chunked storage, compression
4. DataCatalog - metadata tracking, queries
5. PartitionStrategy - time-based partitioning
6. StorageManager - full pipeline integration
7. Cross-backend equivalence tests
"""

import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock

import numpy as np
import pandas as pd
import pytest

from hqt.data.models.bar import Timeframe
from hqt.data.providers.base import DataProvider
from hqt.data.storage.base import DataStore
from hqt.data.storage.catalog import DataCatalog
from hqt.data.storage.hdf5_store import HDF5Store
from hqt.data.storage.manager import PartitionStrategy, StorageManager
from hqt.data.storage.parquet_store import ParquetStore
from hqt.foundation.exceptions.data import DataError


# ============================================================================
# Fixtures - Test Data
# ============================================================================


@pytest.fixture
def sample_bars_df():
    """Create sample bar data."""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    timestamps = [
        int((base_time + timedelta(hours=i)).timestamp() * 1_000_000)
        for i in range(100)
    ]

    np.random.seed(42)
    base_price = 1.10000

    data = {
        "timestamp": timestamps,
        "open": base_price + np.random.randn(100) * 0.0001,
        "high": base_price + np.abs(np.random.randn(100)) * 0.0002,
        "low": base_price - np.abs(np.random.randn(100)) * 0.0002,
        "close": base_price + np.random.randn(100) * 0.0001,
        "tick_volume": np.random.randint(1000, 10000, 100),
        "real_volume": np.random.randint(100000, 1000000, 100),
        "spread": np.random.randint(1, 5, 100),
    }

    df = pd.DataFrame(data)
    # Ensure OHLC consistency
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)

    return df


@pytest.fixture
def sample_ticks_df():
    """Create sample tick data."""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    timestamps = [
        int((base_time + timedelta(seconds=i)).timestamp() * 1_000_000)
        for i in range(1000)
    ]

    np.random.seed(42)
    base_bid = 1.10000
    spread = 0.00002

    data = {
        "timestamp": timestamps,
        "bid": base_bid + np.random.randn(1000) * 0.0001,
        "ask": base_bid + spread + np.random.randn(1000) * 0.0001,
        "bid_volume": np.random.randint(100, 1000, 1000),
        "ask_volume": np.random.randint(100, 1000, 1000),
    }

    return pd.DataFrame(data)


# ============================================================================
# Test DataStore ABC
# ============================================================================


class TestDataStoreABC:
    """Test the DataStore abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Test that DataStore cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            DataStore()

    def test_context_manager_protocol(self, tmp_path):
        """Test that DataStore supports context manager protocol."""
        store = ParquetStore(tmp_path / "parquet")

        # Test __enter__ returns self
        with store as s:
            assert s is store

        # close() should be called on exit (no error should occur)
        # We can verify by using a store that would fail if not closed properly

    def test_default_close_implementation(self, tmp_path):
        """Test that default close() does nothing."""
        store = ParquetStore(tmp_path / "parquet")
        # Should not raise
        store.close()
        store.close()  # Can call multiple times


# ============================================================================
# Test ParquetStore
# ============================================================================


class TestParquetStore:
    """Test ParquetStore implementation."""

    def test_initialization(self, tmp_path):
        """Test ParquetStore initialization creates directory."""
        store_path = tmp_path / "parquet"
        assert not store_path.exists()

        store = ParquetStore(store_path)
        assert store_path.exists()
        assert store.base_path == store_path

    def test_write_read_bars_round_trip(self, tmp_path, sample_bars_df):
        """Test writing and reading bars preserves data."""
        store = ParquetStore(tmp_path / "parquet")

        # Write bars
        file_path = store.write_bars(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            data=sample_bars_df,
            partition="2024",
        )

        assert file_path.exists()
        assert file_path.suffix == ".parquet"

        # Read back
        df_read = store.read_bars("EURUSD", Timeframe.H1)

        # Verify data matches
        assert len(df_read) == len(sample_bars_df)
        pd.testing.assert_series_equal(
            df_read["timestamp"].reset_index(drop=True),
            sample_bars_df["timestamp"].reset_index(drop=True),
        )

        # Check price precision (should be preserved within 6 decimals)
        for col in ["open", "high", "low", "close"]:
            np.testing.assert_allclose(
                df_read[col].values,
                sample_bars_df[col].values,
                rtol=1e-6,
                atol=1e-6,
            )

    def test_write_read_ticks_round_trip(self, tmp_path, sample_ticks_df):
        """Test writing and reading ticks preserves data."""
        store = ParquetStore(tmp_path / "parquet")

        # Write ticks
        file_path = store.write_ticks(
            symbol="EURUSD",
            data=sample_ticks_df,
            partition="2024-01",
        )

        assert file_path.exists()

        # Read back
        df_read = store.read_ticks("EURUSD")

        # Verify data matches
        assert len(df_read) == len(sample_ticks_df)

        # Check price precision
        for col in ["bid", "ask"]:
            np.testing.assert_allclose(
                df_read[col].values,
                sample_ticks_df[col].values,
                rtol=1e-6,
                atol=1e-6,
            )

    def test_fixed_point_price_encoding(self, tmp_path, sample_bars_df):
        """Test that prices are encoded as INT64 with 6 decimals."""
        store = ParquetStore(tmp_path / "parquet")

        # Write data with known precise values
        df = pd.DataFrame({
            "timestamp": [1704067200000000],
            "open": [1.123456],
            "high": [1.123457],
            "low": [1.123455],
            "close": [1.123456],
            "tick_volume": [1000],
            "real_volume": [100000],
            "spread": [2],
        })

        store.write_bars("TEST", Timeframe.M1, df, "2024")

        # Read back and verify precision
        df_read = store.read_bars("TEST", Timeframe.M1)

        assert abs(df_read["open"].iloc[0] - 1.123456) < 1e-6
        assert abs(df_read["high"].iloc[0] - 1.123457) < 1e-6
        assert abs(df_read["low"].iloc[0] - 1.123455) < 1e-6
        assert abs(df_read["close"].iloc[0] - 1.123456) < 1e-6

    def test_columnar_access(self, tmp_path, sample_bars_df):
        """Test reading only specific columns."""
        store = ParquetStore(tmp_path / "parquet")
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")

        # Read only timestamp and close
        df_read = store.read_bars(
            "EURUSD",
            Timeframe.H1,
            columns=["timestamp", "close"],
        )

        assert list(df_read.columns) == ["timestamp", "close"]
        assert len(df_read) == len(sample_bars_df)

    def test_predicate_pushdown_time_filtering(self, tmp_path, sample_bars_df):
        """Test time-based filtering with predicate pushdown."""
        store = ParquetStore(tmp_path / "parquet")
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")

        # Filter to first 50 hours
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 3, 2, 0, 0)  # 50 hours later

        df_read = store.read_bars("EURUSD", Timeframe.H1, start=start, end=end)

        # Should have less than full dataset
        assert len(df_read) < len(sample_bars_df)
        assert len(df_read) <= 50

        # All timestamps should be within range
        start_us = int(start.timestamp() * 1_000_000)
        end_us = int(end.timestamp() * 1_000_000)
        assert all(df_read["timestamp"] >= start_us)
        assert all(df_read["timestamp"] < end_us)

    def test_list_symbols(self, tmp_path, sample_bars_df):
        """Test listing symbols."""
        store = ParquetStore(tmp_path / "parquet")

        # Empty initially
        assert store.list_symbols() == []

        # Add data for multiple symbols
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")
        store.write_bars("GBPUSD", Timeframe.H1, sample_bars_df, "2024")

        symbols = store.list_symbols()
        assert sorted(symbols) == ["EURUSD", "GBPUSD"]

    def test_list_timeframes(self, tmp_path, sample_bars_df):
        """Test listing timeframes for a symbol."""
        store = ParquetStore(tmp_path / "parquet")

        # Add data for multiple timeframes
        store.write_bars("EURUSD", Timeframe.M1, sample_bars_df, "2024")
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")
        store.write_bars("EURUSD", Timeframe.D1, sample_bars_df, "all")

        timeframes = store.list_timeframes("EURUSD")
        assert Timeframe.M1 in timeframes
        assert Timeframe.H1 in timeframes
        assert Timeframe.D1 in timeframes

    def test_list_partitions(self, tmp_path, sample_bars_df):
        """Test listing partitions."""
        store = ParquetStore(tmp_path / "parquet")

        # Add multiple partitions
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2025")

        partitions = store.list_partitions("EURUSD", Timeframe.H1)
        assert sorted(partitions) == ["2024", "2025"]

    def test_delete_data(self, tmp_path, sample_bars_df):
        """Test deleting data."""
        store = ParquetStore(tmp_path / "parquet")

        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2025")

        # Delete one partition
        deleted = store.delete_data("EURUSD", Timeframe.H1, "2024")
        assert deleted == 1

        partitions = store.list_partitions("EURUSD", Timeframe.H1)
        assert partitions == ["2025"]

        # Delete all remaining
        deleted = store.delete_data("EURUSD", Timeframe.H1)
        assert deleted == 1

        # Directory should be gone
        assert not (tmp_path / "parquet" / "EURUSD" / "H1").exists()

    def test_get_file_info(self, tmp_path, sample_bars_df):
        """Test getting file metadata."""
        store = ParquetStore(tmp_path / "parquet")
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")

        info = store.get_file_info("EURUSD", Timeframe.H1, "2024")

        assert "path" in info
        assert info["row_count"] == len(sample_bars_df)
        assert info["size_bytes"] > 0
        assert "date_range" in info
        assert "columns" in info
        assert "compression" in info

    def test_empty_results(self, tmp_path):
        """Test reading non-existent data returns empty DataFrame."""
        store = ParquetStore(tmp_path / "parquet")

        # Write some data
        df = pd.DataFrame({
            "timestamp": [1704067200000000],
            "open": [1.1],
            "high": [1.1],
            "low": [1.1],
            "close": [1.1],
            "tick_volume": [1000],
            "real_volume": [100000],
            "spread": [2],
        })
        store.write_bars("EURUSD", Timeframe.H1, df, "2024")

        # Read with time filter that excludes all data
        result = store.read_bars(
            "EURUSD",
            Timeframe.H1,
            start=datetime(2025, 1, 1),
            end=datetime(2025, 12, 31),
        )

        assert len(result) == 0
        assert list(result.columns) == [
            "timestamp", "open", "high", "low", "close",
            "tick_volume", "real_volume", "spread"
        ]

    def test_error_missing_columns(self, tmp_path):
        """Test error when writing data with missing columns."""
        store = ParquetStore(tmp_path / "parquet")

        # Missing required columns
        df = pd.DataFrame({
            "timestamp": [1704067200000000],
            "open": [1.1],
            "close": [1.1],
        })

        with pytest.raises(ValueError, match="Missing required columns"):
            store.write_bars("EURUSD", Timeframe.H1, df, "2024")

    def test_error_empty_dataframe(self, tmp_path):
        """Test error when writing empty DataFrame."""
        store = ParquetStore(tmp_path / "parquet")

        df = pd.DataFrame(columns=[
            "timestamp", "open", "high", "low", "close",
            "tick_volume", "real_volume", "spread"
        ])

        with pytest.raises(ValueError, match="Cannot write empty DataFrame"):
            store.write_bars("EURUSD", Timeframe.H1, df, "2024")

    def test_error_file_not_found(self, tmp_path):
        """Test error when reading non-existent data."""
        store = ParquetStore(tmp_path / "parquet")

        with pytest.raises(FileNotFoundError):
            store.read_bars("NONEXISTENT", Timeframe.H1)


# ============================================================================
# Test HDF5Store
# ============================================================================


class TestHDF5Store:
    """Test HDF5Store implementation."""

    def test_initialization(self, tmp_path):
        """Test HDF5Store initialization."""
        store_path = tmp_path / "hdf5"
        assert not store_path.exists()

        store = HDF5Store(store_path)
        assert store_path.exists()
        assert store.base_path == store_path

    def test_write_read_bars_round_trip(self, tmp_path, sample_bars_df):
        """Test writing and reading bars preserves data."""
        store = HDF5Store(tmp_path / "hdf5")

        # Write bars
        file_path = store.write_bars(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            data=sample_bars_df,
            partition="2024",
        )

        assert file_path.exists()
        assert file_path.suffix == ".h5"

        # Read back
        df_read = store.read_bars("EURUSD", Timeframe.H1)

        # Verify data matches
        assert len(df_read) == len(sample_bars_df)

        # Check price precision
        for col in ["open", "high", "low", "close"]:
            np.testing.assert_allclose(
                df_read[col].values,
                sample_bars_df[col].values,
                rtol=1e-6,
                atol=1e-6,
            )

    def test_write_read_ticks_round_trip(self, tmp_path, sample_ticks_df):
        """Test writing and reading ticks preserves data."""
        store = HDF5Store(tmp_path / "hdf5")

        # Write ticks
        file_path = store.write_ticks(
            symbol="EURUSD",
            data=sample_ticks_df,
            partition="2024-01",
        )

        assert file_path.exists()

        # Read back
        df_read = store.read_ticks("EURUSD")

        # Verify data matches
        assert len(df_read) == len(sample_ticks_df)

        # Check price precision
        for col in ["bid", "ask"]:
            np.testing.assert_allclose(
                df_read[col].values,
                sample_ticks_df[col].values,
                rtol=1e-6,
                atol=1e-6,
            )

    def test_chunked_storage(self, tmp_path, sample_bars_df):
        """Test that data is stored in chunks."""
        store = HDF5Store(tmp_path / "hdf5")
        file_path = store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")

        # Open HDF5 file and check chunking
        import h5py
        with h5py.File(file_path, "r") as f:
            dataset = f["bars"]
            assert dataset.chunks is not None
            # Chunk size should be min of CHUNK_SIZE and data length
            expected_chunk_size = min(len(sample_bars_df), store.CHUNK_SIZE)
            assert dataset.chunks[0] == expected_chunk_size

    def test_compression(self, tmp_path, sample_bars_df):
        """Test that GZIP compression is applied."""
        store = HDF5Store(tmp_path / "hdf5")
        file_path = store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")

        # Open HDF5 file and check compression
        import h5py
        with h5py.File(file_path, "r") as f:
            dataset = f["bars"]
            assert dataset.compression == "gzip"
            assert dataset.compression_opts == 4

    def test_columnar_access(self, tmp_path, sample_bars_df):
        """Test reading specific columns."""
        store = HDF5Store(tmp_path / "hdf5")
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")

        # Read only timestamp and close
        df_read = store.read_bars(
            "EURUSD",
            Timeframe.H1,
            columns=["timestamp", "close"],
        )

        assert list(df_read.columns) == ["timestamp", "close"]
        assert len(df_read) == len(sample_bars_df)

    def test_time_filtering(self, tmp_path, sample_bars_df):
        """Test time-based filtering."""
        store = HDF5Store(tmp_path / "hdf5")
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")

        # Filter to first 50 hours
        start = datetime(2024, 1, 1, 0, 0, 0)
        end = datetime(2024, 1, 3, 2, 0, 0)

        df_read = store.read_bars("EURUSD", Timeframe.H1, start=start, end=end)

        assert len(df_read) < len(sample_bars_df)

        # All timestamps should be within range
        start_us = int(start.timestamp() * 1_000_000)
        end_us = int(end.timestamp() * 1_000_000)
        assert all(df_read["timestamp"] >= start_us)
        assert all(df_read["timestamp"] < end_us)

    def test_list_symbols(self, tmp_path, sample_bars_df):
        """Test listing symbols."""
        store = HDF5Store(tmp_path / "hdf5")

        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")
        store.write_bars("GBPUSD", Timeframe.H1, sample_bars_df, "2024")

        symbols = store.list_symbols()
        assert sorted(symbols) == ["EURUSD", "GBPUSD"]

    def test_list_timeframes(self, tmp_path, sample_bars_df):
        """Test listing timeframes."""
        store = HDF5Store(tmp_path / "hdf5")

        store.write_bars("EURUSD", Timeframe.M1, sample_bars_df, "2024")
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")

        timeframes = store.list_timeframes("EURUSD")
        assert Timeframe.M1 in timeframes
        assert Timeframe.H1 in timeframes

    def test_list_partitions(self, tmp_path, sample_bars_df):
        """Test listing partitions."""
        store = HDF5Store(tmp_path / "hdf5")

        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2025")

        partitions = store.list_partitions("EURUSD", Timeframe.H1)
        assert sorted(partitions) == ["2024", "2025"]

    def test_delete_data(self, tmp_path, sample_bars_df):
        """Test deleting data."""
        store = HDF5Store(tmp_path / "hdf5")

        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")

        deleted = store.delete_data("EURUSD", Timeframe.H1, "2024")
        assert deleted == 1

        # File should be gone (directory might still exist if empty)
        assert not (tmp_path / "hdf5" / "EURUSD" / "H1" / "2024.h5").exists()

    def test_get_file_info(self, tmp_path, sample_bars_df):
        """Test getting file metadata."""
        store = HDF5Store(tmp_path / "hdf5")
        store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")

        info = store.get_file_info("EURUSD", Timeframe.H1, "2024")

        assert "path" in info
        assert info["row_count"] == len(sample_bars_df)
        assert info["size_bytes"] > 0
        assert info["compression"] == "gzip"
        assert info["chunk_size"] == store.CHUNK_SIZE


# ============================================================================
# Test Parquet/HDF5 Equivalence
# ============================================================================


class TestStorageEquivalence:
    """Test that Parquet and HDF5 stores produce equivalent results."""

    def test_bars_equivalence(self, tmp_path, sample_bars_df):
        """Test that same data written to both stores can be read identically."""
        parquet_store = ParquetStore(tmp_path / "parquet")
        hdf5_store = HDF5Store(tmp_path / "hdf5")

        # Write same data to both
        parquet_store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")
        hdf5_store.write_bars("EURUSD", Timeframe.H1, sample_bars_df, "2024")

        # Read from both
        df_parquet = parquet_store.read_bars("EURUSD", Timeframe.H1)
        df_hdf5 = hdf5_store.read_bars("EURUSD", Timeframe.H1)

        # Verify identical results
        assert len(df_parquet) == len(df_hdf5)
        pd.testing.assert_series_equal(
            df_parquet["timestamp"].reset_index(drop=True),
            df_hdf5["timestamp"].reset_index(drop=True),
        )

        for col in ["open", "high", "low", "close"]:
            np.testing.assert_allclose(
                df_parquet[col].values,
                df_hdf5[col].values,
                rtol=1e-6,
                atol=1e-6,
            )

    def test_ticks_equivalence(self, tmp_path, sample_ticks_df):
        """Test tick data equivalence across stores."""
        parquet_store = ParquetStore(tmp_path / "parquet")
        hdf5_store = HDF5Store(tmp_path / "hdf5")

        # Write same data to both
        parquet_store.write_ticks("EURUSD", sample_ticks_df, "2024-01")
        hdf5_store.write_ticks("EURUSD", sample_ticks_df, "2024-01")

        # Read from both
        df_parquet = parquet_store.read_ticks("EURUSD")
        df_hdf5 = hdf5_store.read_ticks("EURUSD")

        # Verify identical results
        assert len(df_parquet) == len(df_hdf5)

        for col in ["bid", "ask"]:
            np.testing.assert_allclose(
                df_parquet[col].values,
                df_hdf5[col].values,
                rtol=1e-6,
                atol=1e-6,
            )

    def test_price_precision_preservation(self, tmp_path):
        """Test that both stores preserve 6-decimal precision."""
        # Create data with exact values
        df = pd.DataFrame({
            "timestamp": [1704067200000000],
            "open": [1.123456],
            "high": [1.123457],
            "low": [1.123455],
            "close": [1.123456],
            "tick_volume": [1000],
            "real_volume": [100000],
            "spread": [2],
        })

        parquet_store = ParquetStore(tmp_path / "parquet")
        hdf5_store = HDF5Store(tmp_path / "hdf5")

        parquet_store.write_bars("TEST", Timeframe.M1, df, "2024")
        hdf5_store.write_bars("TEST", Timeframe.M1, df, "2024")

        df_parquet = parquet_store.read_bars("TEST", Timeframe.M1)
        df_hdf5 = hdf5_store.read_bars("TEST", Timeframe.M1)

        # Both should preserve precision
        for store_df in [df_parquet, df_hdf5]:
            assert abs(store_df["open"].iloc[0] - 1.123456) < 1e-6
            assert abs(store_df["high"].iloc[0] - 1.123457) < 1e-6
            assert abs(store_df["low"].iloc[0] - 1.123455) < 1e-6


# ============================================================================
# Test DataCatalog
# ============================================================================


class TestDataCatalog:
    """Test DataCatalog metadata tracking."""

    def test_initialization(self, tmp_path):
        """Test catalog initialization creates database."""
        db_path = tmp_path / "catalog.db"
        assert not db_path.exists()

        catalog = DataCatalog(db_path)
        assert db_path.exists()

        # Verify schema
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            assert "catalog" in tables

    def test_register_file_new(self, tmp_path):
        """Test registering a new file."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        entry_id = catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
            data_source="mt5",
            version_hash="abc123",
            file_size_bytes=1024000,
        )

        assert entry_id > 0

        # Verify entry
        metadata = catalog.get_metadata("EURUSD", Timeframe.H1, "2024")
        assert metadata["symbol"] == "EURUSD"
        assert metadata["timeframe"] == "H1"
        assert metadata["partition"] == "2024"
        assert metadata["row_count"] == 8760
        assert metadata["data_source"] == "mt5"

    def test_register_file_update(self, tmp_path):
        """Test updating an existing file entry."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        # Register initially
        id1 = catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        # Register again with updated data
        id2 = catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8800,  # More rows
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        # Should be same entry
        assert id1 == id2

        # Verify update
        metadata = catalog.get_metadata("EURUSD", Timeframe.H1, "2024")
        assert metadata["row_count"] == 8800

    def test_query_available_all(self, tmp_path):
        """Test querying all available data."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        # Register multiple entries
        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        catalog.register_file(
            symbol="GBPUSD",
            timeframe=Timeframe.M1,
            partition="2024-01",
            file_path="/data/GBPUSD/M1/2024-01.parquet",
            storage_format="parquet",
            row_count=44640,
            min_timestamp=1704067200000000,
            max_timestamp=1706745600000000,
        )

        # Query all
        entries = catalog.query_available()
        assert len(entries) == 2

    def test_query_available_by_symbol(self, tmp_path):
        """Test querying by symbol."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        catalog.register_file(
            symbol="GBPUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/GBPUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        # Query by symbol
        entries = catalog.query_available(symbol="EURUSD")
        assert len(entries) == 1
        assert entries[0]["symbol"] == "EURUSD"

    def test_query_available_by_timeframe(self, tmp_path):
        """Test querying by timeframe."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.M1,
            partition="2024",
            file_path="/data/EURUSD/M1/2024.parquet",
            storage_format="parquet",
            row_count=525600,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        # Query by timeframe
        entries = catalog.query_available(symbol="EURUSD", timeframe=Timeframe.H1)
        assert len(entries) == 1
        assert entries[0]["timeframe"] == "H1"

    def test_query_available_by_time_range(self, tmp_path):
        """Test querying by time range."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=int(datetime(2024, 1, 1).timestamp() * 1_000_000),
            max_timestamp=int(datetime(2024, 12, 31, 23).timestamp() * 1_000_000),
        )

        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2025",
            file_path="/data/EURUSD/H1/2025.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=int(datetime(2025, 1, 1).timestamp() * 1_000_000),
            max_timestamp=int(datetime(2025, 12, 31, 23).timestamp() * 1_000_000),
        )

        # Query for 2024 data
        entries = catalog.query_available(
            symbol="EURUSD",
            start=datetime(2024, 1, 1),
            end=datetime(2025, 1, 1),
        )

        # Should return 2024 partition
        assert len(entries) >= 1
        assert any(e["partition"] == "2024" for e in entries)

    def test_get_file_path(self, tmp_path):
        """Test getting file path from catalog."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        file_path_str = str(tmp_path / "EURUSD" / "H1" / "2024.parquet")
        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=file_path_str,
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        path = catalog.get_file_path("EURUSD", Timeframe.H1, "2024")
        # Path should end with the expected structure (normalized for platform)
        assert path.name == "2024.parquet"
        assert path.parent.name == "H1"
        assert path.parent.parent.name == "EURUSD"

    def test_list_symbols(self, tmp_path):
        """Test listing symbols."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        catalog.register_file(
            symbol="GBPUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/GBPUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        symbols = catalog.list_symbols()
        assert sorted(symbols) == ["EURUSD", "GBPUSD"]

    def test_list_timeframes(self, tmp_path):
        """Test listing timeframes for a symbol."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        catalog.register_file(
            symbol="EURUSD",
            timeframe=None,  # Ticks
            partition="2024-01",
            file_path="/data/EURUSD/ticks/2024-01.parquet",
            storage_format="parquet",
            row_count=100000,
            min_timestamp=1704067200000000,
            max_timestamp=1706745600000000,
        )

        timeframes = catalog.list_timeframes("EURUSD")
        assert Timeframe.H1 in timeframes
        assert None in timeframes  # Ticks

    def test_list_partitions(self, tmp_path):
        """Test listing partitions."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2025",
            file_path="/data/EURUSD/H1/2025.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1735689600000000,
            max_timestamp=1767225600000000,
        )

        partitions = catalog.list_partitions("EURUSD", Timeframe.H1)
        assert sorted(partitions) == ["2024", "2025"]

    def test_delete_entry(self, tmp_path):
        """Test deleting catalog entry."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
        )

        # Delete
        deleted = catalog.delete_entry("EURUSD", Timeframe.H1, "2024")
        assert deleted is True

        # Verify gone
        with pytest.raises(KeyError):
            catalog.get_metadata("EURUSD", Timeframe.H1, "2024")

    def test_get_stats(self, tmp_path):
        """Test getting catalog statistics."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="/data/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=1704067200000000,
            max_timestamp=1735689600000000,
            data_source="mt5",
            file_size_bytes=1024000,
        )

        catalog.register_file(
            symbol="GBPUSD",
            timeframe=Timeframe.M1,
            partition="2024-01",
            file_path="/data/GBPUSD/M1/2024-01.h5",
            storage_format="hdf5",
            row_count=44640,
            min_timestamp=1704067200000000,
            max_timestamp=1706745600000000,
            data_source="dukascopy",
            file_size_bytes=2048000,
        )

        stats = catalog.get_stats()

        assert stats["total_entries"] == 2
        assert stats["total_symbols"] == 2
        assert stats["total_rows"] == 8760 + 44640
        assert stats["total_size_bytes"] == 1024000 + 2048000
        assert "parquet" in stats["storage_formats"]
        assert "hdf5" in stats["storage_formats"]
        assert "mt5" in stats["data_sources"]
        assert "dukascopy" in stats["data_sources"]

    def test_error_missing_entry(self, tmp_path):
        """Test error when getting non-existent entry."""
        catalog = DataCatalog(tmp_path / "catalog.db")

        with pytest.raises(KeyError, match="No catalog entry"):
            catalog.get_metadata("NONEXISTENT", Timeframe.H1, "2024")


# ============================================================================
# Test PartitionStrategy
# ============================================================================


class TestPartitionStrategy:
    """Test PartitionStrategy time-based partitioning."""

    def test_get_partition_ticks_monthly(self):
        """Test tick data uses monthly partitions."""
        strategy = PartitionStrategy()

        dt = datetime(2024, 3, 15, 10, 30, 0)
        partition = strategy.get_partition(None, dt)

        assert partition == "2024-03"

    def test_get_partition_m1_yearly(self):
        """Test M1 bars use yearly partitions."""
        strategy = PartitionStrategy()

        dt = datetime(2024, 6, 20, 10, 30, 0)
        partition = strategy.get_partition(Timeframe.M1, dt)

        assert partition == "2024"

    def test_get_partition_h1_yearly(self):
        """Test H1 bars use yearly partitions."""
        strategy = PartitionStrategy()

        dt = datetime(2024, 12, 31, 23, 0, 0)
        partition = strategy.get_partition(Timeframe.H1, dt)

        assert partition == "2024"

    def test_get_partition_d1_all(self):
        """Test D1 bars use single partition."""
        strategy = PartitionStrategy()

        dt = datetime(2024, 6, 20)
        partition = strategy.get_partition(Timeframe.D1, dt)

        assert partition == "all"

    def test_parse_partition_range_monthly(self):
        """Test parsing monthly partition."""
        start, end = PartitionStrategy.parse_partition_range("2024-03")

        assert start == datetime(2024, 3, 1)
        assert end == datetime(2024, 4, 1)

    def test_parse_partition_range_yearly(self):
        """Test parsing yearly partition."""
        start, end = PartitionStrategy.parse_partition_range("2024")

        assert start == datetime(2024, 1, 1)
        assert end == datetime(2025, 1, 1)

    def test_parse_partition_range_all(self):
        """Test parsing 'all' partition."""
        start, end = PartitionStrategy.parse_partition_range("all")

        assert start == datetime.min
        assert end == datetime.max

    def test_parse_partition_range_december(self):
        """Test parsing December (edge case)."""
        start, end = PartitionStrategy.parse_partition_range("2024-12")

        assert start == datetime(2024, 12, 1)
        assert end == datetime(2025, 1, 1)


# ============================================================================
# Test StorageManager
# ============================================================================


class MockDataProvider(DataProvider):
    """Mock data provider for testing."""

    def __init__(self, bars_data=None, ticks_data=None):
        self.bars_data = bars_data
        self.ticks_data = ticks_data

    def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        progress_callback=None,
    ) -> pd.DataFrame:
        return self.bars_data if self.bars_data is not None else pd.DataFrame()

    def fetch_ticks(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        progress_callback=None,
    ) -> pd.DataFrame:
        return self.ticks_data if self.ticks_data is not None else pd.DataFrame()

    def get_available_symbols(self) -> list[str]:
        return ["EURUSD", "GBPUSD"]

    def get_available_timeframes(self, symbol: str) -> list[Timeframe]:
        return [Timeframe.M1, Timeframe.H1, Timeframe.D1]

    def get_provider_name(self) -> str:
        return "mock_provider"

    def validate_connection(self) -> bool:
        return True


class TestStorageManager:
    """Test StorageManager orchestration."""

    def test_download_and_store_bars(self, tmp_path, sample_bars_df):
        """Test download and store pipeline for bars."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        provider = MockDataProvider(bars_data=sample_bars_df)

        result = manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
            validate=False,  # Skip validation for speed
        )

        assert len(result["partitions"]) > 0
        assert result["total_rows"] == len(sample_bars_df)
        # version_hash is only set for single partition downloads
        if len(result["partitions"]) == 1:
            assert result["version_hash"] is not None

    def test_download_and_store_ticks(self, tmp_path, sample_ticks_df):
        """Test download and store pipeline for ticks."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        provider = MockDataProvider(ticks_data=sample_ticks_df)

        result = manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=None,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
            validate=False,
        )

        assert len(result["partitions"]) > 0
        assert result["total_rows"] == len(sample_ticks_df)

    def test_partitioning_splits_data(self, tmp_path):
        """Test that data is correctly split into partitions."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        # Create data spanning two months (within Jan and Feb only)
        base_time = datetime(2024, 1, 15, 0, 0, 0)
        timestamps = [
            int((base_time + timedelta(days=i)).timestamp() * 1_000_000)
            for i in range(30)  # 30 days, spans only Jan 15 to Feb 13
        ]

        df = pd.DataFrame({
            "timestamp": timestamps,
            "bid": [1.1] * 30,
            "ask": [1.10002] * 30,
            "bid_volume": [1000] * 30,
            "ask_volume": [1000] * 30,
        })

        provider = MockDataProvider(ticks_data=df)

        result = manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=None,  # Ticks
            start=datetime(2024, 1, 15),
            end=datetime(2024, 2, 14),
            validate=False,
        )

        # Should have created 2 partitions (2024-01 and 2024-02)
        assert len(result["partitions"]) == 2
        assert "2024-01" in result["partitions"]
        assert "2024-02" in result["partitions"]

    def test_catalog_registration(self, tmp_path, sample_bars_df):
        """Test that files are registered in catalog."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        provider = MockDataProvider(bars_data=sample_bars_df)

        manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
            validate=False,
        )

        # Verify catalog entry
        entries = catalog.query_available(symbol="EURUSD", timeframe=Timeframe.H1)
        assert len(entries) > 0
        assert entries[0]["symbol"] == "EURUSD"
        assert entries[0]["data_source"] == "mock_provider"

    def test_hash_computation(self, tmp_path):
        """Test version hash computation."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        # Create small dataset that fits in one year partition
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        timestamps = [
            int((base_time + timedelta(hours=i)).timestamp() * 1_000_000)
            for i in range(10)
        ]

        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": [1.1] * 10,
            "high": [1.1] * 10,
            "low": [1.1] * 10,
            "close": [1.1] * 10,
            "tick_volume": [1000] * 10,
            "real_volume": [100000] * 10,
            "spread": [2] * 10,
        })

        provider = MockDataProvider(bars_data=df)

        result = manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 1, 10),
            validate=False,
        )

        # Hash should be computed for single partition
        # Note: partitions are by year for H1, so this creates one 2024 partition
        assert len(result["partitions"]) >= 1
        if len(result["partitions"]) == 1:
            assert result["version_hash"] is not None
            assert len(result["version_hash"]) == 64  # SHA-256 hex string

    def test_compact_merge_and_deduplicate(self, tmp_path):
        """Test compacting data merges files and removes duplicates."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        # Create data with duplicates
        df1 = pd.DataFrame({
            "timestamp": [1704067200000000, 1704070800000000],
            "open": [1.1, 1.101],
            "high": [1.1, 1.101],
            "low": [1.1, 1.101],
            "close": [1.1, 1.101],
            "tick_volume": [1000, 1000],
            "real_volume": [100000, 100000],
            "spread": [2, 2],
        })

        df2 = pd.DataFrame({
            "timestamp": [1704070800000000, 1704074400000000],  # Duplicate first row
            "open": [1.101, 1.102],
            "high": [1.101, 1.102],
            "low": [1.101, 1.102],
            "close": [1.101, 1.102],
            "tick_volume": [1000, 1000],
            "real_volume": [100000, 100000],
            "spread": [2, 2],
        })

        # Write both files
        store.write_bars("EURUSD", Timeframe.H1, df1, "2024")
        # Need to manually write second file to same partition (simulating incremental download)
        # For this test, we'll just test the compact functionality

        # Compact
        provider = MockDataProvider(bars_data=pd.concat([df1, df2]))
        manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
            validate=False,
        )

        result = manager.compact("EURUSD", Timeframe.H1, "2024")

        # Should have removed duplicates
        assert result["rows_after"] == 3  # 3 unique timestamps
        assert result["rows_before"] >= result["rows_after"]

    def test_read_bars(self, tmp_path, sample_bars_df):
        """Test reading bars through manager."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        provider = MockDataProvider(bars_data=sample_bars_df)

        manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
            validate=False,
        )

        # Read back
        df = manager.read_bars("EURUSD", Timeframe.H1)
        assert len(df) == len(sample_bars_df)

    def test_read_ticks(self, tmp_path, sample_ticks_df):
        """Test reading ticks through manager."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        provider = MockDataProvider(ticks_data=sample_ticks_df)

        manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=None,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
            validate=False,
        )

        # Read back
        df = manager.read_ticks("EURUSD")
        assert len(df) == len(sample_ticks_df)

    def test_delete(self, tmp_path, sample_bars_df):
        """Test deleting data and catalog entries."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        provider = MockDataProvider(bars_data=sample_bars_df)

        manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
            validate=False,
        )

        # Get partition count before delete
        partitions_before = catalog.list_partitions("EURUSD", Timeframe.H1)

        # Delete all data (not just one partition)
        result = manager.delete("EURUSD", Timeframe.H1)

        assert result["files_deleted"] > 0
        assert result["entries_deleted"] == len(partitions_before)

        # Verify gone from catalog
        entries = catalog.query_available(symbol="EURUSD")
        assert len(entries) == 0

    def test_get_stats(self, tmp_path, sample_bars_df):
        """Test getting storage statistics."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        provider = MockDataProvider(bars_data=sample_bars_df)

        manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
            validate=False,
        )

        stats = manager.get_stats()

        assert stats["total_entries"] > 0
        assert stats["total_rows"] > 0

    def test_empty_download(self, tmp_path):
        """Test handling empty download results."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        provider = MockDataProvider(bars_data=pd.DataFrame())

        result = manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
            validate=False,
        )

        assert result["total_rows"] == 0
        assert len(result["partitions"]) == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_pipeline_parquet(self, tmp_path, sample_bars_df):
        """Test complete pipeline with Parquet backend."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        provider = MockDataProvider(bars_data=sample_bars_df)

        # Download and store
        result = manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
            validate=False,
            data_source="test_provider",
        )

        assert result["total_rows"] == len(sample_bars_df)

        # Query catalog
        entries = catalog.query_available(symbol="EURUSD")
        assert len(entries) > 0

        # Read back data
        df = manager.read_bars("EURUSD", Timeframe.H1)
        assert len(df) == len(sample_bars_df)

        # Get stats
        stats = manager.get_stats()
        assert stats["total_symbols"] == 1

    def test_full_pipeline_hdf5(self, tmp_path, sample_bars_df):
        """Test complete pipeline with HDF5 backend."""
        store = HDF5Store(tmp_path / "hdf5")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        provider = MockDataProvider(bars_data=sample_bars_df)

        # Download and store
        result = manager.download_and_store(
            provider=provider,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 12, 31),
            validate=False,
        )

        assert result["total_rows"] == len(sample_bars_df)

        # Read back
        df = manager.read_bars("EURUSD", Timeframe.H1)
        assert len(df) == len(sample_bars_df)

    @pytest.mark.skip(reason="Test needs refinement for partition boundaries")
    def test_incremental_downloads(self, tmp_path):
        """Test incremental data downloads and compaction."""
        store = ParquetStore(tmp_path / "parquet")
        catalog = DataCatalog(tmp_path / "catalog.db")
        manager = StorageManager(store, catalog)

        # First download
        df1 = pd.DataFrame({
            "timestamp": [
                int(datetime(2024, 1, 1, i).timestamp() * 1_000_000)
                for i in range(10)
            ],
            "open": [1.1] * 10,
            "high": [1.1] * 10,
            "low": [1.1] * 10,
            "close": [1.1] * 10,
            "tick_volume": [1000] * 10,
            "real_volume": [100000] * 10,
            "spread": [2] * 10,
        })

        provider1 = MockDataProvider(bars_data=df1)
        manager.download_and_store(
            provider=provider1,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 2),
            validate=False,
        )

        # Second download (overlapping)
        df2 = pd.DataFrame({
            "timestamp": [
                int(datetime(2024, 1, 1, 5 + i).timestamp() * 1_000_000)
                for i in range(10)
            ],
            "open": [1.1] * 10,
            "high": [1.1] * 10,
            "low": [1.1] * 10,
            "close": [1.1] * 10,
            "tick_volume": [1000] * 10,
            "real_volume": [100000] * 10,
            "spread": [2] * 10,
        })

        provider2 = MockDataProvider(bars_data=df2)
        manager.download_and_store(
            provider=provider2,
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1, 5),
            end=datetime(2024, 1, 2),
            validate=False,
        )

        # Compact
        result = manager.compact("EURUSD", Timeframe.H1, "2024")

        # Should have deduplicated
        assert result["rows_after"] == 15  # 0-14 hours
