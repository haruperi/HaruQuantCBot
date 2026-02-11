"""
Comprehensive tests for data versioning layer.

Tests the hasher, lineage, and manifest modules that provide data versioning,
reproducibility tracking, and integrity verification.

[REQ: DAT-FR-026] Version identifier (content hash)
[REQ: DAT-FR-027] Backtest records data version hashes
[REQ: DAT-FR-028] Preserve previous versions
[REQ: DAT-FR-029] Data lineage query
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from hqt.data.models.bar import Timeframe
from hqt.data.storage.catalog import DataCatalog
from hqt.data.versioning.hasher import (
    compute_dataframe_hash,
    compute_file_hash,
    compute_hash,
    compute_hash_incremental,
    verify_file_hash,
    verify_hash,
)
from hqt.data.versioning.lineage import DataLineage
from hqt.data.versioning.manifest import DataManifest


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    # On Windows, SQLite keeps database files locked, so ignore cleanup errors
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_data():
    """Create sample test data (bytes)."""
    return b"Hello, HQT Trading System!"


@pytest.fixture
def sample_bars():
    """Create sample bar DataFrame."""
    return pd.DataFrame(
        {
            "timestamp": [1000000, 2000000, 3000000],
            "open": [1.1, 1.2, 1.3],
            "high": [1.15, 1.25, 1.35],
            "low": [1.05, 1.15, 1.25],
            "close": [1.12, 1.22, 1.32],
            "volume": [100, 200, 300],
        }
    )


@pytest.fixture
def sample_ticks():
    """Create sample tick DataFrame."""
    return pd.DataFrame(
        {
            "timestamp": [1000000, 2000000, 3000000],
            "bid": [1.1, 1.2, 1.3],
            "ask": [1.11, 1.21, 1.31],
            "bid_volume": [100, 200, 300],
            "ask_volume": [110, 210, 310],
        }
    )


@pytest.fixture
def lineage_db(temp_dir):
    """Create DataLineage instance with temporary database."""
    import gc
    import sqlite3
    db_path = temp_dir / "lineage.db"
    lineage = DataLineage(db_path)
    yield lineage
    # Force garbage collection to close any lingering connections
    del lineage
    gc.collect()


@pytest.fixture
def catalog_db(temp_dir):
    """Create DataCatalog instance with temporary database."""
    import gc
    import sqlite3
    db_path = temp_dir / "catalog.db"
    catalog = DataCatalog(db_path)
    yield catalog
    # Force garbage collection to close any lingering connections
    del catalog
    gc.collect()


# ============================================================================
# Hasher Tests
# ============================================================================


class TestComputeHash:
    """Tests for compute_hash function."""

    def test_compute_hash_basic(self, sample_data):
        """Test basic hash computation."""
        hash_value = compute_hash(sample_data)

        # SHA-256 produces 64 hex characters
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_compute_hash_consistency(self, sample_data):
        """Test hash consistency - same input produces same hash."""
        hash1 = compute_hash(sample_data)
        hash2 = compute_hash(sample_data)

        assert hash1 == hash2

    def test_compute_hash_different_inputs(self):
        """Test different inputs produce different hashes."""
        data1 = b"Hello"
        data2 = b"World"

        hash1 = compute_hash(data1)
        hash2 = compute_hash(data2)

        assert hash1 != hash2

    def test_compute_hash_empty(self):
        """Test hash of empty bytes."""
        hash_value = compute_hash(b"")

        assert len(hash_value) == 64
        # SHA-256 of empty string
        assert hash_value == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_compute_hash_large_data(self):
        """Test hash of large data."""
        large_data = b"x" * 1_000_000  # 1MB

        hash_value = compute_hash(large_data)

        assert len(hash_value) == 64


class TestComputeFileHash:
    """Tests for compute_file_hash function."""

    def test_compute_file_hash_basic(self, temp_dir, sample_data):
        """Test basic file hash computation."""
        file_path = temp_dir / "test.bin"
        file_path.write_bytes(sample_data)

        hash_value = compute_file_hash(file_path)

        assert len(hash_value) == 64
        # Should match hash of the data
        assert hash_value == compute_hash(sample_data)

    def test_compute_file_hash_consistency(self, temp_dir, sample_data):
        """Test file hash consistency."""
        file_path = temp_dir / "test.bin"
        file_path.write_bytes(sample_data)

        hash1 = compute_file_hash(file_path)
        hash2 = compute_file_hash(file_path)

        assert hash1 == hash2

    def test_compute_file_hash_not_found(self, temp_dir):
        """Test file not found error."""
        file_path = temp_dir / "nonexistent.bin"

        with pytest.raises(FileNotFoundError, match="File not found"):
            compute_file_hash(file_path)

    def test_compute_file_hash_custom_chunk_size(self, temp_dir, sample_data):
        """Test custom chunk size."""
        file_path = temp_dir / "test.bin"
        file_path.write_bytes(sample_data)

        hash1 = compute_file_hash(file_path, chunk_size=1024)
        hash2 = compute_file_hash(file_path, chunk_size=8192)

        # Different chunk sizes should produce same hash
        assert hash1 == hash2

    def test_compute_file_hash_large_file(self, temp_dir):
        """Test hash of large file with chunked reading."""
        file_path = temp_dir / "large.bin"
        large_data = b"x" * 1_000_000  # 1MB
        file_path.write_bytes(large_data)

        hash_value = compute_file_hash(file_path, chunk_size=1024)

        assert len(hash_value) == 64
        # Should match hash of the data
        assert hash_value == compute_hash(large_data)


class TestComputeDataFrameHash:
    """Tests for compute_dataframe_hash function."""

    def test_compute_dataframe_hash_bars(self, sample_bars):
        """Test hash of bar DataFrame."""
        hash_value = compute_dataframe_hash(sample_bars)

        assert len(hash_value) == 64

    def test_compute_dataframe_hash_ticks(self, sample_ticks):
        """Test hash of tick DataFrame."""
        hash_value = compute_dataframe_hash(sample_ticks)

        assert len(hash_value) == 64

    def test_compute_dataframe_hash_consistency_bars(self, sample_bars):
        """Test hash consistency for bars."""
        hash1 = compute_dataframe_hash(sample_bars)
        hash2 = compute_dataframe_hash(sample_bars)

        assert hash1 == hash2

    def test_compute_dataframe_hash_consistency_ticks(self, sample_ticks):
        """Test hash consistency for ticks."""
        hash1 = compute_dataframe_hash(sample_ticks)
        hash2 = compute_dataframe_hash(sample_ticks)

        assert hash1 == hash2

    def test_compute_dataframe_hash_different_data(self):
        """Test different DataFrames produce different hashes."""
        df1 = pd.DataFrame({"timestamp": [1000], "close": [1.1]})
        df2 = pd.DataFrame({"timestamp": [2000], "close": [1.2]})

        hash1 = compute_dataframe_hash(df1)
        hash2 = compute_dataframe_hash(df2)

        assert hash1 != hash2

    def test_compute_dataframe_hash_empty(self):
        """Test hash of empty DataFrame."""
        df = pd.DataFrame({"timestamp": [], "close": []})

        hash_value = compute_dataframe_hash(df)

        # Empty DataFrame should produce hash of empty bytes
        assert hash_value == compute_hash(b"")

    def test_compute_dataframe_hash_timestamp_only(self):
        """Test fallback to timestamp only when no close/ask columns."""
        df = pd.DataFrame({"timestamp": [1000, 2000, 3000], "other": [1, 2, 3]})

        hash_value = compute_dataframe_hash(df)

        assert len(hash_value) == 64

    def test_compute_dataframe_hash_signature_independence(self):
        """Test hash uses signature columns only (not all columns)."""
        df1 = pd.DataFrame(
            {
                "timestamp": [1000, 2000],
                "close": [1.1, 1.2],
                "volume": [100, 200],
            }
        )
        df2 = pd.DataFrame(
            {
                "timestamp": [1000, 2000],
                "close": [1.1, 1.2],
                "volume": [300, 400],  # Different volume
            }
        )

        # Should have same hash as volume is not in signature
        hash1 = compute_dataframe_hash(df1)
        hash2 = compute_dataframe_hash(df2)

        assert hash1 == hash2


class TestComputeHashIncremental:
    """Tests for compute_hash_incremental function."""

    def test_compute_hash_incremental_basic(self, temp_dir):
        """Test basic incremental hash computation."""
        file1 = temp_dir / "file1.bin"
        file2 = temp_dir / "file2.bin"
        file1.write_bytes(b"Hello")
        file2.write_bytes(b"World")

        hash_value = compute_hash_incremental([file1, file2])

        assert len(hash_value) == 64

    def test_compute_hash_incremental_consistency(self, temp_dir):
        """Test incremental hash consistency."""
        file1 = temp_dir / "file1.bin"
        file2 = temp_dir / "file2.bin"
        file1.write_bytes(b"Hello")
        file2.write_bytes(b"World")

        hash1 = compute_hash_incremental([file1, file2])
        hash2 = compute_hash_incremental([file1, file2])

        assert hash1 == hash2

    def test_compute_hash_incremental_order_matters(self, temp_dir):
        """Test that file order matters."""
        file1 = temp_dir / "file1.bin"
        file2 = temp_dir / "file2.bin"
        file1.write_bytes(b"Hello")
        file2.write_bytes(b"World")

        hash1 = compute_hash_incremental([file1, file2])
        hash2 = compute_hash_incremental([file2, file1])

        # Different order should produce different hash
        assert hash1 != hash2

    def test_compute_hash_incremental_file_not_found(self, temp_dir):
        """Test error when file not found."""
        file1 = temp_dir / "file1.bin"
        file2 = temp_dir / "nonexistent.bin"
        file1.write_bytes(b"Hello")

        with pytest.raises(FileNotFoundError, match="File not found"):
            compute_hash_incremental([file1, file2])

    def test_compute_hash_incremental_single_file(self, temp_dir):
        """Test with single file."""
        file1 = temp_dir / "file1.bin"
        file1.write_bytes(b"Hello")

        hash_incremental = compute_hash_incremental([file1])
        hash_file = compute_file_hash(file1)

        # Should match single file hash
        assert hash_incremental == hash_file

    def test_compute_hash_incremental_empty_list(self):
        """Test with empty file list."""
        hash_value = compute_hash_incremental([])

        # Should produce hash of empty data
        assert hash_value == compute_hash(b"")


class TestVerifyHash:
    """Tests for verify_hash function."""

    def test_verify_hash_valid(self, sample_data):
        """Test verify with matching hash."""
        expected_hash = compute_hash(sample_data)

        assert verify_hash(sample_data, expected_hash) is True

    def test_verify_hash_invalid(self, sample_data):
        """Test verify with non-matching hash."""
        wrong_hash = compute_hash(b"Different data")

        assert verify_hash(sample_data, wrong_hash) is False

    def test_verify_hash_empty(self):
        """Test verify with empty data."""
        empty_hash = compute_hash(b"")

        assert verify_hash(b"", empty_hash) is True


class TestVerifyFileHash:
    """Tests for verify_file_hash function."""

    def test_verify_file_hash_valid(self, temp_dir, sample_data):
        """Test verify with matching file hash."""
        file_path = temp_dir / "test.bin"
        file_path.write_bytes(sample_data)
        expected_hash = compute_file_hash(file_path)

        assert verify_file_hash(file_path, expected_hash) is True

    def test_verify_file_hash_invalid(self, temp_dir, sample_data):
        """Test verify with non-matching file hash."""
        file_path = temp_dir / "test.bin"
        file_path.write_bytes(sample_data)
        wrong_hash = compute_hash(b"Different data")

        assert verify_file_hash(file_path, wrong_hash) is False

    def test_verify_file_hash_file_modified(self, temp_dir):
        """Test verify detects file modification."""
        file_path = temp_dir / "test.bin"
        file_path.write_bytes(b"Original")
        original_hash = compute_file_hash(file_path)

        # Modify file
        file_path.write_bytes(b"Modified")

        assert verify_file_hash(file_path, original_hash) is False

    def test_verify_file_hash_file_not_found(self, temp_dir):
        """Test verify raises error when file not found."""
        file_path = temp_dir / "nonexistent.bin"
        fake_hash = "a" * 64

        with pytest.raises(FileNotFoundError):
            verify_file_hash(file_path, fake_hash)


# ============================================================================
# DataLineage Tests
# ============================================================================


class TestDataLineageInit:
    """Tests for DataLineage initialization."""

    def test_init_creates_database(self, temp_dir):
        """Test initialization creates database file."""
        db_path = temp_dir / "lineage.db"
        lineage = DataLineage(db_path)

        assert db_path.exists()

    def test_init_creates_parent_directory(self, temp_dir):
        """Test initialization creates parent directories."""
        db_path = temp_dir / "subdir" / "lineage.db"
        lineage = DataLineage(db_path)

        assert db_path.exists()
        assert db_path.parent.exists()

    def test_init_creates_schema(self, temp_dir):
        """Test initialization creates correct schema."""
        import sqlite3

        db_path = temp_dir / "lineage.db"
        lineage = DataLineage(db_path)

        with sqlite3.connect(db_path) as conn:
            # Check table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='lineage'"
            )
            assert cursor.fetchone() is not None

            # Check indexes exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_backtest'"
            )
            assert cursor.fetchone() is not None


class TestDataLineageRecordBacktest:
    """Tests for record_backtest_lineage method."""

    def test_record_backtest_lineage_basic(self, lineage_db):
        """Test recording basic backtest lineage."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]

        count = lineage_db.record_backtest_lineage(
            backtest_id=1, data_files=data_files
        )

        assert count == 1

    def test_record_backtest_lineage_multiple_files(self, lineage_db):
        """Test recording multiple files."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
            {
                "file_path": "data/GBPUSD_H1_2024.parquet",
                "version_hash": "def456",
                "symbol": "GBPUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
        ]

        count = lineage_db.record_backtest_lineage(
            backtest_id=1, data_files=data_files
        )

        assert count == 2

    def test_record_backtest_lineage_optional_fields(self, lineage_db):
        """Test recording with optional fields."""
        data_files = [
            {
                "file_path": "data/EURUSD_ticks_2024.parquet",
                "version_hash": "xyz789",
                "symbol": "EURUSD",
                # No timeframe (ticks)
                "partition": "2024",
            }
        ]

        count = lineage_db.record_backtest_lineage(
            backtest_id=1, data_files=data_files
        )

        assert count == 1


class TestDataLineageGetLineage:
    """Tests for get_lineage method."""

    def test_get_lineage_basic(self, lineage_db):
        """Test getting lineage information."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        lineage_info = lineage_db.get_lineage(backtest_id=1)

        assert lineage_info["backtest_id"] == 1
        assert lineage_info["total_files"] == 1
        assert len(lineage_info["data_files"]) == 1
        assert lineage_info["data_files"][0]["symbol"] == "EURUSD"
        assert lineage_info["data_files"][0]["data_version_hash"] == "abc123"
        assert lineage_info["recorded_at"] > 0

    def test_get_lineage_multiple_files(self, lineage_db):
        """Test getting lineage with multiple files."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
            {
                "file_path": "data/GBPUSD_H1_2024.parquet",
                "version_hash": "def456",
                "symbol": "GBPUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        lineage_info = lineage_db.get_lineage(backtest_id=1)

        assert lineage_info["total_files"] == 2
        assert len(lineage_info["data_files"]) == 2

    def test_get_lineage_not_found(self, lineage_db):
        """Test error when backtest not found."""
        with pytest.raises(KeyError, match="No lineage found for backtest 999"):
            lineage_db.get_lineage(backtest_id=999)

    def test_get_lineage_sorted_order(self, lineage_db):
        """Test lineage files are returned in sorted order."""
        data_files = [
            {
                "file_path": "data/GBPUSD_H1_2024.parquet",
                "version_hash": "def456",
                "symbol": "GBPUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        lineage_info = lineage_db.get_lineage(backtest_id=1)

        # Should be sorted by symbol
        assert lineage_info["data_files"][0]["symbol"] == "EURUSD"
        assert lineage_info["data_files"][1]["symbol"] == "GBPUSD"


class TestDataLineageCanReproduce:
    """Tests for can_reproduce method."""

    def test_can_reproduce_success(self, lineage_db, temp_dir):
        """Test can_reproduce when all files exist with correct hashes."""
        # Create test file
        file_path = temp_dir / "EURUSD_H1_2024.parquet"
        file_path.write_bytes(b"test data")
        file_hash = compute_file_hash(file_path)

        # Record lineage
        data_files = [
            {
                "file_path": str(file_path),
                "version_hash": file_hash,
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        # Check reproducibility
        result = lineage_db.can_reproduce(backtest_id=1)

        assert result["reproducible"] is True
        assert len(result["issues"]) == 0
        assert result["verified_files"] == 1
        assert result["total_files"] == 1

    def test_can_reproduce_missing_file(self, lineage_db, temp_dir):
        """Test can_reproduce when file is missing."""
        # Record lineage for non-existent file
        data_files = [
            {
                "file_path": str(temp_dir / "nonexistent.parquet"),
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        # Check reproducibility
        result = lineage_db.can_reproduce(backtest_id=1)

        assert result["reproducible"] is False
        assert len(result["issues"]) == 1
        assert "Missing file" in result["issues"][0]
        assert result["verified_files"] == 0
        assert result["total_files"] == 1

    def test_can_reproduce_hash_mismatch(self, lineage_db, temp_dir):
        """Test can_reproduce when file hash doesn't match."""
        # Create test file
        file_path = temp_dir / "EURUSD_H1_2024.parquet"
        file_path.write_bytes(b"original data")
        original_hash = compute_file_hash(file_path)

        # Record lineage
        data_files = [
            {
                "file_path": str(file_path),
                "version_hash": original_hash,
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        # Modify file
        file_path.write_bytes(b"modified data")

        # Check reproducibility
        result = lineage_db.can_reproduce(backtest_id=1)

        assert result["reproducible"] is False
        assert len(result["issues"]) == 1
        assert "Hash mismatch" in result["issues"][0]
        assert result["verified_files"] == 0
        assert result["total_files"] == 1

    def test_can_reproduce_backtest_not_found(self, lineage_db):
        """Test can_reproduce when backtest not found."""
        result = lineage_db.can_reproduce(backtest_id=999)

        assert result["reproducible"] is False
        assert len(result["issues"]) == 1
        assert "No lineage found" in result["issues"][0]
        assert result["verified_files"] == 0
        assert result["total_files"] == 0

    def test_can_reproduce_multiple_files_partial_failure(self, lineage_db, temp_dir):
        """Test can_reproduce with multiple files, some failing."""
        # Create first file
        file1 = temp_dir / "EURUSD_H1_2024.parquet"
        file1.write_bytes(b"data 1")
        hash1 = compute_file_hash(file1)

        # Second file doesn't exist
        file2 = temp_dir / "GBPUSD_H1_2024.parquet"

        # Record lineage
        data_files = [
            {
                "file_path": str(file1),
                "version_hash": hash1,
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
            {
                "file_path": str(file2),
                "version_hash": "abc123",
                "symbol": "GBPUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        # Check reproducibility
        result = lineage_db.can_reproduce(backtest_id=1)

        assert result["reproducible"] is False
        assert len(result["issues"]) == 1
        assert result["verified_files"] == 1
        assert result["total_files"] == 2


class TestDataLineageGetDataVersions:
    """Tests for get_data_versions method."""

    def test_get_data_versions_basic(self, lineage_db):
        """Test getting data version hashes."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        versions = lineage_db.get_data_versions(backtest_id=1)

        assert len(versions) == 1
        assert "abc123" in versions

    def test_get_data_versions_multiple_unique(self, lineage_db):
        """Test getting multiple unique versions."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
            {
                "file_path": "data/GBPUSD_H1_2024.parquet",
                "version_hash": "def456",
                "symbol": "GBPUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        versions = lineage_db.get_data_versions(backtest_id=1)

        assert len(versions) == 2
        assert "abc123" in versions
        assert "def456" in versions

    def test_get_data_versions_duplicates(self, lineage_db):
        """Test that duplicate hashes are deduplicated."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
            {
                "file_path": "data/EURUSD_H1_2025.parquet",
                "version_hash": "abc123",  # Same hash
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2025",
            },
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        versions = lineage_db.get_data_versions(backtest_id=1)

        assert len(versions) == 1
        assert "abc123" in versions


class TestDataLineageFindBacktests:
    """Tests for find_backtests_using_data method."""

    def test_find_backtests_using_data_basic(self, lineage_db):
        """Test finding backtests using specific data version."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        backtests = lineage_db.find_backtests_using_data(version_hash="abc123")

        assert len(backtests) == 1
        assert 1 in backtests

    def test_find_backtests_using_data_multiple_backtests(self, lineage_db):
        """Test finding multiple backtests using same data."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]

        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)
        lineage_db.record_backtest_lineage(backtest_id=2, data_files=data_files)

        backtests = lineage_db.find_backtests_using_data(version_hash="abc123")

        assert len(backtests) == 2
        assert 1 in backtests
        assert 2 in backtests

    def test_find_backtests_using_data_not_found(self, lineage_db):
        """Test finding backtests with non-existent hash."""
        backtests = lineage_db.find_backtests_using_data(version_hash="nonexistent")

        assert len(backtests) == 0


class TestDataLineageDeleteLineage:
    """Tests for delete_lineage method."""

    def test_delete_lineage_basic(self, lineage_db):
        """Test deleting lineage."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        count = lineage_db.delete_lineage(backtest_id=1)

        assert count == 1

        # Verify deleted
        with pytest.raises(KeyError):
            lineage_db.get_lineage(backtest_id=1)

    def test_delete_lineage_not_found(self, lineage_db):
        """Test deleting non-existent lineage."""
        count = lineage_db.delete_lineage(backtest_id=999)

        assert count == 0

    def test_delete_lineage_multiple_records(self, lineage_db):
        """Test deleting lineage with multiple records."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
            {
                "file_path": "data/GBPUSD_H1_2024.parquet",
                "version_hash": "def456",
                "symbol": "GBPUSD",
                "timeframe": "H1",
                "partition": "2024",
            },
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        count = lineage_db.delete_lineage(backtest_id=1)

        assert count == 2


class TestDataLineageGetStats:
    """Tests for get_stats method."""

    def test_get_stats_empty(self, lineage_db):
        """Test stats on empty database."""
        stats = lineage_db.get_stats()

        assert stats["total_backtests"] == 0
        assert stats["total_records"] == 0
        assert stats["total_data_versions"] == 0

    def test_get_stats_basic(self, lineage_db):
        """Test stats with data."""
        data_files = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]
        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files)

        stats = lineage_db.get_stats()

        assert stats["total_backtests"] == 1
        assert stats["total_records"] == 1
        assert stats["total_data_versions"] == 1

    def test_get_stats_multiple_backtests(self, lineage_db):
        """Test stats with multiple backtests."""
        data_files1 = [
            {
                "file_path": "data/EURUSD_H1_2024.parquet",
                "version_hash": "abc123",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]
        data_files2 = [
            {
                "file_path": "data/GBPUSD_H1_2024.parquet",
                "version_hash": "def456",
                "symbol": "GBPUSD",
                "timeframe": "H1",
                "partition": "2024",
            }
        ]

        lineage_db.record_backtest_lineage(backtest_id=1, data_files=data_files1)
        lineage_db.record_backtest_lineage(backtest_id=2, data_files=data_files2)

        stats = lineage_db.get_stats()

        assert stats["total_backtests"] == 2
        assert stats["total_records"] == 2
        assert stats["total_data_versions"] == 2


class TestDataLineageContextManager:
    """Tests for DataLineage context manager."""

    def test_context_manager(self, temp_dir):
        """Test using DataLineage as context manager."""
        db_path = temp_dir / "lineage.db"

        with DataLineage(db_path) as lineage:
            data_files = [
                {
                    "file_path": "data/EURUSD_H1_2024.parquet",
                    "version_hash": "abc123",
                    "symbol": "EURUSD",
                    "timeframe": "H1",
                    "partition": "2024",
                }
            ]
            lineage.record_backtest_lineage(backtest_id=1, data_files=data_files)

        # Verify data persisted
        lineage2 = DataLineage(db_path)
        lineage_info = lineage2.get_lineage(backtest_id=1)
        assert lineage_info["total_files"] == 1


# ============================================================================
# DataManifest Tests
# ============================================================================


class TestDataManifestGenerate:
    """Tests for DataManifest.generate method."""

    def test_generate_basic(self, catalog_db, temp_dir):
        """Test basic manifest generation."""
        # Create test file
        file_path = temp_dir / "EURUSD_H1_2024.parquet"
        file_path.write_bytes(b"test data")
        file_hash = compute_file_hash(file_path)

        # Register in catalog
        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file_path),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            data_source="mt5",
            version_hash=file_hash,
        )

        # Generate manifest
        manifest = DataManifest(catalog_db)
        manifest_path = temp_dir / "manifest.json"
        result = manifest.generate(manifest_path)

        assert result["total_files"] == 1
        assert result["total_size_bytes"] > 0
        assert manifest_path.exists()

        # Verify manifest content
        with open(manifest_path) as f:
            manifest_data = json.load(f)

        assert manifest_data["total_files"] == 1
        assert len(manifest_data["files"]) == 1
        assert manifest_data["files"][0]["symbol"] == "EURUSD"
        assert manifest_data["files"][0]["version_hash"] == file_hash

    def test_generate_multiple_files(self, catalog_db, temp_dir):
        """Test manifest generation with multiple files."""
        # Create test files
        file1 = temp_dir / "EURUSD_H1_2024.parquet"
        file2 = temp_dir / "GBPUSD_H1_2024.parquet"
        file1.write_bytes(b"data 1")
        file2.write_bytes(b"data 2")

        # Register in catalog
        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file1),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file1),
        )
        catalog_db.register_file(
            symbol="GBPUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file2),
            storage_format="parquet",
            row_count=200,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file2),
        )

        # Generate manifest
        manifest = DataManifest(catalog_db)
        manifest_path = temp_dir / "manifest.json"
        result = manifest.generate(manifest_path)

        assert result["total_files"] == 2

    def test_generate_creates_parent_directory(self, catalog_db, temp_dir):
        """Test manifest generation creates parent directory."""
        manifest_path = temp_dir / "subdir" / "manifest.json"
        manifest = DataManifest(catalog_db)

        manifest.generate(manifest_path)

        assert manifest_path.parent.exists()


class TestDataManifestVerify:
    """Tests for DataManifest.verify method."""

    def test_verify_valid_manifest(self, catalog_db, temp_dir):
        """Test verifying valid manifest."""
        # Create test file
        file_path = temp_dir / "EURUSD_H1_2024.parquet"
        file_path.write_bytes(b"test data")
        file_hash = compute_file_hash(file_path)

        # Register and generate manifest
        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file_path),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=file_hash,
        )

        manifest = DataManifest(catalog_db)
        manifest_path = temp_dir / "manifest.json"
        manifest.generate(manifest_path)

        # Verify manifest
        result = manifest.verify(manifest_path)

        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert result["verified_files"] == 1
        assert result["total_files"] == 1

    def test_verify_missing_file(self, catalog_db, temp_dir):
        """Test verifying manifest with missing file."""
        # Create file, generate manifest, then delete file
        file_path = temp_dir / "EURUSD_H1_2024.parquet"
        file_path.write_bytes(b"test data")
        file_hash = compute_file_hash(file_path)

        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file_path),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=file_hash,
        )

        manifest = DataManifest(catalog_db)
        manifest_path = temp_dir / "manifest.json"
        manifest.generate(manifest_path)

        # Delete file
        file_path.unlink()

        # Verify manifest
        result = manifest.verify(manifest_path)

        assert result["valid"] is False
        assert len(result["issues"]) == 1
        assert "Missing file" in result["issues"][0]
        assert result["verified_files"] == 0
        assert result["total_files"] == 1

    def test_verify_hash_mismatch(self, catalog_db, temp_dir):
        """Test verifying manifest with hash mismatch."""
        # Create file and generate manifest
        file_path = temp_dir / "EURUSD_H1_2024.parquet"
        file_path.write_bytes(b"original data")
        file_hash = compute_file_hash(file_path)

        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file_path),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=file_hash,
        )

        manifest = DataManifest(catalog_db)
        manifest_path = temp_dir / "manifest.json"
        manifest.generate(manifest_path)

        # Modify file
        file_path.write_bytes(b"modified data")

        # Verify manifest
        result = manifest.verify(manifest_path)

        assert result["valid"] is False
        assert len(result["issues"]) == 1
        assert "Hash mismatch" in result["issues"][0]
        assert result["verified_files"] == 0
        assert result["total_files"] == 1

    def test_verify_manifest_not_found(self, catalog_db, temp_dir):
        """Test verifying non-existent manifest."""
        manifest = DataManifest(catalog_db)
        manifest_path = temp_dir / "nonexistent.json"

        result = manifest.verify(manifest_path)

        assert result["valid"] is False
        assert len(result["issues"]) == 1
        assert "Manifest not found" in result["issues"][0]

    def test_verify_skip_hashes(self, catalog_db, temp_dir):
        """Test verifying without hash checking."""
        # Create file and generate manifest
        file_path = temp_dir / "EURUSD_H1_2024.parquet"
        file_path.write_bytes(b"original data")
        file_hash = compute_file_hash(file_path)

        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file_path),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=file_hash,
        )

        manifest = DataManifest(catalog_db)
        manifest_path = temp_dir / "manifest.json"
        manifest.generate(manifest_path)

        # Modify file
        file_path.write_bytes(b"modified data")

        # Verify without hash checking
        result = manifest.verify(manifest_path, check_hashes=False)

        # Should pass since we're only checking file existence
        assert result["valid"] is True
        assert result["verified_files"] == 1


class TestDataManifestUpdate:
    """Tests for DataManifest.update method."""

    def test_update_add_new_files(self, catalog_db, temp_dir):
        """Test updating manifest with new files."""
        # Create first file and generate manifest
        file1 = temp_dir / "EURUSD_H1_2024.parquet"
        file1.write_bytes(b"data 1")

        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file1),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file1),
        )

        manifest = DataManifest(catalog_db)
        manifest_path = temp_dir / "manifest.json"
        manifest.generate(manifest_path)

        # Add second file
        file2 = temp_dir / "GBPUSD_H1_2024.parquet"
        file2.write_bytes(b"data 2")

        catalog_db.register_file(
            symbol="GBPUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file2),
            storage_format="parquet",
            row_count=200,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file2),
        )

        # Update manifest
        result = manifest.update(manifest_path)

        assert result["added"] == 1
        assert result["updated"] == 0
        assert result["total_files"] == 2

    def test_update_existing_file(self, catalog_db, temp_dir):
        """Test updating manifest with modified file."""
        # Create file and generate manifest
        file_path = temp_dir / "EURUSD_H1_2024.parquet"
        file_path.write_bytes(b"original data")

        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file_path),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file_path),
        )

        manifest = DataManifest(catalog_db)
        manifest_path = temp_dir / "manifest.json"
        manifest.generate(manifest_path)

        # Modify file and update catalog
        file_path.write_bytes(b"modified data")
        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file_path),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file_path),
        )

        # Update manifest
        result = manifest.update(manifest_path)

        assert result["added"] == 0
        assert result["updated"] == 1
        assert result["total_files"] == 1

    def test_update_creates_manifest_if_not_exists(self, catalog_db, temp_dir):
        """Test update creates manifest if it doesn't exist."""
        file_path = temp_dir / "EURUSD_H1_2024.parquet"
        file_path.write_bytes(b"test data")

        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file_path),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file_path),
        )

        manifest = DataManifest(catalog_db)
        manifest_path = temp_dir / "manifest.json"

        # Update (should create)
        result = manifest.update(manifest_path)

        assert result["added"] == 1
        assert manifest_path.exists()


class TestDataManifestDiff:
    """Tests for DataManifest.diff method."""

    def test_diff_added_files(self, catalog_db, temp_dir):
        """Test diff shows added files."""
        # Create manifest 1
        file1 = temp_dir / "EURUSD_H1_2024.parquet"
        file1.write_bytes(b"data 1")
        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file1),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file1),
        )

        manifest = DataManifest(catalog_db)
        manifest1_path = temp_dir / "manifest1.json"
        manifest.generate(manifest1_path)

        # Add file to catalog
        file2 = temp_dir / "GBPUSD_H1_2024.parquet"
        file2.write_bytes(b"data 2")
        catalog_db.register_file(
            symbol="GBPUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file2),
            storage_format="parquet",
            row_count=200,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file2),
        )

        # Create manifest 2
        manifest2_path = temp_dir / "manifest2.json"
        manifest.generate(manifest2_path)

        # Diff
        diff = manifest.diff(manifest1_path, manifest2_path)

        assert len(diff["added"]) == 1
        assert len(diff["removed"]) == 0
        assert len(diff["modified"]) == 0
        assert diff["unchanged"] == 1
        assert diff["added"][0]["symbol"] == "GBPUSD"

    def test_diff_removed_files(self, catalog_db, temp_dir):
        """Test diff shows removed files."""
        # Create two files
        file1 = temp_dir / "EURUSD_H1_2024.parquet"
        file2 = temp_dir / "GBPUSD_H1_2024.parquet"
        file1.write_bytes(b"data 1")
        file2.write_bytes(b"data 2")

        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file1),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file1),
        )
        catalog_db.register_file(
            symbol="GBPUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file2),
            storage_format="parquet",
            row_count=200,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file2),
        )

        manifest = DataManifest(catalog_db)
        manifest1_path = temp_dir / "manifest1.json"
        manifest.generate(manifest1_path)

        # Delete one from catalog
        catalog_db.delete_entry(symbol="GBPUSD", timeframe=Timeframe.H1, partition="2024")

        # Create manifest 2
        manifest2_path = temp_dir / "manifest2.json"
        manifest.generate(manifest2_path)

        # Diff
        diff = manifest.diff(manifest1_path, manifest2_path)

        assert len(diff["added"]) == 0
        assert len(diff["removed"]) == 1
        assert len(diff["modified"]) == 0
        assert diff["unchanged"] == 1
        assert diff["removed"][0]["symbol"] == "GBPUSD"

    def test_diff_modified_files(self, catalog_db, temp_dir):
        """Test diff shows modified files."""
        # Create file and manifest
        file_path = temp_dir / "EURUSD_H1_2024.parquet"
        file_path.write_bytes(b"original data")
        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file_path),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file_path),
        )

        manifest = DataManifest(catalog_db)
        manifest1_path = temp_dir / "manifest1.json"
        manifest.generate(manifest1_path)

        # Modify file and update catalog
        file_path.write_bytes(b"modified data")
        catalog_db.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file_path),
            storage_format="parquet",
            row_count=100,
            min_timestamp=1000000,
            max_timestamp=2000000,
            version_hash=compute_file_hash(file_path),
        )

        # Create manifest 2
        manifest2_path = temp_dir / "manifest2.json"
        manifest.generate(manifest2_path)

        # Diff
        diff = manifest.diff(manifest1_path, manifest2_path)

        assert len(diff["added"]) == 0
        assert len(diff["removed"]) == 0
        assert len(diff["modified"]) == 1
        assert diff["unchanged"] == 0
        assert diff["modified"][0]["file"]["symbol"] == "EURUSD"
        assert diff["modified"][0]["old_hash"] != diff["modified"][0]["new_hash"]


# ============================================================================
# Integration Tests
# ============================================================================


class TestVersioningIntegration:
    """End-to-end integration tests."""

    def test_complete_workflow(self, temp_dir, sample_bars):
        """Test complete versioning workflow."""
        # 1. Create and save data file
        data_file = temp_dir / "EURUSD_H1_2024.parquet"
        sample_bars.to_parquet(data_file)

        # 2. Compute hash
        file_hash = compute_file_hash(data_file)

        # 3. Register in catalog
        catalog = DataCatalog(temp_dir / "catalog.db")
        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(data_file),
            storage_format="parquet",
            row_count=len(sample_bars),
            min_timestamp=int(sample_bars["timestamp"].min()),
            max_timestamp=int(sample_bars["timestamp"].max()),
            data_source="mt5",
            version_hash=file_hash,
        )

        # 4. Record lineage
        lineage = DataLineage(temp_dir / "lineage.db")
        lineage.record_backtest_lineage(
            backtest_id=1,
            data_files=[
                {
                    "file_path": str(data_file),
                    "version_hash": file_hash,
                    "symbol": "EURUSD",
                    "timeframe": "H1",
                    "partition": "2024",
                }
            ],
        )

        # 5. Generate manifest
        manifest_tool = DataManifest(catalog)
        manifest_path = temp_dir / "manifest.json"
        manifest_tool.generate(manifest_path)

        # 6. Verify everything
        # - Lineage can reproduce
        result = lineage.can_reproduce(backtest_id=1)
        assert result["reproducible"] is True

        # - Manifest is valid
        verify_result = manifest_tool.verify(manifest_path)
        assert verify_result["valid"] is True

        # - File hash still matches
        assert verify_file_hash(data_file, file_hash) is True

    def test_reproducibility_workflow(self, temp_dir, sample_bars):
        """Test reproducibility verification workflow."""
        # Setup
        data_file = temp_dir / "EURUSD_H1_2024.parquet"
        sample_bars.to_parquet(data_file)
        file_hash = compute_file_hash(data_file)

        lineage = DataLineage(temp_dir / "lineage.db")
        lineage.record_backtest_lineage(
            backtest_id=1,
            data_files=[
                {
                    "file_path": str(data_file),
                    "version_hash": file_hash,
                    "symbol": "EURUSD",
                    "timeframe": "H1",
                    "partition": "2024",
                }
            ],
        )

        # Verify reproducible
        result = lineage.can_reproduce(backtest_id=1)
        assert result["reproducible"] is True

        # Modify data file
        modified_bars = sample_bars.copy()
        modified_bars.loc[0, "close"] = 999.99
        modified_bars.to_parquet(data_file)

        # Verify no longer reproducible
        result = lineage.can_reproduce(backtest_id=1)
        assert result["reproducible"] is False
        assert "Hash mismatch" in result["issues"][0]

    def test_manifest_integrity_workflow(self, temp_dir, sample_bars):
        """Test manifest integrity verification workflow."""
        # Create multiple data files
        file1 = temp_dir / "EURUSD_H1_2024.parquet"
        file2 = temp_dir / "GBPUSD_H1_2024.parquet"
        sample_bars.to_parquet(file1)
        sample_bars.to_parquet(file2)

        # Register in catalog
        catalog = DataCatalog(temp_dir / "catalog.db")
        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file1),
            storage_format="parquet",
            row_count=len(sample_bars),
            min_timestamp=int(sample_bars["timestamp"].min()),
            max_timestamp=int(sample_bars["timestamp"].max()),
            version_hash=compute_file_hash(file1),
        )
        catalog.register_file(
            symbol="GBPUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path=str(file2),
            storage_format="parquet",
            row_count=len(sample_bars),
            min_timestamp=int(sample_bars["timestamp"].min()),
            max_timestamp=int(sample_bars["timestamp"].max()),
            version_hash=compute_file_hash(file2),
        )

        # Generate manifest
        manifest_tool = DataManifest(catalog)
        manifest_path = temp_dir / "manifest.json"
        manifest_tool.generate(manifest_path)

        # Verify all valid
        result = manifest_tool.verify(manifest_path)
        assert result["valid"] is True
        assert result["verified_files"] == 2

        # Corrupt one file
        file2.write_bytes(b"corrupted")

        # Verify detects corruption
        result = manifest_tool.verify(manifest_path)
        assert result["valid"] is False
        assert result["verified_files"] == 1
        assert "Hash mismatch" in result["issues"][0]
