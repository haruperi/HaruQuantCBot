"""
Database backup and export utilities for HQT Trading System.

This module provides utilities for backing up and restoring the database,
as well as exporting and importing data in various formats.

[REQ: Database backup and recovery capabilities]
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from hqt.foundation.database.connection import DatabaseManager
from hqt.foundation.database.models import Base


class DatabaseBackup:
    """
    Database backup and restore utilities.

    Provides functionality to backup and restore SQLite databases,
    export/import data to JSON/CSV, and manage backup lifecycle.

    Example:
        ```python
        from hqt.foundation.database import DatabaseManager, DatabaseBackup

        db = DatabaseManager("sqlite:///hqt.db")
        backup = DatabaseBackup(db)

        # Create backup
        backup_path = backup.backup_database("backups/")

        # Restore from backup
        backup.restore_database(backup_path)

        # Export to JSON
        backup.export_to_json("users", "users_backup.json")
        ```
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize backup utility.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager

    def backup_database(
        self,
        backup_dir: str | Path,
        include_timestamp: bool = True,
    ) -> Path:
        """
        Create a full database backup (SQLite only).

        Args:
            backup_dir: Directory to store backup
            include_timestamp: Whether to include timestamp in filename

        Returns:
            Path to the backup file

        Raises:
            ValueError: If not using SQLite database
            IOError: If backup fails

        Example:
            ```python
            backup = DatabaseBackup(db_manager)
            backup_path = backup.backup_database("backups/")
            print(f"Backup created at: {backup_path}")
            ```
        """
        # Check if SQLite
        if not self.db_manager.url.startswith("sqlite"):
            raise ValueError("Database backup only supports SQLite databases")

        # Extract database file path
        db_path = self.db_manager.url.replace("sqlite:///", "")
        db_file = Path(db_path)

        if not db_file.exists():
            raise FileNotFoundError(f"Database file not found: {db_file}")

        # Create backup directory
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename
        if include_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"hqt_backup_{timestamp}.db"
        else:
            backup_filename = "hqt_backup.db"

        backup_path = backup_dir / backup_filename

        # Copy database file
        shutil.copy2(db_file, backup_path)

        return backup_path

    def restore_database(
        self,
        backup_path: str | Path,
        confirm: bool = False,
    ) -> None:
        """
        Restore database from backup (SQLite only).

        Args:
            backup_path: Path to backup file
            confirm: Must be True to proceed (safety check)

        Raises:
            ValueError: If not confirmed or not SQLite
            FileNotFoundError: If backup file not found

        Warning:
            This will overwrite the current database!

        Example:
            ```python
            backup = DatabaseBackup(db_manager)
            backup.restore_database("backups/hqt_backup_20240101.db", confirm=True)
            ```
        """
        if not confirm:
            raise ValueError(
                "Must set confirm=True to restore database (this will overwrite current data)"
            )

        # Check if SQLite
        if not self.db_manager.url.startswith("sqlite"):
            raise ValueError("Database restore only supports SQLite databases")

        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Extract database file path
        db_path = self.db_manager.url.replace("sqlite:///", "")
        db_file = Path(db_path)

        # Close all connections
        self.db_manager.dispose()

        # Restore backup
        shutil.copy2(backup_path, db_file)

    def export_table_to_json(
        self,
        table_name: str,
        output_path: str | Path,
        **filter_kwargs: Any,
    ) -> int:
        """
        Export table data to JSON file.

        Args:
            table_name: Name of table to export
            output_path: Path to output JSON file
            **filter_kwargs: Optional filters (e.g., user_id=1)

        Returns:
            Number of rows exported

        Example:
            ```python
            # Export all users
            count = backup.export_table_to_json("users", "users.json")

            # Export specific user's strategies
            count = backup.export_table_to_json(
                "strategies",
                "user1_strategies.json",
                user_id=1
            )
            ```
        """
        with self.db_manager.get_session() as session:
            # Get table class
            table = self._get_table_class(table_name)

            # Query with filters
            query = session.query(table)
            for key, value in filter_kwargs.items():
                query = query.filter(getattr(table, key) == value)

            # Fetch all rows
            rows = query.all()

            # Convert to dict
            data = []
            for row in rows:
                row_dict = {}
                for column in inspect(row).mapper.column_attrs:
                    value = getattr(row, column.key)
                    # Handle datetime serialization
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    row_dict[column.key] = value
                data.append(row_dict)

            # Write to JSON
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)

            return len(data)

    def export_table_to_csv(
        self,
        table_name: str,
        output_path: str | Path,
        **filter_kwargs: Any,
    ) -> int:
        """
        Export table data to CSV file.

        Args:
            table_name: Name of table to export
            output_path: Path to output CSV file
            **filter_kwargs: Optional filters

        Returns:
            Number of rows exported

        Example:
            ```python
            count = backup.export_table_to_csv("backtests", "backtests.csv")
            ```
        """
        with self.db_manager.get_session() as session:
            # Get table class
            table = self._get_table_class(table_name)

            # Query with filters
            query = session.query(table)
            for key, value in filter_kwargs.items():
                query = query.filter(getattr(table, key) == value)

            # Convert to DataFrame
            df = pd.read_sql(query.statement, session.bind)

            # Write to CSV
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False)

            return len(df)

    def import_table_from_json(
        self,
        table_name: str,
        input_path: str | Path,
        replace: bool = False,
    ) -> int:
        """
        Import table data from JSON file.

        Args:
            table_name: Name of table to import into
            input_path: Path to JSON file
            replace: If True, delete existing data first

        Returns:
            Number of rows imported

        Example:
            ```python
            count = backup.import_table_from_json("users", "users.json")
            ```
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Load JSON
        with open(input_path) as f:
            data = json.load(f)

        # Get table class
        table = self._get_table_class(table_name)

        with self.db_manager.get_session() as session:
            # Delete existing data if replace=True
            if replace:
                session.execute(text(f"DELETE FROM {table_name}"))

            # Insert rows
            for row_dict in data:
                row = table(**row_dict)
                session.add(row)

            session.commit()

        return len(data)

    def export_all_tables(
        self,
        output_dir: str | Path,
        format: str = "json",
    ) -> dict[str, int]:
        """
        Export all tables to files.

        Args:
            output_dir: Directory to store exported files
            format: Export format ('json' or 'csv')

        Returns:
            Dictionary mapping table names to row counts

        Example:
            ```python
            counts = backup.export_all_tables("exports/", format="json")
            print(f"Exported {sum(counts.values())} total rows")
            ```
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        # Get all tables
        for table in Base.metadata.sorted_tables:
            table_name = table.name
            output_path = output_dir / f"{table_name}.{format}"

            try:
                if format == "json":
                    count = self.export_table_to_json(table_name, output_path)
                elif format == "csv":
                    count = self.export_table_to_csv(table_name, output_path)
                else:
                    raise ValueError(f"Unknown format: {format}")

                results[table_name] = count
            except Exception as e:
                print(f"Warning: Failed to export {table_name}: {e}")
                results[table_name] = 0

        return results

    def get_database_stats(self) -> dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with table names and row counts

        Example:
            ```python
            stats = backup.get_database_stats()
            print(f"Users: {stats['tables']['users']}")
            ```
        """
        stats = {
            "url": self.db_manager.url,
            "tables": {},
            "total_rows": 0,
        }

        with self.db_manager.get_session() as session:
            for table in Base.metadata.sorted_tables:
                table_name = table.name
                count = session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                ).scalar()
                stats["tables"][table_name] = count
                stats["total_rows"] += count

        return stats

    def _get_table_class(self, table_name: str):
        """Get SQLAlchemy table class by name."""
        for mapper in Base.registry.mappers:
            if mapper.class_.__tablename__ == table_name:
                return mapper.class_
        raise ValueError(f"Table not found: {table_name}")


def create_backup(
    db_url: str,
    backup_dir: str = "backups",
) -> Path:
    """
    Convenience function to create a database backup.

    Args:
        db_url: Database URL
        backup_dir: Backup directory

    Returns:
        Path to backup file

    Example:
        ```python
        from hqt.foundation.database.backup import create_backup

        backup_path = create_backup("sqlite:///hqt.db", "backups/")
        ```
    """
    db = DatabaseManager(db_url)
    backup = DatabaseBackup(db)
    return backup.backup_database(backup_dir)
