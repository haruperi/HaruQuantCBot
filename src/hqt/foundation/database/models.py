"""
SQLAlchemy ORM models for the HQT trading system.

This module defines all database models per SDD §17.2.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


# ============================================================================
# User and Settings
# ============================================================================


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    settings: Mapped[list["UserSetting"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    strategies: Mapped[list["Strategy"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    backtests: Mapped[list["Backtest"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    optimizations: Mapped[list["Optimization"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class UserSetting(Base):
    """User settings and preferences."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one setting per key per user
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_setting"),)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="settings")

    def __repr__(self) -> str:
        return f"<UserSetting(user_id={self.user_id}, key='{self.key}')>"


# ============================================================================
# Strategy
# ============================================================================


class Strategy(Base):
    """Trading strategy model."""

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    class_name: Mapped[str] = mapped_column(String(255), nullable=False)  # Python class name
    parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON parameters
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="strategies")
    backtests: Mapped[list["Backtest"]] = relationship(back_populates="strategy", cascade="all, delete-orphan")
    optimizations: Mapped[list["Optimization"]] = relationship(back_populates="strategy", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name='{self.name}')>"


# ============================================================================
# Backtesting
# ============================================================================


class Backtest(Base):
    """Backtest session model."""

    __tablename__ = "backtests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)  # M1, M5, H1, etc.
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Float, nullable=False)
    final_capital: Mapped[float] = mapped_column(Float, nullable=False)
    total_return: Mapped[float] = mapped_column(Float, nullable=False)  # Percentage
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Percentage
    win_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Percentage
    profit_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed

    # Relationships
    user: Mapped["User"] = relationship(back_populates="backtests")
    strategy: Mapped["Strategy"] = relationship(back_populates="backtests")
    trades: Mapped[list["BacktestTrade"]] = relationship(back_populates="backtest", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Backtest(id={self.id}, name='{self.name}', status='{self.status}')>"


class BacktestTrade(Base):
    """Individual trade from backtest."""

    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    backtest_id: Mapped[int] = mapped_column(ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # long, short
    entry_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    exit_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)  # Lot size
    profit: Mapped[float] = mapped_column(Float, nullable=False)  # In account currency
    profit_pct: Mapped[float] = mapped_column(Float, nullable=False)  # Percentage
    stop_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    take_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # signal, sl, tp, timeout

    # Relationships
    backtest: Mapped["Backtest"] = relationship(back_populates="trades")

    def __repr__(self) -> str:
        return f"<BacktestTrade(id={self.id}, symbol='{self.symbol}', direction='{self.direction}', profit={self.profit})>"


# ============================================================================
# Optimization
# ============================================================================


class Optimization(Base):
    """Parameter optimization session."""

    __tablename__ = "optimizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)  # grid, bayesian, genetic
    objective: Mapped[str] = mapped_column(String(50), nullable=False)  # sharpe, profit_factor, etc.
    parameter_space: Mapped[str] = mapped_column(Text, nullable=False)  # JSON parameter ranges
    total_iterations: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_iterations: Mapped[int] = mapped_column(Integer, default=0)
    best_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed, cancelled

    # Relationships
    user: Mapped["User"] = relationship(back_populates="optimizations")
    strategy: Mapped["Strategy"] = relationship(back_populates="optimizations")
    results: Mapped[list["OptimizationResult"]] = relationship(back_populates="optimization", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Optimization(id={self.id}, name='{self.name}', status='{self.status}')>"


class OptimizationResult(Base):
    """Individual optimization iteration result."""

    __tablename__ = "optimization_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    optimization_id: Mapped[int] = mapped_column(ForeignKey("optimizations.id", ondelete="CASCADE"), nullable=False)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    parameters: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    score: Mapped[float] = mapped_column(Float, nullable=False)
    metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON (sharpe, profit, drawdown, etc.)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    optimization: Mapped["Optimization"] = relationship(back_populates="results")

    def __repr__(self) -> str:
        return f"<OptimizationResult(id={self.id}, iteration={self.iteration}, score={self.score})>"


# ============================================================================
# Live and Paper Trading
# ============================================================================


class LiveTrade(Base):
    """Live trade model."""

    __tablename__ = "live_trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # long, short
    entry_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    take_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, closed, cancelled
    exit_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # No relationship to Strategy - avoid circular imports in live trading
    def __repr__(self) -> str:
        return f"<LiveTrade(id={self.id}, symbol='{self.symbol}', status='{self.status}')>"


class PaperTrade(Base):
    """Paper (simulated) trade model."""

    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    take_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    exit_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<PaperTrade(id={self.id}, symbol='{self.symbol}', status='{self.status}')>"


# ============================================================================
# Account and Performance
# ============================================================================


class AccountSnapshot(Base):
    """Account balance snapshot over time."""

    __tablename__ = "account_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)  # live, paper, backtest
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    equity: Mapped[float] = mapped_column(Float, nullable=False)
    margin_used: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    margin_available: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    open_positions: Mapped[int] = mapped_column(Integer, default=0)
    unrealized_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<AccountSnapshot(id={self.id}, type='{self.account_type}', equity={self.equity})>"


class FinanceMetric(Base):
    """Financial metrics and statistics."""

    __tablename__ = "finance_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # backtest, optimization, live, paper
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Index for efficient queries
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "metric_name", name="uq_finance_metric"),
    )

    def __repr__(self) -> str:
        return f"<FinanceMetric(type='{self.entity_type}', id={self.entity_id}, metric='{self.metric_name}')>"


# ============================================================================
# Walk-Forward and Edge Analysis
# ============================================================================


class EdgeResult(Base):
    """Walk-forward edge analysis results."""

    __tablename__ = "edge_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    in_sample_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    in_sample_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    out_sample_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    out_sample_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    in_sample_sharpe: Mapped[float] = mapped_column(Float, nullable=False)
    out_sample_sharpe: Mapped[float] = mapped_column(Float, nullable=False)
    edge_ratio: Mapped[float] = mapped_column(Float, nullable=False)  # out/in sample performance
    parameters: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<EdgeResult(id={self.id}, symbol='{self.symbol}', edge_ratio={self.edge_ratio})>"


# ============================================================================
# Notifications
# ============================================================================


class Notification(Base):
    """System notification model."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # info, warning, error, critical
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # Sent via external channel (email, telegram)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, level='{self.level}', title='{self.title}')>"
