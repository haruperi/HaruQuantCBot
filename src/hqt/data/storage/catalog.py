"""
Data catalog for HQT Trading System.

This module provides metadata tracking for stored market data using SQLite.
Tracks symbols, timeframes, date ranges, sources, and version hashes.

[REQ: DAT-FR-024] Data catalog with metadata tracking
[SDD: §5.2] Data Storage Architecture
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from hqt.data.models.bar import Timeframe


class DataCatalog:
    """
    SQLite-based data catalog for metadata tracking.

    Tracks metadata about all stored data files including symbols, timeframes,
    date ranges, row counts, data sources, download timestamps, file paths,
    and version hashes.

    Database Schema:
        ```sql
        CREATE TABLE catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT,  -- NULL for ticks
            partition TEXT NOT NULL,
            file_path TEXT NOT NULL UNIQUE,
            storage_format TEXT NOT NULL,  -- 'parquet' or 'hdf5'
            row_count INTEGER NOT NULL,
            min_timestamp INTEGER NOT NULL,
            max_timestamp INTEGER NOT NULL,
            data_source TEXT,  -- Provider used (e.g., 'mt5', 'dukascopy')
            download_timestamp INTEGER NOT NULL,
            version_hash TEXT,  -- SHA-256 content hash
            file_size_bytes INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );

        CREATE INDEX idx_symbol ON catalog(symbol);
        CREATE INDEX idx_symbol_timeframe ON catalog(symbol, timeframe);
        CREATE INDEX idx_timestamps ON catalog(min_timestamp, max_timestamp);
        ```

    Example:
        ```python
        from hqt.data.storage import DataCatalog
        from hqt.data.models import Timeframe
        from datetime import datetime

        catalog = DataCatalog("data/catalog.db")

        # Register a file
        catalog.register_file(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
            file_path="data/parquet/EURUSD/H1/2024.parquet",
            storage_format="parquet",
            row_count=8760,
            min_timestamp=int(datetime(2024, 1, 1).timestamp() * 1_000_000),
            max_timestamp=int(datetime(2024, 12, 31, 23).timestamp() * 1_000_000),
            data_source="mt5",
            version_hash="abc123...",
        )

        # Query available data
        available = catalog.query_available(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
        )
        print(f"Found {len(available)} partitions")

        # Get file metadata
        metadata = catalog.get_metadata(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            partition="2024",
        )
        print(f"Row count: {metadata['row_count']}")
        ```
    """

    def __init__(self, db_path: str | Path = "data/catalog.db"):
        """
        Initialize data catalog.

        Args:
            db_path: Path to SQLite database file

        Note:
            Database and tables are created automatically if they don't exist.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT,
                    partition TEXT NOT NULL,
                    file_path TEXT NOT NULL UNIQUE,
                    storage_format TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    min_timestamp INTEGER NOT NULL,
                    max_timestamp INTEGER NOT NULL,
                    data_source TEXT,
                    download_timestamp INTEGER NOT NULL,
                    version_hash TEXT,
                    file_size_bytes INTEGER,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_symbol ON catalog(symbol)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_symbol_timeframe "
                "ON catalog(symbol, timeframe)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamps "
                "ON catalog(min_timestamp, max_timestamp)"
            )

            conn.commit()

    def register_file(
        self,
        symbol: str,
        timeframe: Timeframe | None,
        partition: str,
        file_path: str | Path,
        storage_format: str,
        row_count: int,
        min_timestamp: int,
        max_timestamp: int,
        data_source: str | None = None,
        version_hash: str | None = None,
        file_size_bytes: int | None = None,
    ) -> int:
        """
        Register a data file in the catalog.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (None for ticks)
            partition: Partition identifier
            file_path: Path to data file
            storage_format: Storage format ('parquet' or 'hdf5')
            row_count: Number of rows in file
            min_timestamp: Minimum timestamp (microseconds)
            max_timestamp: Maximum timestamp (microseconds)
            data_source: Data source/provider (e.g., 'mt5', 'dukascopy')
            version_hash: SHA-256 content hash
            file_size_bytes: File size in bytes

        Returns:
            Catalog entry ID

        Note:
            If file is already registered, updates the existing entry.
        """
        file_path = str(Path(file_path).absolute())
        timeframe_str = timeframe.name if timeframe else None
        now = int(datetime.now().timestamp())

        # Get file size if not provided
        if file_size_bytes is None:
            path = Path(file_path)
            if path.exists():
                file_size_bytes = path.stat().st_size

        with sqlite3.connect(self.db_path) as conn:
            # Check if file already registered
            cursor = conn.execute(
                "SELECT id FROM catalog WHERE file_path = ?", (file_path,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing entry
                conn.execute(
                    """
                    UPDATE catalog
                    SET symbol = ?, timeframe = ?, partition = ?,
                        storage_format = ?, row_count = ?,
                        min_timestamp = ?, max_timestamp = ?,
                        data_source = ?, version_hash = ?,
                        file_size_bytes = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        symbol,
                        timeframe_str,
                        partition,
                        storage_format,
                        row_count,
                        min_timestamp,
                        max_timestamp,
                        data_source,
                        version_hash,
                        file_size_bytes,
                        now,
                        existing[0],
                    ),
                )
                conn.commit()
                return existing[0]
            else:
                # Insert new entry
                cursor = conn.execute(
                    """
                    INSERT INTO catalog (
                        symbol, timeframe, partition, file_path,
                        storage_format, row_count, min_timestamp,
                        max_timestamp, data_source, download_timestamp,
                        version_hash, file_size_bytes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol,
                        timeframe_str,
                        partition,
                        file_path,
                        storage_format,
                        row_count,
                        min_timestamp,
                        max_timestamp,
                        data_source,
                        now,
                        version_hash,
                        file_size_bytes,
                        now,
                        now,
                    ),
                )
                conn.commit()
                return cursor.lastrowid

    def query_available(
        self,
        symbol: str | None = None,
        timeframe: Timeframe | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        storage_format: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query available data in catalog.

        Args:
            symbol: Trading symbol (None = all symbols)
            timeframe: Bar timeframe (None = all timeframes including ticks)
            start: Start datetime (UTC)
            end: End datetime (UTC)
            storage_format: Storage format filter ('parquet' or 'hdf5')

        Returns:
            List of catalog entries matching criteria

        Example:
            ```python
            # All EURUSD data
            entries = catalog.query_available(symbol="EURUSD")

            # H1 bars only
            entries = catalog.query_available(
                symbol="EURUSD",
                timeframe=Timeframe.H1,
            )

            # Data in 2024
            entries = catalog.query_available(
                symbol="EURUSD",
                start=datetime(2024, 1, 1),
                end=datetime(2025, 1, 1),
            )
            ```
        """
        query = "SELECT * FROM catalog WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if timeframe is not None:
            query += " AND timeframe = ?"
            params.append(timeframe.name)

        if start:
            start_us = int(start.timestamp() * 1_000_000)
            query += " AND max_timestamp >= ?"
            params.append(start_us)

        if end:
            end_us = int(end.timestamp() * 1_000_000)
            query += " AND min_timestamp < ?"
            params.append(end_us)

        if storage_format:
            query += " AND storage_format = ?"
            params.append(storage_format)

        query += " ORDER BY symbol, timeframe, partition"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_metadata(
        self,
        symbol: str,
        timeframe: Timeframe | None,
        partition: str,
    ) -> dict[str, Any]:
        """
        Get metadata for a specific file.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (None for ticks)
            partition: Partition identifier

        Returns:
            Metadata dictionary

        Raises:
            KeyError: File not found in catalog
        """
        timeframe_str = timeframe.name if timeframe else None

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM catalog
                WHERE symbol = ? AND timeframe IS ? AND partition = ?
                """,
                (symbol, timeframe_str, partition),
            )
            row = cursor.fetchone()

            if row is None:
                raise KeyError(
                    f"No catalog entry for {symbol} {timeframe} {partition}"
                )

            return dict(row)

    def get_file_path(
        self,
        symbol: str,
        timeframe: Timeframe | None,
        partition: str,
    ) -> Path:
        """
        Get file path for a symbol/timeframe/partition.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (None for ticks)
            partition: Partition identifier

        Returns:
            Path to data file

        Raises:
            KeyError: File not found in catalog
        """
        metadata = self.get_metadata(symbol, timeframe, partition)
        return Path(metadata["file_path"])

    def list_symbols(self) -> list[str]:
        """
        List all symbols in catalog.

        Returns:
            List of unique symbol names
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT DISTINCT symbol FROM catalog ORDER BY symbol"
            )
            return [row[0] for row in cursor.fetchall()]

    def list_timeframes(self, symbol: str) -> list[Timeframe | None]:
        """
        List all timeframes available for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of timeframes (None for ticks)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT timeframe FROM catalog
                WHERE symbol = ?
                ORDER BY timeframe
                """,
                (symbol,),
            )
            timeframes = []
            for (tf_str,) in cursor.fetchall():
                if tf_str is None:
                    timeframes.append(None)
                else:
                    timeframes.append(Timeframe[tf_str])
            return timeframes

    def list_partitions(
        self,
        symbol: str,
        timeframe: Timeframe | None,
    ) -> list[str]:
        """
        List all partitions for a symbol/timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (None for ticks)

        Returns:
            List of partition identifiers
        """
        timeframe_str = timeframe.name if timeframe else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT partition FROM catalog
                WHERE symbol = ? AND timeframe IS ?
                ORDER BY partition
                """,
                (symbol, timeframe_str),
            )
            return [row[0] for row in cursor.fetchall()]

    def delete_entry(
        self,
        symbol: str,
        timeframe: Timeframe | None,
        partition: str,
    ) -> bool:
        """
        Delete a catalog entry.

        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe (None for ticks)
            partition: Partition identifier

        Returns:
            True if entry was deleted, False if not found

        Note:
            This only deletes the catalog entry, not the actual file.
        """
        timeframe_str = timeframe.name if timeframe else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM catalog
                WHERE symbol = ? AND timeframe IS ? AND partition = ?
                """,
                (symbol, timeframe_str, partition),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> dict[str, Any]:
        """
        Get catalog statistics.

        Returns:
            Dictionary with statistics:
                - total_entries: Total number of catalog entries
                - total_symbols: Number of unique symbols
                - total_rows: Total rows across all files
                - total_size_bytes: Total file size in bytes
                - storage_formats: Count by format
                - data_sources: Count by source
        """
        with sqlite3.connect(self.db_path) as conn:
            # Total entries
            cursor = conn.execute("SELECT COUNT(*) FROM catalog")
            total_entries = cursor.fetchone()[0]

            # Unique symbols
            cursor = conn.execute("SELECT COUNT(DISTINCT symbol) FROM catalog")
            total_symbols = cursor.fetchone()[0]

            # Total rows
            cursor = conn.execute("SELECT SUM(row_count) FROM catalog")
            total_rows = cursor.fetchone()[0] or 0

            # Total size
            cursor = conn.execute("SELECT SUM(file_size_bytes) FROM catalog")
            total_size = cursor.fetchone()[0] or 0

            # By format
            cursor = conn.execute(
                """
                SELECT storage_format, COUNT(*), SUM(row_count)
                FROM catalog
                GROUP BY storage_format
                """
            )
            formats = {row[0]: {"count": row[1], "rows": row[2]} for row in cursor}

            # By source
            cursor = conn.execute(
                """
                SELECT data_source, COUNT(*), SUM(row_count)
                FROM catalog
                WHERE data_source IS NOT NULL
                GROUP BY data_source
                """
            )
            sources = {row[0]: {"count": row[1], "rows": row[2]} for row in cursor}

            return {
                "total_entries": total_entries,
                "total_symbols": total_symbols,
                "total_rows": total_rows,
                "total_size_bytes": total_size,
                "storage_formats": formats,
                "data_sources": sources,
            }

    def close(self) -> None:
        """Close catalog (no-op for SQLite)."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
