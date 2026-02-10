"""
Unit tests for database layer.

Tests DatabaseManager, ORM models, and repositories using in-memory SQLite.
"""

import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from hqt.foundation.database import (
    AccountSnapshot,
    Backtest,
    BacktestRepository,
    BacktestTrade,
    Base,
    DatabaseManager,
    Notification,
    NotificationRepository,
    Optimization,
    OptimizationRepository,
    OptimizationResult,
    OptimizationResultRepository,
    Strategy,
    StrategyRepository,
    TradeRepository,
    User,
    UserRepository,
    UserSetting,
)
from hqt.foundation.exceptions import ConfigError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_manager():
    """Create in-memory SQLite database manager."""
    db = DatabaseManager("sqlite:///:memory:", echo=False)
    db.create_all(Base)
    yield db
    db.dispose()


@pytest.fixture
def session(db_manager):
    """Create database session."""
    # Create session directly without context manager for fixture
    # Tests will manually commit/rollback as needed
    session = db_manager._session_factory()
    try:
        yield session
    finally:
        session.rollback()  # Rollback any uncommitted changes
        session.close()


@pytest.fixture
def user_repo(session):
    """Create user repository."""
    return UserRepository(session)


@pytest.fixture
def strategy_repo(session):
    """Create strategy repository."""
    return StrategyRepository(session)


@pytest.fixture
def backtest_repo(session):
    """Create backtest repository."""
    return BacktestRepository(session)


@pytest.fixture
def trade_repo(session):
    """Create trade repository."""
    return TradeRepository(session)


@pytest.fixture
def optimization_repo(session):
    """Create optimization repository."""
    return OptimizationRepository(session)


@pytest.fixture
def optimization_result_repo(session):
    """Create optimization result repository."""
    return OptimizationResultRepository(session)


@pytest.fixture
def notification_repo(session):
    """Create notification repository."""
    return NotificationRepository(session)


@pytest.fixture
def sample_user(user_repo):
    """Create sample user."""
    user = user_repo.create(
        username="trader1",
        email="trader1@example.com",
        password_hash="hashed_password",
        is_active=True,
    )
    return user


@pytest.fixture
def sample_strategy(strategy_repo, sample_user):
    """Create sample strategy."""
    strategy = strategy_repo.create(
        user_id=sample_user.id,
        name="MA Crossover",
        description="Simple moving average crossover strategy",
        class_name="strategies.MACrossoverStrategy",
        parameters=json.dumps({"fast_period": 10, "slow_period": 20}),
        is_active=True,
    )
    return strategy


# ============================================================================
# Test DatabaseManager
# ============================================================================


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    def test_sqlite_memory_connection(self):
        """Test SQLite in-memory connection."""
        db = DatabaseManager("sqlite:///:memory:")
        assert db.db_type == "sqlite"
        assert db.engine is not None
        db.dispose()

    def test_sqlite_file_connection(self, tmp_path):
        """Test SQLite file-based connection."""
        db_file = tmp_path / "test.db"
        db = DatabaseManager(f"sqlite:///{db_file}")
        assert db.db_type == "sqlite"
        assert db.engine is not None
        # Create tables to force file creation
        db.create_all(Base)
        db.dispose()
        assert db_file.exists()

    def test_invalid_database_url(self):
        """Test invalid database URL raises ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            DatabaseManager("invalid://url")
        assert "DB-002" in str(exc_info.value)

    def test_get_session_context_manager(self, db_manager):
        """Test session context manager."""
        with db_manager.get_session() as session:
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_session_commit_on_success(self, db_manager):
        """Test session commits on successful context exit."""
        db_manager.create_all(Base)

        with db_manager.get_session() as session:
            user = User(username="test", email="test@example.com", password_hash="hash")
            session.add(user)

        # Verify user was committed
        with db_manager.get_session() as session:
            user = session.execute(text("SELECT * FROM users WHERE username='test'")).first()
            assert user is not None

    def test_session_rollback_on_error(self, db_manager):
        """Test session rolls back on exception."""
        db_manager.create_all(Base)

        try:
            with db_manager.get_session() as session:
                user = User(username="test", email="test@example.com", password_hash="hash")
                session.add(user)
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify user was NOT committed
        with db_manager.get_session() as session:
            count = session.execute(text("SELECT COUNT(*) FROM users")).scalar()
            assert count == 0

    def test_create_all_tables(self, db_manager):
        """Test create_all creates all tables."""
        db_manager.create_all(Base)

        with db_manager.get_session() as session:
            # Check that tables exist
            result = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            tables = [row[0] for row in result]

            expected_tables = [
                "account_snapshots",
                "backtests",
                "backtest_trades",
                "edge_results",
                "finance_metrics",
                "live_trades",
                "notifications",
                "optimizations",
                "optimization_results",
                "paper_trades",
                "strategies",
                "users",
                "user_settings",
            ]

            for table in expected_tables:
                assert table in tables

    def test_context_manager(self):
        """Test DatabaseManager as context manager."""
        with DatabaseManager("sqlite:///:memory:") as db:
            assert db.engine is not None
        # Engine should be disposed after context exit


# ============================================================================
# Test User & UserRepository
# ============================================================================


class TestUserRepository:
    """Test UserRepository functionality."""

    def test_create_user(self, user_repo):
        """Test creating a user."""
        user = user_repo.create(
            username="trader1",
            email="trader1@example.com",
            password_hash="hashed_password",
            is_active=True,
        )

        assert user.id is not None
        assert user.username == "trader1"
        assert user.email == "trader1@example.com"
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)

    def test_get_by_id(self, user_repo, sample_user):
        """Test get user by ID."""
        user = user_repo.get_by_id(sample_user.id)
        assert user is not None
        assert user.id == sample_user.id
        assert user.username == sample_user.username

    def test_get_by_username(self, user_repo, sample_user):
        """Test get user by username."""
        user = user_repo.get_by_username("trader1")
        assert user is not None
        assert user.id == sample_user.id

    def test_get_by_email(self, user_repo, sample_user):
        """Test get user by email."""
        user = user_repo.get_by_email("trader1@example.com")
        assert user is not None
        assert user.id == sample_user.id

    def test_get_active_users(self, user_repo, sample_user):
        """Test get active users."""
        # Create inactive user
        user_repo.create(
            username="inactive",
            email="inactive@example.com",
            password_hash="hash",
            is_active=False,
        )

        active_users = user_repo.get_active_users()
        assert len(active_users) == 1
        assert active_users[0].username == "trader1"

    def test_update_user(self, user_repo, sample_user):
        """Test updating a user."""
        sample_user.email = "newemail@example.com"
        updated_user = user_repo.update(sample_user)

        assert updated_user.email == "newemail@example.com"

        # Verify in database
        user = user_repo.get_by_id(sample_user.id)
        assert user.email == "newemail@example.com"

    def test_delete_user(self, user_repo, sample_user):
        """Test deleting a user."""
        user_id = sample_user.id
        user_repo.delete(sample_user)

        user = user_repo.get_by_id(user_id)
        assert user is None

    def test_delete_by_id(self, user_repo, sample_user):
        """Test deleting user by ID."""
        user_id = sample_user.id
        result = user_repo.delete_by_id(user_id)
        assert result is True

        user = user_repo.get_by_id(user_id)
        assert user is None

    def test_count_users(self, user_repo, sample_user):
        """Test counting users."""
        user_repo.create(username="user2", email="user2@example.com", password_hash="hash")

        count = user_repo.count()
        assert count == 2

    def test_get_all_users(self, user_repo, sample_user):
        """Test get all users."""
        user_repo.create(username="user2", email="user2@example.com", password_hash="hash")

        users = user_repo.get_all()
        assert len(users) == 2

    def test_get_all_with_pagination(self, user_repo, sample_user):
        """Test get all with pagination."""
        for i in range(2, 6):
            user_repo.create(username=f"user{i}", email=f"user{i}@example.com", password_hash="hash")

        # Get first page (2 users)
        users = user_repo.get_all(limit=2, offset=0)
        assert len(users) == 2

        # Get second page
        users = user_repo.get_all(limit=2, offset=2)
        assert len(users) == 2


# ============================================================================
# Test Strategy & StrategyRepository
# ============================================================================


class TestStrategyRepository:
    """Test StrategyRepository functionality."""

    def test_create_strategy(self, strategy_repo, sample_user):
        """Test creating a strategy."""
        strategy = strategy_repo.create(
            user_id=sample_user.id,
            name="Test Strategy",
            description="Test description",
            class_name="strategies.TestStrategy",
            parameters=json.dumps({"param1": "value1"}),
            is_active=True,
        )

        assert strategy.id is not None
        assert strategy.name == "Test Strategy"
        assert strategy.user_id == sample_user.id
        assert isinstance(strategy.created_at, datetime)

    def test_get_by_user(self, strategy_repo, sample_user, sample_strategy):
        """Test get strategies by user."""
        # Create another strategy
        strategy_repo.create(
            user_id=sample_user.id,
            name="Strategy 2",
            class_name="strategies.Strategy2",
            parameters=json.dumps({}),
        )

        strategies = strategy_repo.get_by_user(sample_user.id)
        assert len(strategies) == 2

    def test_get_active_by_user(self, strategy_repo, sample_user, sample_strategy):
        """Test get active strategies by user."""
        # Create inactive strategy
        strategy_repo.create(
            user_id=sample_user.id,
            name="Inactive Strategy",
            class_name="strategies.InactiveStrategy",
            parameters=json.dumps({}),
            is_active=False,
        )

        strategies = strategy_repo.get_active_by_user(sample_user.id)
        assert len(strategies) == 1
        assert strategies[0].name == "MA Crossover"

    def test_strategy_user_relationship(self, session, sample_user, sample_strategy):
        """Test strategy-user relationship."""
        # Access user from strategy
        assert sample_strategy.user.username == "trader1"

        # Access strategies from user
        assert len(sample_user.strategies) == 1
        assert sample_user.strategies[0].name == "MA Crossover"


# ============================================================================
# Test Backtest & BacktestRepository
# ============================================================================


class TestBacktestRepository:
    """Test BacktestRepository functionality."""

    def test_create_backtest(self, backtest_repo, sample_user, sample_strategy):
        """Test creating a backtest."""
        backtest = backtest_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Test Backtest",
            symbol="EURUSD",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=10000.0,
            final_capital=11550.0,
            total_return=15.5,
            sharpe_ratio=1.8,
            max_drawdown=-8.2,
            win_rate=65.0,
            total_trades=100,
            status="completed",
        )

        assert backtest.id is not None
        assert backtest.name == "Test Backtest"
        assert backtest.total_return == 15.5
        assert backtest.status == "completed"

    def test_get_by_user(self, backtest_repo, sample_user, sample_strategy):
        """Test get backtests by user."""
        backtest_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Test Backtest",
            symbol="EURUSD",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=10000.0,
            final_capital=11000.0,
            total_return=10.0,
            status="completed",
        )

        backtests = backtest_repo.get_by_user(sample_user.id)
        assert len(backtests) == 1

    def test_get_by_strategy(self, backtest_repo, sample_user, sample_strategy):
        """Test get backtests by strategy."""
        backtest_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Test Backtest",
            symbol="EURUSD",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=10000.0,
            final_capital=11000.0,
            total_return=10.0,
            status="completed",
        )

        backtests = backtest_repo.get_by_strategy(sample_strategy.id)
        assert len(backtests) == 1

    def test_get_completed(self, backtest_repo, sample_user, sample_strategy):
        """Test get completed backtests."""
        # Create completed backtest
        backtest_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Test Backtest",
            symbol="EURUSD",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=10000.0,
            final_capital=11000.0,
            total_return=10.0,
            status="completed",
            completed_at=datetime.utcnow(),
        )

        # Create running backtest
        backtest_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Test Backtest",
            symbol="GBPUSD",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=10000.0,
            final_capital=11000.0,
            total_return=0.0,
            status="running",
        )

        completed = backtest_repo.get_completed()
        assert len(completed) == 1
        assert completed[0].status == "completed"

    def test_update_status(self, backtest_repo, sample_user, sample_strategy):
        """Test updating backtest status."""
        backtest = backtest_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Test Backtest",
            symbol="EURUSD",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=10000.0,
            final_capital=11000.0,
            total_return=0.0,
            status="running",
        )

        updated = backtest_repo.update_status(backtest.id, "completed")
        assert updated.status == "completed"
        assert updated.completed_at is not None


# ============================================================================
# Test BacktestTrade & TradeRepository
# ============================================================================


class TestTradeRepository:
    """Test TradeRepository functionality."""

    @pytest.fixture
    def sample_backtest(self, backtest_repo, sample_user, sample_strategy):
        """Create sample backtest."""
        return backtest_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Test Backtest",
            symbol="EURUSD",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=10000.0,
            final_capital=11000.0,
            total_return=10.0,
            status="completed",
        )

    def test_create_trade(self, trade_repo, sample_backtest):
        """Test creating a trade."""
        trade = trade_repo.create(
            backtest_id=sample_backtest.id,
            symbol="EURUSD",
            entry_time=datetime(2023, 1, 10, 10, 0),
            exit_time=datetime(2023, 1, 10, 15, 0),
            direction="long",
            entry_price=1.1000,
            exit_price=1.1050,
            volume=1.0,
            profit=50.0,
            profit_pct=0.5,
        )

        assert trade.id is not None
        assert trade.backtest_id == sample_backtest.id
        assert trade.direction == "long"
        assert trade.profit == 50.0

    def test_get_by_backtest(self, trade_repo, sample_backtest):
        """Test get trades by backtest."""
        trade_repo.create(
            backtest_id=sample_backtest.id,
            symbol="EURUSD",
            entry_time=datetime(2023, 1, 10),
            exit_time=datetime(2023, 1, 11),
            direction="long",
            entry_price=1.1000,
            exit_price=1.1050,
            volume=1.0,
            profit=50.0,
            profit_pct=0.5,
        )

        trade_repo.create(
            backtest_id=sample_backtest.id,
            symbol="EURUSD",
            entry_time=datetime(2023, 1, 12),
            exit_time=datetime(2023, 1, 13),
            direction="short",
            entry_price=1.1000,
            exit_price=1.0950,
            volume=1.0,
            profit=50.0,
            profit_pct=0.5,
        )

        trades = trade_repo.get_by_backtest(sample_backtest.id)
        assert len(trades) == 2

    def test_get_winning_trades(self, trade_repo, sample_backtest):
        """Test get winning trades."""
        trade_repo.create(
            backtest_id=sample_backtest.id,
            symbol="EURUSD",
            entry_time=datetime(2023, 1, 10),
            exit_time=datetime(2023, 1, 11),
            direction="long",
            entry_price=1.1000,
            exit_price=1.1050,
            volume=1.0,
            profit=50.0,
            profit_pct=0.5,
        )

        trade_repo.create(
            backtest_id=sample_backtest.id,
            symbol="EURUSD",
            entry_time=datetime(2023, 1, 12),
            exit_time=datetime(2023, 1, 13),
            direction="short",
            entry_price=1.1000,
            exit_price=1.1050,
            volume=1.0,
            profit=-50.0,
            profit_pct=0.5,
        )

        winning_trades = trade_repo.get_winning_trades(sample_backtest.id)
        assert len(winning_trades) == 1
        assert winning_trades[0].profit > 0

    def test_get_losing_trades(self, trade_repo, sample_backtest):
        """Test get losing trades."""
        trade_repo.create(
            backtest_id=sample_backtest.id,
            symbol="EURUSD",
            entry_time=datetime(2023, 1, 10),
            exit_time=datetime(2023, 1, 11),
            direction="long",
            entry_price=1.1000,
            exit_price=1.1050,
            volume=1.0,
            profit=50.0,
            profit_pct=0.5,
        )

        trade_repo.create(
            backtest_id=sample_backtest.id,
            symbol="EURUSD",
            entry_time=datetime(2023, 1, 12),
            exit_time=datetime(2023, 1, 13),
            direction="short",
            entry_price=1.1000,
            exit_price=1.1050,
            volume=1.0,
            profit=-50.0,
            profit_pct=0.5,
        )

        losing_trades = trade_repo.get_losing_trades(sample_backtest.id)
        assert len(losing_trades) == 1
        assert losing_trades[0].profit < 0


# ============================================================================
# Test Optimization & OptimizationRepository
# ============================================================================


class TestOptimizationRepository:
    """Test OptimizationRepository functionality."""

    def test_create_optimization(self, optimization_repo, sample_user, sample_strategy):
        """Test creating an optimization."""
        opt = optimization_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Test Optimization",
            method="grid",
            parameter_space=json.dumps({"fast_period": [5, 15], "slow_period": [20, 30]}),
            objective="sharpe_ratio",
            total_iterations=100,
            completed_iterations=0,
            status="pending",
        )

        assert opt.id is not None
        assert opt.name == "Test Optimization"
        assert opt.status == "pending"

    def test_get_by_user(self, optimization_repo, sample_user, sample_strategy):
        """Test get optimizations by user."""
        optimization_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Optimization 1",
            method="grid",
            parameter_space=json.dumps({}),
            objective="sharpe_ratio",
            total_iterations=100,
            completed_iterations=0,
            status="pending",
        )

        opts = optimization_repo.get_by_user(sample_user.id)
        assert len(opts) == 1

    def test_get_by_strategy(self, optimization_repo, sample_user, sample_strategy):
        """Test get optimizations by strategy."""
        optimization_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Optimization 2",
            method="grid",
            parameter_space=json.dumps({}),
            objective="sharpe_ratio",
            total_iterations=100,
            completed_iterations=0,
            status="pending",
        )

        opts = optimization_repo.get_by_strategy(sample_strategy.id)
        assert len(opts) == 1

    def test_get_running(self, optimization_repo, sample_user, sample_strategy):
        """Test get running optimizations."""
        optimization_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Running Optimization",
            method="grid",
            parameter_space=json.dumps({}),
            objective="sharpe_ratio",
            total_iterations=100,
            completed_iterations=0,
            status="running",
        )

        optimization_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Completed Optimization",
            method="grid",
            parameter_space=json.dumps({}),
            objective="sharpe_ratio",
            total_iterations=100,
            completed_iterations=100,
            status="completed",
        )

        running = optimization_repo.get_running()
        assert len(running) == 1
        assert running[0].status == "running"

    def test_update_progress(self, optimization_repo, sample_user, sample_strategy):
        """Test updating optimization progress."""
        opt = optimization_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Progress Test",
            method="grid",
            parameter_space=json.dumps({}),
            objective="sharpe_ratio",
            total_iterations=100,
            completed_iterations=0,
            status="running",
        )

        updated = optimization_repo.update_progress(
            opt.id,
            completed_iterations=50,
            best_score=1.5,
            best_parameters=json.dumps({"fast_period": 10, "slow_period": 25}),
        )

        assert updated.completed_iterations == 50
        assert updated.best_score == 1.5
        assert updated.best_parameters is not None


# ============================================================================
# Test OptimizationResult & OptimizationResultRepository
# ============================================================================


class TestOptimizationResultRepository:
    """Test OptimizationResultRepository functionality."""

    @pytest.fixture
    def sample_optimization(self, optimization_repo, sample_user, sample_strategy):
        """Create sample optimization."""
        return optimization_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Sample Optimization",
            method="grid",
            parameter_space=json.dumps({}),
            objective="sharpe_ratio",
            total_iterations=100,
            completed_iterations=0,
            status="running",
        )

    def test_create_result(self, optimization_result_repo, sample_optimization):
        """Test creating optimization result."""
        result = optimization_result_repo.create(
            optimization_id=sample_optimization.id,
            iteration=1,
            parameters=json.dumps({"fast_period": 10, "slow_period": 20}),
            score=1.5,
            metrics=json.dumps({"total_return": 15.0, "sharpe_ratio": 1.5, "max_drawdown": -8.0}),
        )

        assert result.id is not None
        assert result.iteration == 1
        assert result.score == 1.5

    def test_get_by_optimization(self, optimization_result_repo, sample_optimization):
        """Test get results by optimization."""
        for i in range(1, 6):
            optimization_result_repo.create(
                optimization_id=sample_optimization.id,
                iteration=i,
                parameters=json.dumps({"fast_period": 10 + i}),
                score=1.0 + i * 0.1,
            )

        results = optimization_result_repo.get_by_optimization(sample_optimization.id)
        assert len(results) == 5

    def test_get_best_results(self, optimization_result_repo, sample_optimization):
        """Test get best results."""
        scores = [1.5, 1.2, 1.8, 1.1, 1.6]
        for i, score in enumerate(scores, 1):
            optimization_result_repo.create(
                optimization_id=sample_optimization.id,
                iteration=i,
                parameters=json.dumps({"fast_period": 10 + i}),
                score=score,
            )

        best_results = optimization_result_repo.get_best_results(sample_optimization.id, limit=3)
        assert len(best_results) == 3
        assert best_results[0].score == 1.8  # Highest score first
        assert best_results[1].score == 1.6
        assert best_results[2].score == 1.5


# ============================================================================
# Test Notification & NotificationRepository
# ============================================================================


class TestNotificationRepository:
    """Test NotificationRepository functionality."""

    def test_create_notification(self, notification_repo, sample_user):
        """Test creating a notification."""
        notif = notification_repo.create(
            user_id=sample_user.id,
            level="backtest_completed",
            title="Backtest Completed",
            message="Your backtest has completed successfully",
        )

        assert notif.id is not None
        assert notif.level == "backtest_completed"
        assert notif.read_at is None

    def test_get_by_user(self, notification_repo, sample_user):
        """Test get notifications by user."""
        notification_repo.create(
            user_id=sample_user.id,
            level="info",
            title="Title 1",
            message="Message 1",
        )
        notification_repo.create(
            user_id=sample_user.id,
            level="info",
            title="Title 2",
            message="Message 2",
        )

        notifs = notification_repo.get_by_user(sample_user.id)
        assert len(notifs) == 2

    def test_get_unread_only(self, notification_repo, sample_user):
        """Test get unread notifications only."""
        notif1 = notification_repo.create(
            user_id=sample_user.id,
            level="info",
            title="Unread",
            message="Message",
        )
        notif2 = notification_repo.create(
            user_id=sample_user.id,
            level="info",
            title="Read",
            message="Message",
        )

        # Mark one as read
        notification_repo.mark_as_read(notif2.id)

        unread = notification_repo.get_by_user(sample_user.id, unread_only=True)
        assert len(unread) == 1
        assert unread[0].id == notif1.id

    def test_mark_as_read(self, notification_repo, sample_user):
        """Test marking notification as read."""
        notif = notification_repo.create(
            user_id=sample_user.id,
            level="info",
            title="Title",
            message="Message",
        )

        assert notif.read_at is None

        updated = notification_repo.mark_as_read(notif.id)
        assert updated.read_at is not None

    def test_mark_all_as_read(self, notification_repo, sample_user):
        """Test marking all notifications as read."""
        for i in range(3):
            notification_repo.create(
                user_id=sample_user.id,
                level="info",
                title=f"Title {i}",
                message="Message",
            )

        count = notification_repo.mark_all_as_read(sample_user.id)
        assert count == 3

        unread = notification_repo.get_by_user(sample_user.id, unread_only=True)
        assert len(unread) == 0


# ============================================================================
# Test Model Relationships and Cascades
# ============================================================================


class TestModelRelationships:
    """Test model relationships and cascade deletes."""

    def test_user_cascade_delete(self, session, user_repo, strategy_repo, sample_user):
        """Test deleting user cascades to strategies."""
        strategy_repo.create(
            user_id=sample_user.id,
            name="Strategy 1",
            class_name="strategies.Strategy1",
            parameters=json.dumps({}),
        )

        user_id = sample_user.id
        user_repo.delete(sample_user)
        session.flush()

        # Verify strategies were deleted
        strategies = strategy_repo.get_by_user(user_id)
        assert len(strategies) == 0

    def test_strategy_cascade_delete(self, session, strategy_repo, backtest_repo, sample_user, sample_strategy):
        """Test deleting strategy cascades to backtests."""
        backtest_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Test Backtest",
            symbol="EURUSD",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=10000.0,
            final_capital=11000.0,
            total_return=10.0,
            status="completed",
        )

        strategy_id = sample_strategy.id
        strategy_repo.delete(sample_strategy)
        session.flush()

        # Verify backtests were deleted
        backtests = backtest_repo.get_by_strategy(strategy_id)
        assert len(backtests) == 0

    def test_backtest_cascade_delete(self, session, backtest_repo, trade_repo, sample_user, sample_strategy):
        """Test deleting backtest cascades to trades."""
        backtest = backtest_repo.create(
            user_id=sample_user.id,
            strategy_id=sample_strategy.id,
            name="Test Backtest",
            symbol="EURUSD",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=10000.0,
            final_capital=11000.0,
            total_return=10.0,
            status="completed",
        )

        trade_repo.create(
            backtest_id=backtest.id,
            symbol="EURUSD",
            entry_time=datetime(2023, 1, 10),
            exit_time=datetime(2023, 1, 11),
            direction="long",
            entry_price=1.1000,
            exit_price=1.1050,
            volume=1.0,
            profit=50.0,
            profit_pct=0.5,
        )

        backtest_id = backtest.id
        backtest_repo.delete(backtest)
        session.flush()

        # Verify trades were deleted
        trades = trade_repo.get_by_backtest(backtest_id)
        assert len(trades) == 0
