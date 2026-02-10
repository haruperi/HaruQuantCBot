"""
HQT Trading System Database Layer.

This module provides database connectivity, ORM models, and repositories
for the HQT trading system.

Quick Start:
    ```python
    from hqt.foundation.database import DatabaseManager, Base, User, Strategy

    # Create database manager
    db = DatabaseManager("sqlite:///hqt.db")

    # Create tables
    db.create_all(Base)

    # Use session
    with db.get_session() as session:
        user = User(username="trader1", email="trader@example.com")
        session.add(user)
        session.commit()
    ```
"""

# Connection management
from .connection import DatabaseManager

# ORM models
from .models import (
    AccountSnapshot,
    Backtest,
    BacktestTrade,
    Base,
    EdgeResult,
    FinanceMetric,
    LiveTrade,
    Notification,
    Optimization,
    OptimizationResult,
    PaperTrade,
    Strategy,
    User,
    UserSetting,
)

# Repositories
from .repositories import (
    BacktestRepository,
    BaseRepository,
    NotificationRepository,
    OptimizationRepository,
    OptimizationResultRepository,
    StrategyRepository,
    TradeRepository,
    UserRepository,
)

__all__ = [
    # Connection
    "DatabaseManager",
    # Base
    "Base",
    # Models
    "User",
    "UserSetting",
    "Strategy",
    "Backtest",
    "BacktestTrade",
    "Optimization",
    "OptimizationResult",
    "LiveTrade",
    "PaperTrade",
    "AccountSnapshot",
    "FinanceMetric",
    "EdgeResult",
    "Notification",
    # Repositories
    "BaseRepository",
    "UserRepository",
    "StrategyRepository",
    "BacktestRepository",
    "TradeRepository",
    "OptimizationRepository",
    "OptimizationResultRepository",
    "NotificationRepository",
]
