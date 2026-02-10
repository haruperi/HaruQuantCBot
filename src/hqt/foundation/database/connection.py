"""
Database connection management for the HQT trading system.

This module provides DatabaseManager for managing SQLAlchemy 2.x connections
with connection pooling and session management.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from hqt.foundation.exceptions import ConfigError


class DatabaseManager:
    """
    Manages database connections with SQLAlchemy 2.x.

    Supports SQLite and PostgreSQL with connection pooling and
    session management via context manager.

    Example:
        ```python
        from hqt.foundation.database import DatabaseManager

        # SQLite (in-memory)
        db = DatabaseManager("sqlite:///:memory:")

        # SQLite (file-based)
        db = DatabaseManager("sqlite:///hqt.db")

        # PostgreSQL
        db = DatabaseManager("postgresql://user:pass@localhost/hqt")

        # Use session context manager
        with db.get_session() as session:
            # Perform database operations
            result = session.execute(text("SELECT 1"))
            session.commit()
        ```
    """

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        **engine_kwargs,
    ) -> None:
        """
        Initialize the database manager.

        Args:
            database_url: Database connection URL (SQLAlchemy format)
            echo: Echo SQL statements (useful for debugging)
            pool_size: Connection pool size (ignored for SQLite)
            max_overflow: Maximum overflow connections (ignored for SQLite)
            pool_timeout: Pool timeout in seconds (ignored for SQLite)
            pool_recycle: Connection recycle time in seconds (-1 = no recycle)
            **engine_kwargs: Additional engine kwargs passed to create_engine

        Raises:
            ConfigError: If database URL is invalid or connection fails

        Example:
            ```python
            # SQLite with debugging
            db = DatabaseManager("sqlite:///hqt.db", echo=True)

            # PostgreSQL with custom pool
            db = DatabaseManager(
                "postgresql://user:pass@localhost/hqt",
                pool_size=10,
                max_overflow=20,
                pool_timeout=60,
            )
            ```
        """
        self.database_url = database_url
        self.echo = echo
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None

        # Determine database type
        self.db_type = self._get_db_type(database_url)

        # Create engine with appropriate settings
        try:
            if self.db_type == "sqlite":
                self._engine = self._create_sqlite_engine(database_url, echo, **engine_kwargs)
            elif self.db_type == "postgresql":
                self._engine = self._create_postgresql_engine(
                    database_url,
                    echo,
                    pool_size,
                    max_overflow,
                    pool_timeout,
                    pool_recycle,
                    **engine_kwargs,
                )
            else:
                raise ConfigError(
                    error_code="DB-001",
                    module="database.connection",
                    message=f"Unsupported database type: {self.db_type}",
                    database_url=database_url,
                )

            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
            )

        except Exception as e:
            raise ConfigError(
                error_code="DB-002",
                module="database.connection",
                message=f"Failed to create database engine: {e}",
                database_url=database_url,
                error=str(e),
            ) from e

    def _get_db_type(self, url: str) -> str:
        """Extract database type from URL."""
        if url.startswith("sqlite"):
            return "sqlite"
        elif url.startswith("postgresql"):
            return "postgresql"
        else:
            # Try to extract from URL
            if "://" in url:
                return url.split("://")[0]
            return "unknown"

    def _create_sqlite_engine(self, url: str, echo: bool, **kwargs) -> Engine:
        """
        Create SQLite engine with optimized settings.

        Args:
            url: SQLite URL
            echo: Echo SQL statements
            **kwargs: Additional engine kwargs

        Returns:
            SQLAlchemy Engine
        """
        # SQLite-specific settings
        engine = create_engine(
            url,
            echo=echo,
            # Use StaticPool for SQLite (including in-memory) to maintain single connection
            poolclass=pool.StaticPool,
            **kwargs,
        )

        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            cursor.close()

        return engine

    def _create_postgresql_engine(
        self,
        url: str,
        echo: bool,
        pool_size: int,
        max_overflow: int,
        pool_timeout: int,
        pool_recycle: int,
        **kwargs,
    ) -> Engine:
        """
        Create PostgreSQL engine with connection pooling.

        Args:
            url: PostgreSQL URL
            echo: Echo SQL statements
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
            pool_timeout: Pool timeout in seconds
            pool_recycle: Connection recycle time in seconds
            **kwargs: Additional engine kwargs

        Returns:
            SQLAlchemy Engine
        """
        return create_engine(
            url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle if pool_recycle >= 0 else -1,
            pool_pre_ping=True,  # Verify connections before using
            **kwargs,
        )

    @property
    def engine(self) -> Engine:
        """
        Get the SQLAlchemy engine.

        Returns:
            SQLAlchemy Engine

        Raises:
            ConfigError: If engine is not initialized
        """
        if self._engine is None:
            raise ConfigError(
                error_code="DB-003",
                module="database.connection",
                message="Database engine not initialized",
            )
        return self._engine

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session via context manager.

        The session is automatically committed if no exceptions occur,
        and rolled back on exceptions.

        Yields:
            SQLAlchemy Session

        Raises:
            ConfigError: If session factory is not initialized

        Example:
            ```python
            from sqlalchemy import text

            # Successful transaction (auto-commit)
            with db.get_session() as session:
                result = session.execute(text("SELECT 1"))
                # Session commits automatically

            # Failed transaction (auto-rollback)
            try:
                with db.get_session() as session:
                    session.execute(text("INVALID SQL"))
            except Exception:
                # Session rolled back automatically
                pass
            ```
        """
        if self._session_factory is None:
            raise ConfigError(
                error_code="DB-004",
                module="database.connection",
                message="Session factory not initialized",
            )

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_all(self, base) -> None:
        """
        Create all tables defined in the Base metadata.

        Args:
            base: SQLAlchemy declarative base

        Example:
            ```python
            from hqt.foundation.database import Base, DatabaseManager

            db = DatabaseManager("sqlite:///hqt.db")
            db.create_all(Base)
            ```
        """
        base.metadata.create_all(self.engine)

    def drop_all(self, base) -> None:
        """
        Drop all tables defined in the Base metadata.

        Warning:
            This will delete all data! Use with caution.

        Args:
            base: SQLAlchemy declarative base

        Example:
            ```python
            from hqt.foundation.database import Base, DatabaseManager

            db = DatabaseManager("sqlite:///hqt.db")
            db.drop_all(Base)  # Deletes all tables and data!
            ```
        """
        base.metadata.drop_all(self.engine)

    def dispose(self) -> None:
        """
        Dispose of the connection pool.

        Closes all connections and cleans up resources.

        Example:
            ```python
            db = DatabaseManager("sqlite:///hqt.db")
            # ... use database ...
            db.dispose()  # Clean up
            ```
        """
        if self._engine is not None:
            self._engine.dispose()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - dispose of connections."""
        self.dispose()
