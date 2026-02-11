"""
Data lineage tracking for HQT Trading System.

This module provides lineage tracking to record what data was used in each
backtest, enabling exact reproduction and verification.

[REQ: DAT-FR-027] Backtest records data version hashes
[REQ: DAT-FR-029] Data lineage query
[SDD: §5.2] Data Storage Architecture
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from hqt.data.versioning.hasher import verify_file_hash


class DataLineage:
    """
    SQLite-based data lineage tracking.

    Records the exact data versions (file hashes) used in each backtest,
    enabling reproducibility verification and auditing.

    Database Schema:
        ```sql
        CREATE TABLE lineage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backtest_id INTEGER NOT NULL,
            data_file_path TEXT NOT NULL,
            data_version_hash TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT,
            partition TEXT,
            recorded_at INTEGER NOT NULL
        );

        CREATE INDEX idx_backtest ON lineage(backtest_id);
        CREATE INDEX idx_hash ON lineage(data_version_hash);
        ```

    Example:
        ```python
        from hqt.data.versioning import DataLineage

        lineage = DataLineage("data/lineage.db")

        # Record data used in backtest
        lineage.record_backtest_lineage(
            backtest_id=1,
            data_files=[
                {
                    "file_path": "data/parquet/EURUSD/H1/2024.parquet",
                    "version_hash": "abc123...",
                    "symbol": "EURUSD",
                    "timeframe": "H1",
                    "partition": "2024",
                }
            ],
        )

        # Later, verify backtest can be reproduced
        can_reproduce = lineage.can_reproduce(backtest_id=1)
        if can_reproduce["reproducible"]:
            print("Backtest can be exactly reproduced")
        else:
            print(f"Cannot reproduce: {can_reproduce['issues']}")

        # Get lineage
        lineage_info = lineage.get_lineage(backtest_id=1)
        print(f"Used {len(lineage_info['data_files'])} data files")
        ```
    """

    def __init__(self, db_path: str | Path = "data/lineage.db"):
        """
        Initialize data lineage tracker.

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
                CREATE TABLE IF NOT EXISTS lineage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backtest_id INTEGER NOT NULL,
                    data_file_path TEXT NOT NULL,
                    data_version_hash TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT,
                    partition TEXT,
                    recorded_at INTEGER NOT NULL
                )
                """
            )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_backtest ON lineage(backtest_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_hash ON lineage(data_version_hash)"
            )

            conn.commit()

    def record_backtest_lineage(
        self,
        backtest_id: int,
        data_files: list[dict[str, Any]],
    ) -> int:
        """
        Record data files used in a backtest.

        Args:
            backtest_id: Backtest database ID
            data_files: List of dictionaries with:
                - file_path: Path to data file
                - version_hash: SHA-256 hash of file content
                - symbol: Trading symbol
                - timeframe: Bar timeframe (None for ticks)
                - partition: Partition identifier

        Returns:
            Number of entries recorded

        Example:
            ```python
            lineage.record_backtest_lineage(
                backtest_id=123,
                data_files=[
                    {
                        "file_path": "data/parquet/EURUSD/H1/2024.parquet",
                        "version_hash": "abc123def456...",
                        "symbol": "EURUSD",
                        "timeframe": "H1",
                        "partition": "2024",
                    },
                    {
                        "file_path": "data/parquet/GBPUSD/H1/2024.parquet",
                        "version_hash": "789xyz...",
                        "symbol": "GBPUSD",
                        "timeframe": "H1",
                        "partition": "2024",
                    },
                ],
            )
            ```

        Note:
            This creates a permanent record. If the same backtest_id is
            recorded again, it creates additional entries (doesn't overwrite).
        """
        now = int(datetime.now().timestamp())

        with sqlite3.connect(self.db_path) as conn:
            for data_file in data_files:
                conn.execute(
                    """
                    INSERT INTO lineage (
                        backtest_id, data_file_path, data_version_hash,
                        symbol, timeframe, partition, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        backtest_id,
                        data_file["file_path"],
                        data_file["version_hash"],
                        data_file["symbol"],
                        data_file.get("timeframe"),
                        data_file.get("partition"),
                        now,
                    ),
                )

            conn.commit()

        return len(data_files)

    def get_lineage(self, backtest_id: int) -> dict[str, Any]:
        """
        Get data lineage for a backtest.

        Args:
            backtest_id: Backtest database ID

        Returns:
            Dictionary with:
                - backtest_id: Backtest ID
                - data_files: List of data file records
                - total_files: Number of data files
                - recorded_at: Timestamp of first record

        Raises:
            KeyError: Backtest not found

        Example:
            ```python
            lineage_info = lineage.get_lineage(backtest_id=123)
            print(f"Backtest {lineage_info['backtest_id']}")
            print(f"Used {lineage_info['total_files']} data files:")
            for f in lineage_info['data_files']:
                print(f"  - {f['symbol']} {f['timeframe']} {f['partition']}")
                print(f"    Hash: {f['version_hash']}")
            ```
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM lineage
                WHERE backtest_id = ?
                ORDER BY symbol, timeframe, partition
                """,
                (backtest_id,),
            )
            rows = cursor.fetchall()

            if not rows:
                raise KeyError(f"No lineage found for backtest {backtest_id}")

            data_files = [dict(row) for row in rows]

            return {
                "backtest_id": backtest_id,
                "data_files": data_files,
                "total_files": len(data_files),
                "recorded_at": data_files[0]["recorded_at"],
            }

    def can_reproduce(self, backtest_id: int) -> dict[str, Any]:
        """
        Check if a backtest can be exactly reproduced.

        Verifies that:
        1. All data files still exist
        2. File hashes match recorded hashes (data unchanged)

        Args:
            backtest_id: Backtest database ID

        Returns:
            Dictionary with:
                - reproducible: bool - True if can be reproduced
                - issues: list[str] - Issues preventing reproduction
                - verified_files: int - Number of files verified
                - total_files: int - Total files in lineage

        Example:
            ```python
            result = lineage.can_reproduce(backtest_id=123)

            if result["reproducible"]:
                print("✓ Backtest can be exactly reproduced")
            else:
                print("✗ Cannot reproduce backtest:")
                for issue in result["issues"]:
                    print(f"  - {issue}")
            ```

        Note:
            This method does NOT verify strategy code or engine version.
            It only checks data files.
        """
        try:
            lineage_info = self.get_lineage(backtest_id)
        except KeyError:
            return {
                "reproducible": False,
                "issues": [f"No lineage found for backtest {backtest_id}"],
                "verified_files": 0,
                "total_files": 0,
            }

        issues = []
        verified_files = 0

        for data_file in lineage_info["data_files"]:
            file_path = Path(data_file["data_file_path"])
            expected_hash = data_file["data_version_hash"]

            # Check file exists
            if not file_path.exists():
                issues.append(
                    f"Missing file: {file_path} "
                    f"({data_file['symbol']} {data_file['timeframe']} {data_file['partition']})"
                )
                continue

            # Verify hash
            try:
                if not verify_file_hash(file_path, expected_hash):
                    issues.append(
                        f"Hash mismatch: {file_path} "
                        f"({data_file['symbol']} {data_file['timeframe']} {data_file['partition']}) "
                        f"- data has been modified"
                    )
                    continue
            except Exception as e:
                issues.append(
                    f"Hash verification failed: {file_path} - {e}"
                )
                continue

            verified_files += 1

        return {
            "reproducible": len(issues) == 0,
            "issues": issues,
            "verified_files": verified_files,
            "total_files": lineage_info["total_files"],
        }

    def get_data_versions(self, backtest_id: int) -> list[str]:
        """
        Get list of data version hashes for a backtest.

        Args:
            backtest_id: Backtest database ID

        Returns:
            List of unique version hashes

        Example:
            ```python
            hashes = lineage.get_data_versions(backtest_id=123)
            print(f"Backtest uses {len(hashes)} unique data versions")
            for hash_value in hashes:
                print(f"  - {hash_value}")
            ```
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT data_version_hash FROM lineage
                WHERE backtest_id = ?
                ORDER BY data_version_hash
                """,
                (backtest_id,),
            )
            return [row[0] for row in cursor.fetchall()]

    def find_backtests_using_data(
        self,
        version_hash: str,
    ) -> list[int]:
        """
        Find all backtests that used a specific data version.

        Args:
            version_hash: Data version hash to search for

        Returns:
            List of backtest IDs

        Example:
            ```python
            # Find which backtests used this data file
            backtests = lineage.find_backtests_using_data(
                version_hash="abc123..."
            )
            print(f"Data used in {len(backtests)} backtests: {backtests}")
            ```

        Note:
            Useful for impact analysis when data is updated.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT backtest_id FROM lineage
                WHERE data_version_hash = ?
                ORDER BY backtest_id
                """,
                (version_hash,),
            )
            return [row[0] for row in cursor.fetchall()]

    def delete_lineage(self, backtest_id: int) -> int:
        """
        Delete lineage records for a backtest.

        Args:
            backtest_id: Backtest database ID

        Returns:
            Number of records deleted

        Warning:
            This permanently deletes lineage information. Only use when
            deleting a backtest permanently.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM lineage WHERE backtest_id = ?",
                (backtest_id,),
            )
            conn.commit()
            return cursor.rowcount

    def get_stats(self) -> dict[str, Any]:
        """
        Get lineage database statistics.

        Returns:
            Dictionary with statistics:
                - total_backtests: Number of unique backtests
                - total_records: Total lineage records
                - total_data_versions: Unique data versions

        Example:
            ```python
            stats = lineage.get_stats()
            print(f"Tracking {stats['total_backtests']} backtests")
            print(f"Using {stats['total_data_versions']} data versions")
            ```
        """
        with sqlite3.connect(self.db_path) as conn:
            # Total backtests
            cursor = conn.execute("SELECT COUNT(DISTINCT backtest_id) FROM lineage")
            total_backtests = cursor.fetchone()[0]

            # Total records
            cursor = conn.execute("SELECT COUNT(*) FROM lineage")
            total_records = cursor.fetchone()[0]

            # Unique data versions
            cursor = conn.execute("SELECT COUNT(DISTINCT data_version_hash) FROM lineage")
            total_data_versions = cursor.fetchone()[0]

            return {
                "total_backtests": total_backtests,
                "total_records": total_records,
                "total_data_versions": total_data_versions,
            }

    def close(self) -> None:
        """Close lineage database (no-op for SQLite)."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
