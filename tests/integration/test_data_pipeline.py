"""
End-to-end integration tests for the complete data pipeline.

Tests the full workflow using storage components:
- Data storage (Parquet)
- Catalog registration
- Versioning (hashing)
- Lineage tracking
- Manifest generation

[REQ: DAT-FR-001 through DAT-FR-029]
[SDD: §5] Data Layer
"""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from hqt.data.models.bar import Timeframe
from hqt.data.storage.catalog import DataCatalog
from hqt.data.storage.parquet_store import ParquetStore
from hqt.data.versioning.hasher import compute_file_hash
from hqt.data.versioning.lineage import DataLineage
from hqt.data.versioning.manifest import DataManifest


class TestDataPipelineE2E:
    """End-to-end tests for the complete data pipeline."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def sample_bars(self):
        """Generate sample bar data for testing."""
        start = datetime(2024, 1, 1, 0, 0, 0)
        timestamps = [start + timedelta(hours=i) for i in range(100)]

        data = {
            "timestamp": [int(ts.timestamp() * 1_000_000) for ts in timestamps],
            "open": [1.09000 + (i % 10) * 0.00001 for i in range(100)],
            "high": [1.09050 + (i % 10) * 0.00001 for i in range(100)],
            "low": [1.08950 + (i % 10) * 0.00001 for i in range(100)],
            "close": [1.09025 + (i % 10) * 0.00001 for i in range(100)],
            "tick_volume": [1000 + (i % 10) * 100 for i in range(100)],
            "real_volume": [100000 + (i % 10) * 10000 for i in range(100)],
            "spread": [10 + (i % 5) for i in range(100)],
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def sample_ticks(self):
        """Generate sample tick data for testing."""
        start = datetime(2024, 1, 1, 0, 0, 0)
        timestamps = [start + timedelta(milliseconds=i * 100) for i in range(1000)]

        data = {
            "timestamp": [int(ts.timestamp() * 1_000_000) for ts in timestamps],
            "bid": [1.09000 + (i % 50) * 0.00001 for i in range(1000)],
            "ask": [1.09020 + (i % 50) * 0.00001 for i in range(1000)],
            "bid_volume": [100 + (i % 20) * 10 for i in range(1000)],
            "ask_volume": [100 + (i % 20) * 10 for i in range(1000)],
        }
        return pd.DataFrame(data)

    def test_complete_bars_pipeline(self, temp_dir, sample_bars):
        """
        Test complete bar data pipeline: store → catalog → hash → read.
        """
        data_dir = temp_dir / "data"
        catalog_db = temp_dir / "catalog.db"

        store = ParquetStore(str(data_dir))
        symbol = "EURUSD"
        timeframe = Timeframe.H1
        partition = "2024"

        # Store to Parquet
        file_path = store.write_bars(symbol, timeframe, sample_bars, partition)
        assert file_path.exists()

        # Compute hash
        version_hash = compute_file_hash(file_path)
        assert len(version_hash) == 64

        # Register in catalog
        with DataCatalog(str(catalog_db)) as catalog:
            catalog.register_file(
                symbol=symbol,
                timeframe=timeframe,
                partition=partition,
                file_path=str(file_path),
                storage_format="parquet",
                row_count=len(sample_bars),
                min_timestamp=int(sample_bars["timestamp"].min()),
                max_timestamp=int(sample_bars["timestamp"].max()),
                data_source="test",
                version_hash=version_hash,
                file_size_bytes=file_path.stat().st_size,
            )

        # Read back
        df = store.read_bars(symbol, timeframe, partition=partition)
        assert len(df) == len(sample_bars)

        # Verify price integrity
        max_diff = abs(df["close"] - sample_bars["close"]).max()
        assert max_diff < 0.00001

    def test_complete_ticks_pipeline(self, temp_dir, sample_ticks):
        """
        Test complete tick data pipeline: store → catalog → read.
        """
        data_dir = temp_dir / "data"
        catalog_db = temp_dir / "catalog.db"

        store = ParquetStore(str(data_dir))
        symbol = "EURUSD"
        partition = "2024-01"

        # Store ticks
        file_path = store.write_ticks(symbol, sample_ticks, partition)
        assert file_path.exists()

        # Compute hash
        version_hash = compute_file_hash(file_path)

        # Register in catalog
        with DataCatalog(str(catalog_db)) as catalog:
            catalog.register_file(
                symbol=symbol,
                timeframe=None,
                partition=partition,
                file_path=str(file_path),
                storage_format="parquet",
                row_count=len(sample_ticks),
                min_timestamp=int(sample_ticks["timestamp"].min()),
                max_timestamp=int(sample_ticks["timestamp"].max()),
                data_source="test",
                version_hash=version_hash,
                file_size_bytes=file_path.stat().st_size,
            )

        # Read back
        df = store.read_ticks(symbol, partition=partition)
        assert len(df) == len(sample_ticks)

    def test_versioning_and_lineage_integration(self, temp_dir, sample_bars):
        """
        Test versioning and lineage tracking integration.
        """
        data_dir = temp_dir / "data"
        catalog_db = temp_dir / "catalog.db"
        lineage_db = temp_dir / "lineage.db"

        store = ParquetStore(str(data_dir))
        symbol = "EURUSD"
        timeframe = Timeframe.H1
        partition = "2024"

        # Store data
        file_path = store.write_bars(symbol, timeframe, sample_bars, partition)
        version_hash = compute_file_hash(file_path)

        # Register in catalog
        with DataCatalog(str(catalog_db)) as catalog:
            catalog.register_file(
                symbol=symbol,
                timeframe=timeframe,
                partition=partition,
                file_path=str(file_path),
                storage_format="parquet",
                row_count=len(sample_bars),
                min_timestamp=int(sample_bars["timestamp"].min()),
                max_timestamp=int(sample_bars["timestamp"].max()),
                data_source="test",
                version_hash=version_hash,
                file_size_bytes=file_path.stat().st_size,
            )

        # Record lineage
        with DataLineage(str(lineage_db)) as lineage:
            backtest_id = 12345
            lineage.record_backtest_lineage(
                backtest_id=backtest_id,
                data_files=[
                    {
                        "file_path": str(file_path),
                        "version_hash": version_hash,
                        "symbol": symbol,
                        "timeframe": timeframe.value,
                        "partition": partition,
                    }
                ],
            )

            # Verify reproducibility
            reproducibility = lineage.can_reproduce(backtest_id)
            assert reproducibility["reproducible"]
            assert reproducibility["verified_files"] == 1

    def test_manifest_generation_and_verification(self, temp_dir, sample_bars):
        """
        Test manifest generation and verification.
        """
        data_dir = temp_dir / "data"
        catalog_db = temp_dir / "catalog.db"
        manifest_path = temp_dir / "manifest.json"

        store = ParquetStore(str(data_dir))
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        timeframe = Timeframe.H1

        with DataCatalog(str(catalog_db)) as catalog:
            # Store multiple datasets
            for symbol in symbols:
                partition = "2024"
                file_path = store.write_bars(symbol, timeframe, sample_bars, partition)
                version_hash = compute_file_hash(file_path)

                catalog.register_file(
                    symbol=symbol,
                    timeframe=timeframe,
                    partition=partition,
                    file_path=str(file_path),
                    storage_format="parquet",
                    row_count=len(sample_bars),
                    min_timestamp=int(sample_bars["timestamp"].min()),
                    max_timestamp=int(sample_bars["timestamp"].max()),
                    data_source="test",
                    version_hash=version_hash,
                    file_size_bytes=file_path.stat().st_size,
                )

            # Generate manifest
            manifest = DataManifest(catalog)
            result = manifest.generate(manifest_path)
            assert result["total_files"] == 3

        # Verify manifest
        with DataCatalog(str(catalog_db)) as catalog:
            manifest = DataManifest(catalog)
            verification = manifest.verify(manifest_path, check_hashes=True)
            assert verification["valid"]
            assert verification["verified_files"] == 3

    def test_data_modification_detection(self, temp_dir, sample_bars):
        """
        Test that data modification is detected.
        """
        data_dir = temp_dir / "data"
        catalog_db = temp_dir / "catalog.db"
        manifest_path = temp_dir / "manifest.json"

        store = ParquetStore(str(data_dir))
        symbol = "EURUSD"
        timeframe = Timeframe.H1
        partition = "2024"

        # Store and register
        file_path = store.write_bars(symbol, timeframe, sample_bars, partition)
        version_hash = compute_file_hash(file_path)

        with DataCatalog(str(catalog_db)) as catalog:
            catalog.register_file(
                symbol=symbol,
                timeframe=timeframe,
                partition=partition,
                file_path=str(file_path),
                storage_format="parquet",
                row_count=len(sample_bars),
                min_timestamp=int(sample_bars["timestamp"].min()),
                max_timestamp=int(sample_bars["timestamp"].max()),
                data_source="test",
                version_hash=version_hash,
                file_size_bytes=file_path.stat().st_size,
            )

            # Generate manifest
            manifest = DataManifest(catalog)
            manifest.generate(manifest_path)

        # Modify file
        with open(file_path, "ab") as f:
            f.write(b"\x00")

        # Verify detects modification
        with DataCatalog(str(catalog_db)) as catalog:
            manifest = DataManifest(catalog)
            verification = manifest.verify(manifest_path, check_hashes=True)
            assert not verification["valid"]
            assert "Hash mismatch" in verification["issues"][0]
