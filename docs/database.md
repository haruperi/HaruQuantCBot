# Database Layer Documentation

## Overview

The HQT Database Layer provides a complete SQLAlchemy-based ORM system with connection pooling, repository pattern, migrations, and backup utilities for the trading system.

## Quick Start

```python
from hqt.foundation.database import DatabaseManager, Base, User, UserRepository

# 1. Create database manager
db = DatabaseManager("sqlite:///hqt.db")

# 2. Create all tables
db.create_all(Base)

# 3. Use repository pattern
with db.get_session() as session:
    user_repo = UserRepository(session)

    # Create user
    user = user_repo.create(
        username="trader1",
        email="trader@example.com",
        password_hash="hashed_password",
    )

    # Query user
    user = user_repo.get_by_username("trader1")
    print(f"User ID: {user.id}")
```

## Database Models

### User Model

Represents system users (traders, administrators).

```python
from hqt.foundation.database import User

user = User(
    username="trader1",
    email="trader@example.com",
    password_hash="hashed_password",
    full_name="John Trader",
    is_active=True,
    is_superuser=False,
)
```

**Fields:**
- `id`: Primary key (auto-increment)
- `username`: Unique username
- `email`: Unique email address
- `password_hash`: Hashed password (never store plaintext!)
- `full_name`: Optional full name
- `is_active`: Account status
- `is_superuser`: Admin privileges
- `created_at`: Account creation timestamp
- `updated_at`: Last update timestamp

**Relationships:**
- `strategies`: One-to-many with Strategy
- `backtests`: One-to-many with Backtest
- `settings`: One-to-one with UserSetting

### Strategy Model

Trading strategy definitions.

```python
from hqt.foundation.database import Strategy

strategy = Strategy(
    user_id=1,
    name="MA Crossover",
    description="Moving average crossover strategy",
    class_name="strategies.ma_crossover.MACrossover",
    parameters='{"fast_period": 10, "slow_period": 20}',
    is_active=True,
)
```

**Fields:**
- `id`: Primary key
- `user_id`: Foreign key to User
- `name`: Strategy name
- `description`: Strategy description
- `class_name`: Python class path
- `parameters`: JSON-encoded parameters
- `is_active`: Whether strategy is active
- `created_at`, `updated_at`: Timestamps

**Relationships:**
- `user`: Many-to-one with User
- `backtests`: One-to-many with Backtest

### Backtest Model

Backtest execution results.

```python
from hqt.foundation.database import Backtest

backtest = Backtest(
    user_id=1,
    strategy_id=1,
    name="EURUSD H1 Backtest",
    symbol="EURUSD",
    timeframe="H1",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    initial_capital=10000.0,
    final_capital=11500.0,
    total_return=15.0,
    sharpe_ratio=1.8,
    max_drawdown=-8.5,
    status="completed",
)
```

**Key Metrics:**
- Performance: `total_return`, `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`
- Risk: `max_drawdown`, `volatility`
- Trade Statistics: `total_trades`, `winning_trades`, `win_rate`, `profit_factor`
- Execution: `start_date`, `end_date`, `status`, `completed_at`

### BacktestTrade Model

Individual trades within a backtest.

```python
from hqt.foundation.database import BacktestTrade

trade = BacktestTrade(
    backtest_id=1,
    symbol="EURUSD",
    entry_time=datetime(2023, 6, 1, 10, 0),
    exit_time=datetime(2023, 6, 1, 15, 0),
    direction="long",
    entry_price=1.1000,
    exit_price=1.1050,
    volume=1.0,
    profit=500.0,
    profit_pct=5.0,
    exit_reason="tp",
)
```

### Additional Models

- **Optimization**: Parameter optimization runs
- **OptimizationResult**: Individual parameter combinations and results
- **LiveTrade**: Live trading executions
- **PaperTrade**: Paper trading executions
- **AccountSnapshot**: Account state snapshots
- **FinanceMetric**: Financial performance metrics
- **EdgeResult**: Edge analysis results
- **Notification**: User notifications
- **UserSetting**: User preferences

## Repository Pattern

Repositories provide CRUD operations and business logic for database models.

### Base Repository

All repositories inherit from `BaseRepository`:

```python
from hqt.foundation.database import BaseRepository

class MyRepository(BaseRepository[MyModel]):
    def __init__(self, session: Session):
        super().__init__(session, MyModel)
```

**Common Methods:**
- `create(**kwargs)`: Create new record
- `get_by_id(id)`: Get by primary key
- `get_all()`: Get all records
- `update(instance, **kwargs)`: Update record
- `delete(instance)`: Delete record
- `count()`: Count records

### User Repository

```python
from hqt.foundation.database import UserRepository

with db.get_session() as session:
    user_repo = UserRepository(session)

    # Create
    user = user_repo.create(
        username="trader1",
        email="trader@example.com",
        password_hash="hash",
    )

    # Query
    user = user_repo.get_by_username("trader1")
    user = user_repo.get_by_email("trader@example.com")

    # Update
    user_repo.update(user, full_name="John Trader")

    # Delete
    user_repo.delete(user)
```

### Strategy Repository

```python
from hqt.foundation.database import StrategyRepository

with db.get_session() as session:
    strategy_repo = StrategyRepository(session)

    # Get user's strategies
    strategies = strategy_repo.get_by_user(user_id=1)

    # Get active strategies
    strategies = strategy_repo.get_active()

    # Activate/deactivate
    strategy_repo.activate(strategy)
    strategy_repo.deactivate(strategy)
```

### Backtest Repository

```python
from hqt.foundation.database import BacktestRepository

with db.get_session() as session:
    backtest_repo = BacktestRepository(session)

    # Get user's backtests
    backtests = backtest_repo.get_by_user(user_id=1)

    # Get by strategy
    backtests = backtest_repo.get_by_strategy(strategy_id=1)

    # Get by symbol
    backtests = backtest_repo.get_by_symbol("EURUSD")

    # Get by status
    backtests = backtest_repo.get_by_status("completed")
```

### Trade Repository

```python
from hqt.foundation.database import TradeRepository

with db.get_session() as session:
    trade_repo = TradeRepository(session)

    # Get backtest trades
    trades = trade_repo.get_by_backtest(backtest_id=1)

    # Get winning/losing trades
    winners = trade_repo.get_winning_trades(backtest_id=1)
    losers = trade_repo.get_losing_trades(backtest_id=1)
```

## Database Migrations

HQT uses Alembic for database migrations.

### Initialize Migrations (Already Done)

```bash
alembic init alembic
```

### Create Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column to users table"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific version
alembic upgrade abc123

# Downgrade one version
alembic downgrade -1

# View current version
alembic current

# View migration history
alembic history
```

### Migration Scripts

Located in `alembic/versions/`. Each migration has:
- `upgrade()`: Forward migration
- `downgrade()`: Rollback migration

Example:
```python
def upgrade():
    op.add_column('users', sa.Column('api_key', sa.String(255)))

def downgrade():
    op.drop_column('users', 'api_key')
```

## Backup and Export

### Database Backup

```python
from hqt.foundation.database import DatabaseManager, DatabaseBackup

db = DatabaseManager("sqlite:///hqt.db")
backup = DatabaseBackup(db)

# Create backup
backup_path = backup.backup_database("backups/")
print(f"Backup created: {backup_path}")

# Restore from backup
backup.restore_database("backups/hqt_backup_20240101_120000.db", confirm=True)
```

### Export to JSON

```python
# Export single table
count = backup.export_table_to_json("users", "exports/users.json")

# Export with filters
count = backup.export_table_to_json(
    "strategies",
    "exports/user1_strategies.json",
    user_id=1,
)

# Export all tables
counts = backup.export_all_tables("exports/", format="json")
```

### Export to CSV

```python
# Export table to CSV
count = backup.export_table_to_csv("backtests", "exports/backtests.csv")

# Export all tables
counts = backup.export_all_tables("exports/", format="csv")
```

### Import from JSON

```python
# Import table (append)
count = backup.import_table_from_json("users", "imports/users.json")

# Import table (replace existing data)
count = backup.import_table_from_json(
    "users",
    "imports/users.json",
    replace=True,
)
```

### Database Statistics

```python
stats = backup.get_database_stats()

print(f"Total rows: {stats['total_rows']}")
print(f"Users: {stats['tables']['users']}")
print(f"Strategies: {stats['tables']['strategies']}")
```

## Connection Management

### Database URLs

```python
# SQLite (file)
db = DatabaseManager("sqlite:///hqt.db")

# SQLite (memory - for testing)
db = DatabaseManager("sqlite:///:memory:")

# PostgreSQL
db = DatabaseManager("postgresql://user:pass@localhost/hqt")

# MySQL
db = DatabaseManager("mysql://user:pass@localhost/hqt")
```

### Connection Pooling

```python
db = DatabaseManager(
    url="sqlite:///hqt.db",
    echo=False,              # SQL logging
    pool_size=5,             # Connection pool size
    max_overflow=10,         # Max overflow connections
    pool_timeout=30,         # Pool timeout (seconds)
    pool_recycle=3600,       # Recycle connections after 1 hour
)
```

### Session Management

```python
# Context manager (recommended)
with db.get_session() as session:
    user = session.query(User).first()
    # Session auto-commits and closes

# Manual management
session = db.get_session()
try:
    user = session.query(User).first()
    session.commit()
finally:
    session.close()
```

### Scoped Sessions

```python
# Thread-local sessions
session = db.get_scoped_session()
user = session.query(User).first()
db.remove_scoped_session()
```

## Best Practices

### 1. Always Use Repositories

```python
# Good - Repository pattern
with db.get_session() as session:
    user_repo = UserRepository(session)
    user = user_repo.get_by_username("trader1")

# Avoid - Direct queries
with db.get_session() as session:
    user = session.query(User).filter_by(username="trader1").first()
```

### 2. Use Context Managers

```python
# Good - Auto-commit and close
with db.get_session() as session:
    user_repo = UserRepository(session)
    user = user_repo.create(username="trader1")

# Avoid - Manual management
session = db.get_session()
user = User(username="trader1")
session.add(user)
session.commit()
session.close()
```

### 3. Handle Exceptions

```python
try:
    with db.get_session() as session:
        user_repo = UserRepository(session)
        user = user_repo.create(username="trader1")
except IntegrityError as e:
    print(f"User already exists: {e}")
except Exception as e:
    print(f"Database error: {e}")
```

### 4. Regular Backups

```python
from hqt.foundation.database.backup import create_backup

# Daily backup
backup_path = create_backup("sqlite:///hqt.db", "backups/")

# Keep last 7 days
import os
from pathlib import Path
backup_dir = Path("backups/")
backups = sorted(backup_dir.glob("*.db"), key=os.path.getmtime, reverse=True)
for old_backup in backups[7:]:
    old_backup.unlink()
```

### 5. Use Migrations for Schema Changes

```bash
# Don't modify database directly
# Don't create tables manually

# Instead, use migrations
alembic revision --autogenerate -m "Add column"
alembic upgrade head
```

## Troubleshooting

### Connection Pool Exhausted

```python
# Increase pool size
db = DatabaseManager(
    url="sqlite:///hqt.db",
    pool_size=20,
    max_overflow=40,
)
```

### Too Many Open Connections

```python
# Ensure sessions are closed
with db.get_session() as session:
    # Work with session
    pass  # Auto-closes

# Or dispose connections
db.dispose()
```

### Migration Conflicts

```bash
# View current state
alembic current

# View pending migrations
alembic history

# Force to specific version
alembic stamp head
```

### Lock Errors (SQLite)

```python
# Use StaticPool for concurrent access
from sqlalchemy.pool import StaticPool

db = DatabaseManager(
    url="sqlite:///hqt.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

## API Reference

See module docstrings for complete API documentation:
- `hqt.foundation.database.connection`
- `hqt.foundation.database.models`
- `hqt.foundation.database.repositories`
- `hqt.foundation.database.backup`
