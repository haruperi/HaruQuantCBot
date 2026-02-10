"""
Pydantic configuration models for the HQT trading system.

This module defines type-safe configuration models for all system components
with validation, defaults, and documentation.
"""

from enum import Enum
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ============================================================================
# Engine Configuration
# ============================================================================


class EngineConfig(BaseModel):
    """
    Configuration for the C++ core engine.

    Controls event processing, memory management, and performance settings.
    """

    tick_buffer_size: Annotated[int, Field(gt=0, le=1000000)] = 100000
    """Maximum number of ticks to buffer in memory"""

    event_queue_size: Annotated[int, Field(gt=0, le=100000)] = 10000
    """Size of the event processing queue"""

    worker_threads: Annotated[int, Field(ge=1, le=32)] = 4
    """Number of worker threads for parallel processing"""

    enable_wal: bool = True
    """Enable Write-Ahead Logging for crash recovery"""

    wal_sync_interval_ms: Annotated[int, Field(ge=0, le=10000)] = 1000
    """WAL fsync interval in milliseconds (0 = immediate)"""

    model_config = ConfigDict(frozen=False)  # Will be frozen after validation


# ============================================================================
# Data Configuration
# ============================================================================


class DataProviderType(str, Enum):
    """Supported data provider types."""

    MT5 = "mt5"
    DUKASCOPY = "dukascopy"
    CSV = "csv"
    CUSTOM = "custom"


class DataConfig(BaseModel):
    """
    Configuration for data management and storage.

    Controls data providers, storage format, and validation settings.
    """

    storage_path: Path = Field(default=Path("data"))
    """Base directory for data storage"""

    storage_format: Annotated[str, Field(pattern="^(parquet|hdf5)$")] = "parquet"
    """Storage format: 'parquet' or 'hdf5'"""

    compression: Annotated[str, Field(pattern="^(snappy|gzip|lz4|zstd|none)$")] = "snappy"
    """Compression algorithm for stored data"""

    default_provider: DataProviderType = DataProviderType.MT5
    """Default data provider to use"""

    validation_enabled: bool = True
    """Enable data quality validation"""

    validation_strict: bool = False
    """Strict validation mode (reject invalid data)"""

    max_gap_seconds: Annotated[int, Field(ge=0)] = 300
    """Maximum allowed gap in data (seconds)"""

    max_spread_multiplier: Annotated[float, Field(gt=0)] = 3.0
    """Maximum spread as multiplier of median spread"""

    model_config = ConfigDict(frozen=False)


# ============================================================================
# Broker Configuration
# ============================================================================


class BrokerType(str, Enum):
    """Supported broker types."""

    MT5 = "mt5"
    PAPER = "paper"
    CUSTOM = "custom"


class BrokerConfig(BaseModel):
    """
    Configuration for broker connectivity.

    Controls broker gateway settings, credentials, and connection parameters.
    """

    broker_type: BrokerType = BrokerType.PAPER
    """Broker type: mt5, paper, or custom"""

    mt5_terminal_path: Path | None = None
    """Path to MT5 terminal executable (Windows only)"""

    mt5_login: int | None = None
    """MT5 account login number"""

    mt5_server: str | None = None
    """MT5 server name"""

    zmq_tick_port: Annotated[int, Field(ge=1024, le=65535)] = 5555
    """ZeroMQ port for tick data stream"""

    zmq_command_port: Annotated[int, Field(ge=1024, le=65535)] = 5556
    """ZeroMQ port for trading commands"""

    connection_timeout_seconds: Annotated[int, Field(gt=0)] = 30
    """Connection timeout in seconds"""

    reconnect_attempts: Annotated[int, Field(ge=0)] = 5
    """Maximum reconnection attempts"""

    reconnect_backoff_seconds: Annotated[int, Field(ge=1)] = 5
    """Backoff time between reconnection attempts"""

    model_config = ConfigDict(frozen=False)


# ============================================================================
# Risk Management Configuration
# ============================================================================


class PositionSizingMethod(str, Enum):
    """Position sizing methods."""

    FIXED_LOT = "fixed_lot"
    RISK_PERCENT = "risk_percent"
    KELLY = "kelly"
    ATR_BASED = "atr_based"
    FIXED_CAPITAL = "fixed_capital"


class RiskConfig(BaseModel):
    """
    Configuration for risk management.

    Controls position sizing, risk limits, and portfolio constraints.
    """

    position_sizing_method: PositionSizingMethod = PositionSizingMethod.RISK_PERCENT
    """Position sizing method"""

    risk_per_trade_percent: Annotated[float, Field(gt=0, le=100)] = 1.0
    """Risk per trade as percentage of equity"""

    max_positions: Annotated[int, Field(ge=1)] = 10
    """Maximum number of concurrent positions"""

    max_daily_trades: Annotated[int, Field(ge=1)] = 20
    """Maximum trades per day"""

    max_daily_loss_percent: Annotated[float, Field(gt=0, le=100)] = 5.0
    """Maximum daily loss as percentage of equity"""

    max_drawdown_percent: Annotated[float, Field(gt=0, le=100)] = 20.0
    """Maximum allowed drawdown percentage"""

    max_correlation: Annotated[float, Field(ge=0, le=1)] = 0.7
    """Maximum correlation between positions"""

    stop_out_level_percent: Annotated[float, Field(gt=0, le=100)] = 20.0
    """Stop-out level as margin level percentage"""

    enable_circuit_breaker: bool = True
    """Enable circuit breaker on excessive losses"""

    circuit_breaker_threshold_percent: Annotated[float, Field(gt=0)] = 3.0
    """Circuit breaker threshold (% loss in 5min)"""

    model_config = ConfigDict(frozen=False)


# ============================================================================
# Notification Configuration
# ============================================================================


class NotificationChannel(str, Enum):
    """Notification channels."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationConfig(BaseModel):
    """
    Configuration for notifications.

    Controls notification channels, triggers, and rate limiting.
    """

    enabled: bool = False
    """Enable notification system"""

    channels: list[NotificationChannel] = []
    """Active notification channels"""

    telegram_bot_token: str | None = None
    """Telegram bot API token (stored as secret)"""

    telegram_chat_id: str | None = None
    """Telegram chat ID for notifications"""

    email_smtp_host: str | None = None
    """SMTP server hostname"""

    email_smtp_port: Annotated[int, Field(ge=1, le=65535)] = 587
    """SMTP server port"""

    email_from: str | None = None
    """From email address"""

    email_to: list[str] = []
    """Recipient email addresses"""

    notify_on_trade: bool = True
    """Send notification on trade execution"""

    notify_on_error: bool = True
    """Send notification on errors"""

    notify_on_disconnect: bool = True
    """Send notification on broker disconnect"""

    rate_limit_messages_per_hour: Annotated[int, Field(ge=1)] = 60
    """Maximum messages per hour per channel"""

    model_config = ConfigDict(frozen=False)


# ============================================================================
# Logging Configuration
# ============================================================================


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingConfig(BaseModel):
    """
    Configuration for logging system.

    Controls log levels, output destinations, and format.
    """

    level: LogLevel = LogLevel.INFO
    """Global log level"""

    console_enabled: bool = True
    """Enable console output"""

    console_level: LogLevel = LogLevel.INFO
    """Console log level"""

    file_enabled: bool = True
    """Enable file output"""

    file_level: LogLevel = LogLevel.DEBUG
    """File log level"""

    file_path: Path = Field(default=Path("logs/hqt.log"))
    """Log file path"""

    file_max_bytes: Annotated[int, Field(gt=0)] = 10485760  # 10MB
    """Maximum log file size before rotation"""

    file_backup_count: Annotated[int, Field(ge=0)] = 5
    """Number of backup files to keep"""

    json_enabled: bool = True
    """Enable JSON structured logging"""

    json_path: Path = Field(default=Path("logs/hqt.json"))
    """JSON log file path"""

    enable_redaction: bool = True
    """Enable sensitive data redaction"""

    model_config = ConfigDict(frozen=False)


# ============================================================================
# UI Configuration
# ============================================================================


class UIConfig(BaseModel):
    """
    Configuration for desktop UI.

    Controls UI appearance, behavior, and performance settings.
    """

    theme: Annotated[str, Field(pattern="^(light|dark|auto)$")] = "dark"
    """UI theme: light, dark, or auto"""

    window_width: Annotated[int, Field(ge=800)] = 1920
    """Default window width in pixels"""

    window_height: Annotated[int, Field(ge=600)] = 1080
    """Default window height in pixels"""

    chart_update_interval_ms: Annotated[int, Field(ge=100)] = 1000
    """Chart refresh interval in milliseconds"""

    max_chart_points: Annotated[int, Field(ge=1000)] = 10000
    """Maximum points to display on chart"""

    enable_animations: bool = True
    """Enable UI animations"""

    font_size: Annotated[int, Field(ge=8, le=24)] = 10
    """UI font size in points"""

    model_config = ConfigDict(frozen=False)


# ============================================================================
# Database Configuration
# ============================================================================


class DatabaseConfig(BaseModel):
    """
    Configuration for database connectivity.

    Controls database connection, pooling, and storage settings.
    """

    url: str = "sqlite:///hqt.db"
    """Database connection URL"""

    echo: bool = False
    """Echo SQL statements (debug mode)"""

    pool_size: Annotated[int, Field(ge=1)] = 5
    """Connection pool size"""

    max_overflow: Annotated[int, Field(ge=0)] = 10
    """Maximum overflow connections"""

    pool_timeout: Annotated[int, Field(ge=1)] = 30
    """Pool timeout in seconds"""

    pool_recycle: Annotated[int, Field(ge=-1)] = 3600
    """Connection recycle time in seconds (-1 = no recycle)"""

    enable_migrations: bool = True
    """Auto-run database migrations on startup"""

    backup_enabled: bool = True
    """Enable automatic database backups"""

    backup_interval_hours: Annotated[int, Field(ge=1)] = 24
    """Backup interval in hours"""

    model_config = ConfigDict(frozen=False)


# ============================================================================
# Optimization Configuration
# ============================================================================


class OptimizationMethod(str, Enum):
    """Optimization methods."""

    GRID = "grid"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"


class OptimizationConfig(BaseModel):
    """
    Configuration for parameter optimization.

    Controls optimization method, parallelization, and resource limits.
    """

    method: OptimizationMethod = OptimizationMethod.GRID
    """Optimization method: grid, bayesian, or genetic"""

    max_parallel_workers: Annotated[int, Field(ge=1)] = 4
    """Maximum parallel optimization workers"""

    use_ray: bool = True
    """Use Ray for distributed optimization"""

    objective_function: Annotated[str, Field(pattern="^(sharpe|profit_factor|total_return|calmar|custom)$")] = "sharpe"
    """Objective function to maximize"""

    bayesian_n_trials: Annotated[int, Field(ge=10)] = 100
    """Number of trials for Bayesian optimization"""

    genetic_population_size: Annotated[int, Field(ge=10)] = 50
    """Population size for genetic algorithm"""

    genetic_generations: Annotated[int, Field(ge=10)] = 100
    """Number of generations for genetic algorithm"""

    timeout_hours: Annotated[int, Field(ge=1)] | None = None
    """Optimization timeout in hours (None = no limit)"""

    model_config = ConfigDict(frozen=False)
