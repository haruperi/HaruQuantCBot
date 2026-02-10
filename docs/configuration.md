# Configuration Management

**HQT Trading System Configuration Guide**

This document describes the comprehensive configuration management system for the HQT Trading System, including all configuration sections, validation rules, secrets management, and hot reload capabilities.

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Configuration Sections](#configuration-sections)
  - [Engine Configuration](#engine-configuration)
  - [Data Configuration](#data-configuration)
  - [Broker Configuration](#broker-configuration)
  - [Risk Management Configuration](#risk-management-configuration)
  - [Notification Configuration](#notification-configuration)
  - [Logging Configuration](#logging-configuration)
  - [UI Configuration](#ui-configuration)
  - [Database Configuration](#database-configuration)
  - [Optimization Configuration](#optimization-configuration)
- [Secrets Management](#secrets-management)
- [Environment Variables](#environment-variables)
- [Hot Reload](#hot-reload)
- [Validation Rules](#validation-rules)
- [Examples](#examples)

---

## Overview

The HQT configuration system provides:

- **Type-safe Pydantic models** with automatic validation
- **TOML file loading** with environment-specific overlays
- **Secrets management** using OS keyring or encrypted file storage
- **Environment variable resolution** for dynamic configuration
- **Hot reload** for select configuration keys without restart
- **Cross-field validation** to ensure consistency across components
- **Configuration freezing** to prevent accidental modifications

---

## Quick Start

### Basic Usage

```python
from hqt.foundation.config import ConfigManager

# Initialize config manager
manager = ConfigManager(config_dir="config")

# Load configuration (defaults to development environment)
config = manager.load(env="development")

# Access configuration values
print(f"Tick buffer size: {config.engine.tick_buffer_size}")
print(f"Max positions: {config.risk.max_positions}")
print(f"Log level: {config.logging.level}")
```

### Configuration Files

Create `config/base.toml` with base settings:

```toml
[engine]
tick_buffer_size = 100000
worker_threads = 4
enable_wal = true

[data]
storage_format = "parquet"
compression = "snappy"
validation_enabled = true

[risk]
max_positions = 10
risk_per_trade_percent = 1.0
max_daily_loss_percent = 5.0
enable_circuit_breaker = true
```

Create `config/production.toml` for production overrides:

```toml
[engine]
worker_threads = 8

[risk]
max_positions = 20
max_daily_loss_percent = 3.0

[logging]
level = "WARNING"
```

Load production configuration:

```python
config = manager.load(env="production", freeze=True)
```

---

## Configuration Sections

### Engine Configuration

Controls the C++ core engine performance and memory management.

**Section:** `[engine]`

| Key | Type | Default | Range | Description |
|-----|------|---------|-------|-------------|
| `tick_buffer_size` | int | 100000 | 1-1000000 | Maximum ticks in memory buffer |
| `event_queue_size` | int | 10000 | 1-100000 | Event processing queue size |
| `worker_threads` | int | 4 | 1-32 | Parallel processing threads |
| `enable_wal` | bool | true | - | Enable Write-Ahead Logging |
| `wal_sync_interval_ms` | int | 1000 | 0-10000 | WAL fsync interval (0=immediate) |

**Example:**

```toml
[engine]
tick_buffer_size = 50000
event_queue_size = 5000
worker_threads = 8
enable_wal = true
wal_sync_interval_ms = 500
```

---

### Data Configuration

Controls data providers, storage formats, and validation.

**Section:** `[data]`

| Key | Type | Default | Options | Description |
|-----|------|---------|---------|-------------|
| `storage_path` | Path | "data" | - | Base data storage directory |
| `storage_format` | str | "parquet" | parquet, hdf5 | Storage file format |
| `compression` | str | "snappy" | snappy, gzip, lz4, zstd, none | Compression algorithm |
| `default_provider` | str | "mt5" | mt5, dukascopy, csv, custom | Default data provider |
| `validation_enabled` | bool | true | - | Enable data quality validation |
| `validation_strict` | bool | false | - | Strict validation (reject invalid data) |
| `max_gap_seconds` | int | 300 | ≥0 | Maximum allowed data gap |
| `max_spread_multiplier` | float | 3.0 | >0 | Max spread as multiplier of median |

**Example:**

```toml
[data]
storage_path = "D:/TradingData"
storage_format = "parquet"
compression = "snappy"
default_provider = "mt5"
validation_enabled = true
validation_strict = false
max_gap_seconds = 300
max_spread_multiplier = 3.0
```

---

### Broker Configuration

Controls broker connectivity and gateway settings.

**Section:** `[broker]`

| Key | Type | Default | Range | Description |
|-----|------|---------|-------|-------------|
| `broker_type` | str | "paper" | mt5, paper, custom | Broker type |
| `mt5_terminal_path` | Path | null | - | MT5 terminal path (Windows) |
| `mt5_login` | int | null | - | MT5 account login number |
| `mt5_server` | str | null | - | MT5 server name |
| `zmq_tick_port` | int | 5555 | 1024-65535 | ZeroMQ tick data port |
| `zmq_command_port` | int | 5556 | 1024-65535 | ZeroMQ command port |
| `connection_timeout_seconds` | int | 30 | >0 | Connection timeout |
| `reconnect_attempts` | int | 5 | ≥0 | Max reconnection attempts |
| `reconnect_backoff_seconds` | int | 5 | ≥1 | Reconnection backoff time |

**Validation:**
- `zmq_tick_port` and `zmq_command_port` must be different
- MT5 broker requires `mt5_login` and `mt5_server`

**Example:**

```toml
[broker]
broker_type = "mt5"
mt5_terminal_path = "C:/Program Files/MetaTrader 5/terminal64.exe"
mt5_login = "${secret:mt5.login}"
mt5_server = "${secret:mt5.server}"
zmq_tick_port = 5555
zmq_command_port = 5556
connection_timeout_seconds = 30
reconnect_attempts = 5
reconnect_backoff_seconds = 5
```

---

### Risk Management Configuration

Controls position sizing, risk limits, and portfolio constraints.

**Section:** `[risk]`

| Key | Type | Default | Range | Description |
|-----|------|---------|-------|-------------|
| `position_sizing_method` | str | "risk_percent" | fixed_lot, risk_percent, kelly, atr_based, fixed_capital | Position sizing method |
| `risk_per_trade_percent` | float | 1.0 | 0-100 | Risk per trade (% equity) |
| `max_positions` | int | 10 | ≥1 | Maximum concurrent positions |
| `max_daily_trades` | int | 20 | ≥1 | Maximum trades per day |
| `max_daily_loss_percent` | float | 5.0 | 0-100 | Daily loss limit (% equity) |
| `max_drawdown_percent` | float | 20.0 | 0-100 | Maximum drawdown allowed |
| `max_correlation` | float | 0.7 | 0-1 | Max correlation between positions |
| `stop_out_level_percent` | float | 20.0 | 0-100 | Stop-out margin level |
| `enable_circuit_breaker` | bool | true | - | Enable circuit breaker |
| `circuit_breaker_threshold_percent` | float | 3.0 | >0 | Circuit breaker threshold (5min loss %) |

**Validation:**
- `circuit_breaker_threshold_percent` must be less than `max_daily_loss_percent`

**Example:**

```toml
[risk]
position_sizing_method = "risk_percent"
risk_per_trade_percent = 1.0
max_positions = 10
max_daily_trades = 20
max_daily_loss_percent = 5.0
max_drawdown_percent = 20.0
max_correlation = 0.7
stop_out_level_percent = 20.0
enable_circuit_breaker = true
circuit_breaker_threshold_percent = 3.0
```

---

### Notification Configuration

Controls notification channels and triggers.

**Section:** `[notifications]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | false | Enable notification system |
| `channels` | list[str] | [] | Active channels (telegram, email, webhook) |
| `telegram_bot_token` | str | null | Telegram bot API token (use secret) |
| `telegram_chat_id` | str | null | Telegram chat ID |
| `email_smtp_host` | str | null | SMTP server hostname |
| `email_smtp_port` | int | 587 | SMTP server port |
| `email_from` | str | null | From email address |
| `email_to` | list[str] | [] | Recipient email addresses |
| `notify_on_trade` | bool | true | Notify on trade execution |
| `notify_on_error` | bool | true | Notify on errors |
| `notify_on_disconnect` | bool | true | Notify on broker disconnect |
| `rate_limit_messages_per_hour` | int | 60 | Max messages per hour |

**Validation:**
- Telegram channel requires `telegram_bot_token` and `telegram_chat_id`
- Email channel requires `email_smtp_host` and `email_to`

**Example:**

```toml
[notifications]
enabled = true
channels = ["telegram"]
telegram_bot_token = "${secret:telegram.bot_token}"
telegram_chat_id = "${secret:telegram.chat_id}"
notify_on_trade = true
notify_on_error = true
notify_on_disconnect = true
rate_limit_messages_per_hour = 60
```

---

### Logging Configuration

Controls logging levels, outputs, and formats.

**Section:** `[logging]`

| Key | Type | Default | Options | Description |
|-----|------|---------|---------|-------------|
| `level` | str | "INFO" | DEBUG, INFO, WARNING, ERROR, CRITICAL | Global log level |
| `console_enabled` | bool | true | - | Enable console output |
| `console_level` | str | "INFO" | DEBUG, INFO, WARNING, ERROR, CRITICAL | Console log level |
| `file_enabled` | bool | true | - | Enable file output |
| `file_level` | str | "DEBUG" | DEBUG, INFO, WARNING, ERROR, CRITICAL | File log level |
| `file_path` | Path | "logs/hqt.log" | - | Log file path |
| `file_max_bytes` | int | 10485760 | >0 | Max file size before rotation (bytes) |
| `file_backup_count` | int | 5 | ≥0 | Number of backup files |
| `json_enabled` | bool | true | - | Enable JSON structured logging |
| `json_path` | Path | "logs/hqt.json" | - | JSON log file path |
| `enable_redaction` | bool | true | - | Enable sensitive data redaction |

**Example:**

```toml
[logging]
level = "INFO"
console_enabled = true
console_level = "INFO"
file_enabled = true
file_level = "DEBUG"
file_path = "logs/hqt.log"
file_max_bytes = 10485760  # 10MB
file_backup_count = 5
json_enabled = true
json_path = "logs/hqt.json"
enable_redaction = true
```

---

### UI Configuration

Controls desktop UI appearance and performance.

**Section:** `[ui]`

| Key | Type | Default | Range | Description |
|-----|------|---------|-------|-------------|
| `theme` | str | "dark" | light, dark, auto | UI theme |
| `window_width` | int | 1920 | ≥800 | Default window width (pixels) |
| `window_height` | int | 1080 | ≥600 | Default window height (pixels) |
| `chart_update_interval_ms` | int | 1000 | ≥100 | Chart refresh interval |
| `max_chart_points` | int | 10000 | ≥1000 | Max points on chart |
| `enable_animations` | bool | true | - | Enable UI animations |
| `font_size` | int | 10 | 8-24 | UI font size (points) |

**Example:**

```toml
[ui]
theme = "dark"
window_width = 1920
window_height = 1080
chart_update_interval_ms = 1000
max_chart_points = 10000
enable_animations = true
font_size = 10
```

---

### Database Configuration

Controls database connectivity and pooling.

**Section:** `[database]`

| Key | Type | Default | Range | Description |
|-----|------|---------|-------|-------------|
| `url` | str | "sqlite:///hqt.db" | - | Database connection URL |
| `echo` | bool | false | - | Echo SQL statements (debug) |
| `pool_size` | int | 5 | ≥1 | Connection pool size |
| `max_overflow` | int | 10 | ≥0 | Maximum overflow connections |
| `pool_timeout` | int | 30 | ≥1 | Pool timeout (seconds) |
| `pool_recycle` | int | 3600 | ≥-1 | Connection recycle time (-1=no recycle) |
| `enable_migrations` | bool | true | - | Auto-run migrations on startup |
| `backup_enabled` | bool | true | - | Enable automatic backups |
| `backup_interval_hours` | int | 24 | ≥1 | Backup interval (hours) |

**Example:**

```toml
[database]
url = "postgresql://user:pass@localhost/hqt"
echo = false
pool_size = 5
max_overflow = 10
pool_timeout = 30
pool_recycle = 3600
enable_migrations = true
backup_enabled = true
backup_interval_hours = 24
```

---

### Optimization Configuration

Controls parameter optimization and backtesting.

**Section:** `[optimization]`

| Key | Type | Default | Options | Description |
|-----|------|---------|---------|-------------|
| `method` | str | "grid" | grid, bayesian, genetic | Optimization method |
| `max_parallel_workers` | int | 4 | ≥1 | Max parallel workers |
| `use_ray` | bool | true | - | Use Ray for distributed optimization |
| `objective_function` | str | "sharpe" | sharpe, profit_factor, total_return, calmar, custom | Objective function |
| `bayesian_n_trials` | int | 100 | ≥10 | Trials for Bayesian optimization |
| `genetic_population_size` | int | 50 | ≥10 | Population size (genetic algorithm) |
| `genetic_generations` | int | 100 | ≥10 | Generations (genetic algorithm) |
| `timeout_hours` | int | null | ≥1 or null | Optimization timeout (null=no limit) |

**Validation:**
- `max_parallel_workers` should not exceed 2x `engine.worker_threads`

**Example:**

```toml
[optimization]
method = "bayesian"
max_parallel_workers = 8
use_ray = true
objective_function = "sharpe"
bayesian_n_trials = 200
timeout_hours = 12
```

---

## Secrets Management

The HQT config system provides secure storage for sensitive values like API keys and passwords.

### Using Secrets Manager

```python
from hqt.foundation.config import SecretsManager

# Initialize secrets manager
secrets = SecretsManager(service_name="hqt_trading")

# Store a secret
secrets.set("mt5.login", "12345678")
secrets.set("mt5.password", "mypassword")
secrets.set("telegram.bot_token", "123456:ABC-DEF")

# Retrieve a secret
login = secrets.get("mt5.login")
password = secrets.get("mt5.password", default="")

# Delete a secret
secrets.delete("old.api.key")

# List all keys (file backend only)
if secrets.get_backend() == "encrypted_file":
    keys = secrets.list_keys()
```

### Storage Backends

1. **OS Keyring (Preferred):**
   - Uses system keyring (Windows Credential Manager, macOS Keychain, Linux Secret Service)
   - Automatically used if `keyring` package is available
   - Most secure option

2. **Encrypted File (Fallback):**
   - Uses Fernet encryption to store secrets in `~/.hqt/secrets.enc`
   - Encryption key stored in `~/.hqt/secrets.key` (600 permissions)
   - Used when OS keyring is unavailable

### Using Secrets in Configuration

Reference secrets in TOML files using `${secret:key.name}`:

```toml
[broker]
mt5_login = "${secret:mt5.login}"
mt5_server = "${secret:mt5.server}"

[notifications]
telegram_bot_token = "${secret:telegram.bot_token}"
telegram_chat_id = "${secret:telegram.chat_id}"
```

---

## Environment Variables

Use environment variables for dynamic configuration using `${env:VAR_NAME}`:

```toml
[engine]
tick_buffer_size = "${env:TICK_BUFFER_SIZE}"
worker_threads = "${env:WORKER_THREADS}"

[data]
storage_path = "${env:DATA_PATH}"
```

Set environment variables before loading config:

```bash
export TICK_BUFFER_SIZE=50000
export WORKER_THREADS=8
export DATA_PATH=/mnt/data/trading
```

Or in Python:

```python
import os
os.environ["TICK_BUFFER_SIZE"] = "50000"
os.environ["WORKER_THREADS"] = "8"

config = manager.load()
```

---

## Hot Reload

Certain configuration keys can be reloaded at runtime without restart.

### Hot-Reloadable Keys

- `logging.level`
- `logging.console_level`
- `logging.file_level`
- `ui.theme`
- `ui.chart_update_interval_ms`
- `notifications.enabled`
- `risk.max_positions`
- `risk.max_daily_trades`

### Using Hot Reload

```python
from hqt.foundation.config import ConfigManager

manager = ConfigManager()
config = manager.load(env="development", freeze=False)

# Modify config file (e.g., change logging.level in development.toml)
# Then hot reload specific keys
manager.reload_hot(["logging.level"])

# Or reload all whitelisted keys
manager.reload_hot()

# Register callback for reload events
def on_config_reload(new_config):
    print(f"Config reloaded! New log level: {new_config.logging.level}")

manager.register_reload_callback(on_config_reload)
```

**Important:** Configuration must NOT be frozen for hot reload to work.

---

## Validation Rules

The configuration system performs comprehensive validation:

### Field-Level Validation

- Type checking (int, float, str, bool, Path)
- Range validation (min/max values)
- Enum validation (restricted options)
- Pattern validation (regex for strings)

### Cross-Field Validation

1. **ZMQ Ports:**
   - `broker.zmq_tick_port` ≠ `broker.zmq_command_port`

2. **Circuit Breaker:**
   - `risk.circuit_breaker_threshold_percent` < `risk.max_daily_loss_percent`

3. **Optimization Workers:**
   - `optimization.max_parallel_workers` ≤ 2 × `engine.worker_threads`

4. **Notification Channels:**
   - Telegram requires `telegram_bot_token` and `telegram_chat_id`
   - Email requires `email_smtp_host` and `email_to`

5. **MT5 Broker:**
   - MT5 broker requires `mt5_login` and `mt5_server`

### Handling Validation Errors

```python
from hqt.foundation.config import ConfigManager
from hqt.foundation.exceptions import ConfigError, SchemaError

try:
    manager = ConfigManager(config_dir="config")
    config = manager.load(env="production")
except ConfigError as e:
    print(f"Configuration file error: {e.message}")
    print(f"Error code: {e.error_code}")
    print(f"File: {e.context.get('config_file')}")
except SchemaError as e:
    print(f"Validation error: {e.message}")
    print(f"Details: {e.context.get('validation_error')}")
```

---

## Examples

### Complete Configuration Example

**`config/base.toml`:**

```toml
# Engine Configuration
[engine]
tick_buffer_size = 100000
event_queue_size = 10000
worker_threads = 4
enable_wal = true
wal_sync_interval_ms = 1000

# Data Management
[data]
storage_path = "data"
storage_format = "parquet"
compression = "snappy"
default_provider = "mt5"
validation_enabled = true
validation_strict = false
max_gap_seconds = 300
max_spread_multiplier = 3.0

# Broker Connectivity
[broker]
broker_type = "paper"
zmq_tick_port = 5555
zmq_command_port = 5556
connection_timeout_seconds = 30
reconnect_attempts = 5
reconnect_backoff_seconds = 5

# Risk Management
[risk]
position_sizing_method = "risk_percent"
risk_per_trade_percent = 1.0
max_positions = 10
max_daily_trades = 20
max_daily_loss_percent = 5.0
max_drawdown_percent = 20.0
max_correlation = 0.7
stop_out_level_percent = 20.0
enable_circuit_breaker = true
circuit_breaker_threshold_percent = 3.0

# Notifications (disabled by default)
[notifications]
enabled = false
channels = []
rate_limit_messages_per_hour = 60

# Logging
[logging]
level = "INFO"
console_enabled = true
console_level = "INFO"
file_enabled = true
file_level = "DEBUG"
file_path = "logs/hqt.log"
file_max_bytes = 10485760
file_backup_count = 5
json_enabled = true
json_path = "logs/hqt.json"
enable_redaction = true

# Desktop UI
[ui]
theme = "dark"
window_width = 1920
window_height = 1080
chart_update_interval_ms = 1000
max_chart_points = 10000
enable_animations = true
font_size = 10

# Database
[database]
url = "sqlite:///hqt.db"
echo = false
pool_size = 5
max_overflow = 10
pool_timeout = 30
pool_recycle = 3600
enable_migrations = true
backup_enabled = true
backup_interval_hours = 24

# Optimization
[optimization]
method = "grid"
max_parallel_workers = 4
use_ray = true
objective_function = "sharpe"
bayesian_n_trials = 100
genetic_population_size = 50
genetic_generations = 100
```

**`config/production.toml`:**

```toml
# Production Overrides

[engine]
tick_buffer_size = 200000
worker_threads = 8

[data]
storage_path = "/mnt/trading/data"
validation_strict = true

[broker]
broker_type = "mt5"
mt5_terminal_path = "C:/Program Files/MetaTrader 5/terminal64.exe"
mt5_login = "${secret:mt5.login}"
mt5_server = "${secret:mt5.server}"

[risk]
max_positions = 20
max_daily_loss_percent = 3.0
circuit_breaker_threshold_percent = 2.0

[notifications]
enabled = true
channels = ["telegram", "email"]
telegram_bot_token = "${secret:telegram.bot_token}"
telegram_chat_id = "${secret:telegram.chat_id}"
email_smtp_host = "smtp.gmail.com"
email_smtp_port = 587
email_from = "${secret:email.from}"
email_to = ["${secret:email.to}"]

[logging]
level = "WARNING"
console_level = "WARNING"
file_level = "INFO"

[optimization]
max_parallel_workers = 16
```

### Loading Configuration

```python
from hqt.foundation.config import ConfigManager, SecretsManager

# Setup secrets first
secrets = SecretsManager()
secrets.set("mt5.login", "12345678")
secrets.set("mt5.server", "MetaQuotes-Demo")
secrets.set("telegram.bot_token", "123456:ABC-DEF")
secrets.set("telegram.chat_id", "987654321")

# Load production configuration
manager = ConfigManager(config_dir="config", secrets_manager=secrets)
config = manager.load(env="production", freeze=True)

# Use configuration
print(f"Worker threads: {config.engine.worker_threads}")
print(f"Max positions: {config.risk.max_positions}")
print(f"Broker type: {config.broker.broker_type}")
```

---

## Best Practices

1. **Use Secrets for Sensitive Data:**
   - Never store API keys, passwords, or tokens in TOML files
   - Always use `${secret:key.name}` placeholders

2. **Environment-Specific Overlays:**
   - Keep common settings in `base.toml`
   - Use environment files (`development.toml`, `production.toml`) for overrides

3. **Freeze Production Configuration:**
   - Always freeze config in production to prevent accidental modifications
   - Only leave unfrozen for hot reload scenarios

4. **Validate Early:**
   - Load and validate configuration at application startup
   - Handle `ConfigError` and `SchemaError` gracefully

5. **Use Hot Reload Sparingly:**
   - Only reload configuration for non-critical runtime adjustments
   - Avoid hot reloading engine or broker settings

6. **Document Custom Settings:**
   - Add comments in TOML files explaining non-obvious values
   - Keep this documentation updated with configuration changes

---

## Troubleshooting

### Configuration File Not Found

```python
hqt.foundation.exceptions.config.ConfigError: [config.manager] CFG-001: Base configuration file not found
```

**Solution:** Ensure `config/base.toml` exists in the config directory.

### Validation Error

```python
hqt.foundation.exceptions.config.SchemaError: [config.manager] CFG-004: Configuration validation failed
```

**Solution:** Check validation error details and ensure all required fields meet constraints.

### Secret Not Found

```python
hqt.foundation.exceptions.config.ConfigError: [config.manager] CFG-005: Secret not found: mt5.login
```

**Solution:** Store the secret using `SecretsManager.set()` before loading config.

### Hot Reload on Frozen Config

```python
hqt.foundation.exceptions.config.ConfigError: [config.manager] CFG-007: Cannot hot reload frozen configuration
```

**Solution:** Load config with `freeze=False` if hot reload is needed.

---

## API Reference

See the following modules for detailed API documentation:

- `hqt.foundation.config.models` - Pydantic configuration models
- `hqt.foundation.config.schema` - AppConfig root schema
- `hqt.foundation.config.manager` - ConfigManager for loading and hot reload
- `hqt.foundation.config.secrets` - SecretsManager for secure storage

For exception handling:

- `hqt.foundation.exceptions.config` - ConfigError, SchemaError, SecretError

---

**Last Updated:** 2026-02-10
**Version:** 1.0.0
**Phase:** Phase 1, Task 1.5 - Configuration Management
