"""
Repository pattern for database operations.

Provides CRUD operations for all entities with a consistent interface.
"""

from datetime import datetime
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Backtest,
    BacktestTrade,
    Notification,
    Optimization,
    OptimizationResult,
    Strategy,
    User,
)

# Generic type for models
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""

    def __init__(self, session: Session, model_class: Type[T]):
        """
        Initialize repository.

        Args:
            session: SQLAlchemy session
            model_class: Model class
        """
        self.session = session
        self.model_class = model_class

    def create(self, **kwargs) -> T:
        """
        Create a new entity.

        Args:
            **kwargs: Entity fields

        Returns:
            Created entity
        """
        entity = self.model_class(**kwargs)
        self.session.add(entity)
        self.session.flush()
        return entity

    def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity or None
        """
        return self.session.get(self.model_class, entity_id)

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        Get all entities.

        Args:
            limit: Maximum number of entities
            offset: Offset for pagination

        Returns:
            List of entities
        """
        stmt = select(self.model_class).offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt))

    def update(self, entity: T) -> T:
        """
        Update entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity
        """
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete(self, entity: T) -> None:
        """
        Delete entity.

        Args:
            entity: Entity to delete
        """
        self.session.delete(entity)
        self.session.flush()

    def delete_by_id(self, entity_id: int) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        entity = self.get_by_id(entity_id)
        if entity:
            self.delete(entity)
            return True
        return False

    def count(self) -> int:
        """
        Count total entities.

        Returns:
            Count
        """
        stmt = select(self.model_class)
        return len(list(self.session.scalars(stmt)))


class UserRepository(BaseRepository[User]):
    """Repository for User entities."""

    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        return self.session.scalar(stmt)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        return self.session.scalar(stmt)

    def get_active_users(self) -> List[User]:
        """Get all active users."""
        stmt = select(User).where(User.is_active == True)
        return list(self.session.scalars(stmt))


class StrategyRepository(BaseRepository[Strategy]):
    """Repository for Strategy entities."""

    def __init__(self, session: Session):
        super().__init__(session, Strategy)

    def get_by_user(self, user_id: int) -> List[Strategy]:
        """Get strategies for a user."""
        stmt = select(Strategy).where(Strategy.user_id == user_id)
        return list(self.session.scalars(stmt))

    def get_active_by_user(self, user_id: int) -> List[Strategy]:
        """Get active strategies for a user."""
        stmt = select(Strategy).where(
            Strategy.user_id == user_id,
            Strategy.is_active == True
        )
        return list(self.session.scalars(stmt))


class BacktestRepository(BaseRepository[Backtest]):
    """Repository for Backtest entities."""

    def __init__(self, session: Session):
        super().__init__(session, Backtest)

    def get_by_user(self, user_id: int) -> List[Backtest]:
        """Get backtests for a user."""
        stmt = select(Backtest).where(Backtest.user_id == user_id).order_by(Backtest.created_at.desc())
        return list(self.session.scalars(stmt))

    def get_by_strategy(self, strategy_id: int) -> List[Backtest]:
        """Get backtests for a strategy."""
        stmt = select(Backtest).where(Backtest.strategy_id == strategy_id).order_by(Backtest.created_at.desc())
        return list(self.session.scalars(stmt))

    def get_completed(self, user_id: Optional[int] = None) -> List[Backtest]:
        """Get completed backtests."""
        stmt = select(Backtest).where(Backtest.status == "completed")
        if user_id:
            stmt = stmt.where(Backtest.user_id == user_id)
        stmt = stmt.order_by(Backtest.completed_at.desc())
        return list(self.session.scalars(stmt))

    def update_status(self, backtest_id: int, status: str) -> Optional[Backtest]:
        """Update backtest status."""
        backtest = self.get_by_id(backtest_id)
        if backtest:
            backtest.status = status
            if status == "completed":
                backtest.completed_at = datetime.utcnow()
            self.session.flush()
        return backtest


class TradeRepository(BaseRepository[BacktestTrade]):
    """Repository for BacktestTrade entities."""

    def __init__(self, session: Session):
        super().__init__(session, BacktestTrade)

    def get_by_backtest(self, backtest_id: int) -> List[BacktestTrade]:
        """Get trades for a backtest."""
        stmt = select(BacktestTrade).where(BacktestTrade.backtest_id == backtest_id).order_by(BacktestTrade.entry_time)
        return list(self.session.scalars(stmt))

    def get_winning_trades(self, backtest_id: int) -> List[BacktestTrade]:
        """Get winning trades for a backtest."""
        stmt = select(BacktestTrade).where(
            BacktestTrade.backtest_id == backtest_id,
            BacktestTrade.profit > 0
        )
        return list(self.session.scalars(stmt))

    def get_losing_trades(self, backtest_id: int) -> List[BacktestTrade]:
        """Get losing trades for a backtest."""
        stmt = select(BacktestTrade).where(
            BacktestTrade.backtest_id == backtest_id,
            BacktestTrade.profit < 0
        )
        return list(self.session.scalars(stmt))


class OptimizationRepository(BaseRepository[Optimization]):
    """Repository for Optimization entities."""

    def __init__(self, session: Session):
        super().__init__(session, Optimization)

    def get_by_user(self, user_id: int) -> List[Optimization]:
        """Get optimizations for a user."""
        stmt = select(Optimization).where(Optimization.user_id == user_id).order_by(Optimization.created_at.desc())
        return list(self.session.scalars(stmt))

    def get_by_strategy(self, strategy_id: int) -> List[Optimization]:
        """Get optimizations for a strategy."""
        stmt = select(Optimization).where(Optimization.strategy_id == strategy_id).order_by(Optimization.created_at.desc())
        return list(self.session.scalars(stmt))

    def get_running(self) -> List[Optimization]:
        """Get running optimizations."""
        stmt = select(Optimization).where(Optimization.status == "running")
        return list(self.session.scalars(stmt))

    def update_progress(
        self,
        optimization_id: int,
        completed_iterations: int,
        best_score: Optional[float] = None,
        best_parameters: Optional[str] = None,
    ) -> Optional[Optimization]:
        """Update optimization progress."""
        opt = self.get_by_id(optimization_id)
        if opt:
            opt.completed_iterations = completed_iterations
            if best_score is not None:
                opt.best_score = best_score
            if best_parameters is not None:
                opt.best_parameters = best_parameters
            self.session.flush()
        return opt


class OptimizationResultRepository(BaseRepository[OptimizationResult]):
    """Repository for OptimizationResult entities."""

    def __init__(self, session: Session):
        super().__init__(session, OptimizationResult)

    def get_by_optimization(self, optimization_id: int) -> List[OptimizationResult]:
        """Get results for an optimization."""
        stmt = select(OptimizationResult).where(
            OptimizationResult.optimization_id == optimization_id
        ).order_by(OptimizationResult.iteration)
        return list(self.session.scalars(stmt))

    def get_best_results(self, optimization_id: int, limit: int = 10) -> List[OptimizationResult]:
        """Get best results for an optimization."""
        stmt = select(OptimizationResult).where(
            OptimizationResult.optimization_id == optimization_id
        ).order_by(OptimizationResult.score.desc()).limit(limit)
        return list(self.session.scalars(stmt))


class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification entities."""

    def __init__(self, session: Session):
        super().__init__(session, Notification)

    def get_by_user(self, user_id: int, unread_only: bool = False) -> List[Notification]:
        """Get notifications for a user."""
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        stmt = stmt.order_by(Notification.created_at.desc())
        return list(self.session.scalars(stmt))

    def mark_as_read(self, notification_id: int) -> Optional[Notification]:
        """Mark notification as read."""
        notif = self.get_by_id(notification_id)
        if notif and notif.read_at is None:
            notif.read_at = datetime.utcnow()
            self.session.flush()
        return notif

    def mark_all_as_read(self, user_id: int) -> int:
        """Mark all user notifications as read."""
        notifications = self.get_by_user(user_id, unread_only=True)
        count = 0
        for notif in notifications:
            notif.read_at = datetime.utcnow()
            count += 1
        self.session.flush()
        return count
