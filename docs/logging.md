

# Logging System Documentation

**Document ID**: LOG-DOC-001
**Version**: 1.0.0
**Date**: 2026-02-10
**Status**: Active

---

## Overview

The HQT Trading System implements a comprehensive logging framework built on Python's standard `logging` module with extensive customizations for:

- **Structured Logging**: JSON output for machine processing
- **Colored Console**: Terminal output with ANSI colors
- **Automatic Redaction**: Sensitive data (API keys, passwords) masked automatically
- **Flexible Filtering**: Module-based, level-based, keyword-based filtering
- **File Rotation**: Automatic log rotation with configurable size limits
- **C++ Bridge**: Integration with spdlog (Phase 3)

---

## Quick Start

### Basic Setup

```python
from hqt.foundation.logging import setup_logging, get_logger

# Initialize logging (call once at application start)
setup_logging()

# Get a logger
logger = get_logger(__name__)

# Use it
logger.debug("Detailed debug information")
logger.info("General information message")
logger.warning("Warning message")
logger.error("Error occurred", extra={"error_code": "E001"})
logger.critical("Critical system failure")
```

### Output Locations

By default, logs are written to:
- **Console** (`stdout`): INFO level and above, colored
- **File** (`logs/hqt.log`): DEBUG level and above, detailed format
- **JSON** (`logs/hqt.json`): DEBUG level and above, structured format

---

## Configuration

### Default Configuration

The system uses a comprehensive default configuration that can be customized:

```python
from hqt.foundation.logging import setup_logging, DEFAULT_LOG_CONFIG

# Use defaults
setup_logging()

# Or customize
custom_config = DEFAULT_LOG_CONFIG.copy()
custom_config["loggers"]["hqt"]["level"] = "INFO"
setup_logging(custom_config)
```

### Custom Configuration

```python
custom_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simple",
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}

setup_logging(custom_config, log_dir="custom_logs")
```

---

## Formatters

### ConsoleFormatter

Colored output for terminal display with automatic TTY detection.

**Features:**
- Level-based coloring (DEBUG=cyan, INFO=green, WARNING=yellow, ERROR=red, CRITICAL=bold magenta)
- Automatic color detection (disabled when piping to files)
- Customizable format string

**Usage:**
```python
from hqt.foundation.logging import ConsoleFormatter
import logging

handler = logging.StreamHandler()
handler.setFormatter(ConsoleFormatter(
    fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    use_colors=True  # or None for auto-detect
))
```

**Color Codes:**
- `DEBUG`: Cyan
- `INFO`: Green
- `WARNING`: Yellow
- `ERROR`: Red
- `CRITICAL`: Bold Magenta

---

### FileFormatter

Detailed file output with millisecond precision timestamps.

**Features:**
- Millisecond-precision timestamps
- Module and function information
- Line numbers
- Thread information (when not MainThread)

**Usage:**
```python
from hqt.foundation.logging import FileFormatter
import logging

handler = logging.FileHandler("app.log")
handler.setFormatter(FileFormatter(
    fmt="%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
))
```

**Output Example:**
```
2024-01-01 10:00:00.123 | INFO | hqt.trading | execute_order:42 | Order executed successfully
```

---

### JsonFormatter

Structured JSON output for log aggregation and analysis.

**Features:**
- One JSON object per log record
- All log fields included
- ISO 8601 timestamps
- Automatic serialization of extra fields

**Usage:**
```python
from hqt.foundation.logging import JsonFormatter
import logging

handler = logging.FileHandler("app.json")
handler.setFormatter(JsonFormatter())
```

**Output Example:**
```json
{
  "timestamp": "2024-01-01T10:00:00.123Z",
  "level": "INFO",
  "logger": "hqt.trading",
  "module": "orders",
  "function": "execute_order",
  "line": 42,
  "message": "Order executed successfully",
  "order_id": "ORD-12345",
  "symbol": "EURUSD"
}
```

---

## Handlers

### RotatingFileHandlerWrapper

File handler with automatic rotation and directory creation.

**Features:**
- Automatic directory creation
- Size-based rotation
- Configurable backup count
- UTF-8 encoding by default

**Usage:**
```python
from hqt.foundation.logging import RotatingFileHandlerWrapper

handler = RotatingFileHandlerWrapper(
    filename="logs/app.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8"
)
```

**Rotation Behavior:**
- When `maxBytes` is reached, file is rotated
- Old files are renamed: `app.log.1`, `app.log.2`, etc.
- Oldest file is deleted when `backupCount` is exceeded

---

### JsonFileHandler

Specialized handler for JSON log files.

**Features:**
- Automatic JSON formatting (no separate formatter needed)
- One JSON object per line
- Size-based rotation
- Handles non-serializable objects gracefully

**Usage:**
```python
from hqt.foundation.logging import JsonFileHandler

handler = JsonFileHandler(
    filename="logs/app.json",
    maxBytes=10 * 1024 * 1024,
    backupCount=3
)
```

---

### SpdlogBridgeHandler

Bridge to C++ spdlog library (Phase 3).

**Status:** Placeholder implementation, will be completed in Phase 3 with Nanobind integration.

**Planned Features:**
- Forward Python logs to C++ spdlog
- Unified logging across Python and C++ components
- High-performance logging for critical paths

---

## Filters

### ModuleFilter

Filter logs by module name patterns (glob-style).

**Usage:**
```python
from hqt.foundation.logging import ModuleFilter

# Only allow logs from trading modules
filter_obj = ModuleFilter(
    allow=["hqt.trading.*", "hqt.risk.*"],
    block=[]
)
handler.addFilter(filter_obj)

# Block verbose modules
filter_obj = ModuleFilter(
    allow=[],
    block=["hqt.data.providers.mt5"]
)
```

**Pattern Syntax:**
- `*` matches any characters
- Patterns use full module names
- Block patterns take precedence over allow patterns

---

### LevelRangeFilter

Filter logs by level range (min and max).

**Usage:**
```python
from hqt.foundation.logging import LevelRangeFilter
import logging

# Only WARNING and ERROR (not CRITICAL)
filter_obj = LevelRangeFilter(
    min_level=logging.WARNING,
    max_level=logging.ERROR
)

# DEBUG and INFO only
filter_obj = LevelRangeFilter(
    min_level=logging.DEBUG,
    max_level=logging.INFO
)
```

**Use Cases:**
- Separate handlers for different log levels
- Route errors to one file, info to another
- Filter out critical logs for normal handlers

---

### KeywordFilter

Filter logs by keyword matching in messages.

**Usage:**
```python
from hqt.foundation.logging import KeywordFilter

# Only log messages about orders or trades
filter_obj = KeywordFilter(
    keywords=["order", "trade", "execution"],
    mode="allow",
    case_sensitive=False
)

# Block debug messages
filter_obj = KeywordFilter(
    keywords=["debug", "verbose", "trace"],
    mode="block",
    case_sensitive=False
)
```

**Modes:**
- `allow`: Only log messages containing keywords
- `block`: Block messages containing keywords

---

### ThrottleFilter

Suppress repeated identical log messages.

**Usage:**
```python
from hqt.foundation.logging import ThrottleFilter

# Suppress duplicates within 60 seconds
filter_obj = ThrottleFilter(window_seconds=60)
handler.addFilter(filter_obj)
```

**Behavior:**
- First occurrence of a message is logged
- Subsequent identical messages within window are suppressed
- Message identity based on: logger name + level + message content
- Automatic cleanup of old entries

---

## Sensitive Data Redaction

### RedactionFilter

Automatically masks sensitive information in logs.

**Protected Data:**
- API keys and tokens
- Passwords and secrets
- AWS keys
- Credit card numbers
- JWT tokens
- Authorization headers

**Usage:**
```python
from hqt.foundation.logging import RedactionFilter

# Basic usage
filter_obj = RedactionFilter()
handler.addFilter(filter_obj)

# Custom redaction text
filter_obj = RedactionFilter(redaction_text="***HIDDEN***")

# Redact emails too
filter_obj = RedactionFilter(redact_emails=True)
```

**Example:**
```python
logger.info("Connecting with api_key=sk-1234567890abcdef")
# Logged as: "Connecting with api_key [REDACTED]"

logger.info("User logged in", extra={"password": "secret123"})
# Logged with: password="[REDACTED]"
```

### Custom Redaction Patterns

```python
from hqt.foundation.logging import RedactionFilter, add_redaction_pattern

filter_obj = RedactionFilter()

# Add custom pattern
add_redaction_pattern(
    filter_obj,
    "account_id",
    r"ACC-\d{10}"
)

handler.addFilter(filter_obj)
```

**Built-in Patterns:**
- `api_key`: API keys in various formats
- `bearer_token`: Bearer tokens
- `password`: Password fields
- `secret`: Secret keys and private keys
- `aws_key`: AWS access keys
- `aws_secret`: AWS secret keys
- `credit_card`: Credit card numbers
- `jwt`: JWT tokens
- `auth_header`: Authorization headers

---

## Best Practices

### 1. Use Appropriate Log Levels

```python
# DEBUG: Detailed diagnostic information
logger.debug("Processing order", extra={"order_id": order.id, "state": order.state})

# INFO: General informational messages
logger.info("Order executed successfully", extra={"order_id": order.id})

# WARNING: Warning messages (recoverable issues)
logger.warning("High latency detected", extra={"latency_ms": 250})

# ERROR: Error messages (non-critical failures)
logger.error("Failed to place order", exc_info=True, extra={"order_id": order.id})

# CRITICAL: Critical errors (system failure)
logger.critical("Database connection lost", exc_info=True)
```

### 2. Include Structured Context

```python
# Good: Structured extra fields
logger.info(
    "Trade executed",
    extra={
        "symbol": "EURUSD",
        "volume": 1.0,
        "price": 1.1000,
        "order_id": "ORD-123"
    }
)

# Bad: Unstructured string interpolation
logger.info(f"Trade executed: EURUSD 1.0 @ 1.1000")
```

### 3. Log Exceptions Properly

```python
try:
    risky_operation()
except Exception as e:
    logger.error(
        "Operation failed",
        exc_info=True,  # Includes full traceback
        extra={"operation": "order_placement", "user_id": user_id}
    )
    raise
```

### 4. Use Module-Level Loggers

```python
# At module level
logger = get_logger(__name__)

# In functions
def process_order(order):
    logger.info("Processing order", extra={"order_id": order.id})
```

### 5. Configure Once, Use Everywhere

```python
# In main.py or __init__.py
from hqt.foundation.logging import setup_logging
import atexit

setup_logging()
atexit.register(shutdown_logging)

# In other modules
from hqt.foundation.logging import get_logger
logger = get_logger(__name__)
```

---

## Performance Considerations

### 1. Lazy Message Formatting

```python
# Good: Message formatted only if logged
logger.debug("Processing %d orders", len(orders))

# Bad: Always formatted, even if not logged
logger.debug(f"Processing {len(orders)} orders")
```

### 2. Conditional Expensive Operations

```python
if logger.isEnabledFor(logging.DEBUG):
    expensive_data = compute_expensive_debug_info()
    logger.debug("Debug info", extra={"data": expensive_data})
```

### 3. Use Filters Wisely

- Apply filters to handlers, not root logger
- Module filters are more efficient than keyword filters
- Throttle filters add minimal overhead

---

## Troubleshooting

### Logs Not Appearing

1. Check log level: `logger.setLevel(logging.DEBUG)`
2. Check handler levels: `handler.setLevel(logging.DEBUG)`
3. Verify logger hierarchy: Use `logger.parent` to check inheritance

### Duplicate Log Messages

- Check `propagate` flag on loggers
- Ensure setup_logging() is called only once
- Review logger hierarchy

### Colors Not Working

- Check if output is a TTY: `sys.stdout.isatty()`
- Force colors: `ConsoleFormatter(use_colors=True)`
- Windows: May require colorama or ANSI support

### Redaction Not Working

- Verify RedactionFilter is added to handlers
- Check pattern matching with test cases
- Add custom patterns if needed

---

## Integration Examples

### With FastAPI

```python
from fastapi import FastAPI
from hqt.foundation.logging import setup_logging, get_logger

app = FastAPI()
setup_logging()
logger = get_logger(__name__)

@app.on_event("startup")
async def startup():
    logger.info("Application starting")

@app.get("/")
async def root():
    logger.debug("Root endpoint called")
    return {"status": "ok"}
```

### With PySide6

```python
from PySide6.QtWidgets import QApplication
from hqt.foundation.logging import setup_logging, get_logger
import sys

app = QApplication(sys.argv)
setup_logging()
logger = get_logger(__name__)

logger.info("GUI application started")
```

### With Async Code

```python
import asyncio
from hqt.foundation.logging import get_logger

logger = get_logger(__name__)

async def process_async():
    logger.info("Async processing started")
    await asyncio.sleep(1)
    logger.info("Async processing completed")
```

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-10 | Initial logging system implementation |

---

*End of Document — LOG-DOC-001 v1.0.0*
