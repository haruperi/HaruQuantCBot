# Exception Reference

**Document ID**: EXC-REF-001
**Version**: 1.0.0
**Date**: 2026-02-10
**Status**: Active

---

## Overview

The HQT Trading System implements a comprehensive exception hierarchy that provides standardized error handling across all system components. All exceptions inherit from `HQTBaseError` and include:

- **Error Code**: Unique identifier for the error type
- **Module**: Component where the error originated
- **Timestamp**: UTC timestamp of error occurrence
- **Message**: Human-readable error description
- **Context**: Additional fields specific to the error type

---

## Exception Hierarchy

```
HQTBaseError
├── DataError
│   ├── ValidationError
│   ├── PriceSanityError
│   ├── GapError
│   └── DuplicateError
├── TradingError
│   ├── OrderError
│   ├── MarginError
│   └── StopOutError
├── BrokerError
│   ├── ConnectionError
│   ├── TimeoutError
│   └── ReconnectError
├── EngineError
├── BridgeError
├── ConfigError
│   ├── SchemaError
│   └── SecretError
```

---

## Base Exception

### HQTBaseError

**Base class for all HQT system exceptions.**

All custom exceptions in the system inherit from this base class, providing consistent error handling with standardized fields and serialization support.

**Fields:**
- `error_code` (str): Unique error identifier
- `module` (str): Module where error occurred
- `message` (str): Error description
- `timestamp` (datetime): UTC timestamp
- `context` (dict): Additional context fields

**Methods:**
- `to_dict()`: Serialize exception to dictionary
- `__str__()`: Format as "[module] error_code: message"
- `__repr__()`: Detailed representation for debugging

**Usage:**
```python
from hqt.foundation.exceptions import HQTBaseError

raise HQTBaseError(
    error_code="SYS-001",
    module="system",
    message="System initialization failed",
    custom_field="additional_info"
)
```

---

## Data Exceptions

### DataError

**Base class for all data-related errors.**

Parent exception for data pipeline, validation, and quality issues.

**Error Code Prefix**: `DAT-`

---

### ValidationError

**Raised when data fails validation checks.**

Used when data does not meet expected constraints, schemas, or business rules.

**Context Fields:**
- `field` (str): Field that failed validation
- `value` (Any): The invalid value
- `constraint` (str): Constraint that was violated
- `expected` (Any): Expected value or format

**Example:**
```python
from hqt.foundation.exceptions import ValidationError

raise ValidationError(
    error_code="DAT-001",
    module="data.validation",
    message="Price cannot be negative",
    field="price",
    value=-100.0,
    constraint="price > 0"
)
```

---

### PriceSanityError

**Raised when price data fails sanity checks.**

Indicates unrealistic or impossible price values (negative prices, bid > ask, etc.).

**Context Fields:**
- `symbol` (str): Trading symbol
- `timestamp` (datetime): When invalid price occurred
- `bid` (float): Bid price
- `ask` (float): Ask price
- `price` (float): The problematic price value
- `reason` (str): Specific failure reason

**Example:**
```python
raise PriceSanityError(
    error_code="DAT-002",
    module="data.validation",
    message="Bid price exceeds ask price",
    symbol="EURUSD",
    bid=1.1000,
    ask=1.0900,
    reason="bid > ask"
)
```

---

### GapError

**Raised when data contains unexpected gaps in time series.**

Indicates missing data points or timestamps that violate continuity expectations.

**Context Fields:**
- `symbol` (str): Trading symbol
- `expected_time` (str): Expected timestamp
- `actual_time` (str): Actual next timestamp
- `gap_size` (int/float): Size of the gap (seconds)
- `timeframe` (str): Timeframe of the data

**Example:**
```python
raise GapError(
    error_code="DAT-003",
    module="data.pipeline",
    message="Missing 2 hours of data",
    symbol="EURUSD",
    gap_size=7200,
    expected_time="2024-01-01T10:00:00Z",
    actual_time="2024-01-01T12:00:00Z"
)
```

---

### DuplicateError

**Raised when duplicate data is detected where uniqueness is required.**

Indicates duplicate timestamps, duplicate bar data, or other uniqueness violations.

**Context Fields:**
- `symbol` (str): Trading symbol
- `timestamp` (datetime): Duplicate timestamp
- `duplicate_count` (int): Number of duplicates found
- `key` (str): The key that was duplicated

**Example:**
```python
raise DuplicateError(
    error_code="DAT-004",
    module="data.storage",
    message="Duplicate bar data detected",
    symbol="EURUSD",
    duplicate_count=3,
    key="2024-01-01T10:00:00Z"
)
```

---

## Trading Exceptions

### TradingError

**Base class for all trading-related errors.**

Parent exception for trading operations, order management, and position handling.

**Error Code Prefix**: `TRD-`

---

### OrderError

**Raised when order operations fail.**

Covers order placement, modification, cancellation, and validation failures.

**Context Fields:**
- `order_id` (str/int): Order identifier
- `symbol` (str): Trading symbol
- `order_type` (str): Type of order (market, limit, stop)
- `volume` (float): Order volume
- `price` (float): Order price
- `reason` (str): Specific failure reason

**Example:**
```python
raise OrderError(
    error_code="TRD-001",
    module="trading.orders",
    message="Invalid order volume",
    order_id="ORD-12345",
    symbol="EURUSD",
    volume=-1.0,
    reason="Volume must be positive"
)
```

---

### MarginError

**Raised when margin requirements are not met.**

Indicates insufficient margin or margin calculation errors.

**Context Fields:**
- `required_margin` (float): Margin required for operation
- `available_margin` (float): Available free margin
- `account_equity` (float): Current account equity
- `margin_level` (float): Current margin level percentage
- `operation` (str): Operation that triggered the error

**Example:**
```python
raise MarginError(
    error_code="TRD-002",
    module="trading.margin",
    message="Insufficient margin for order",
    required_margin=1000.0,
    available_margin=500.0,
    account_equity=5000.0,
    margin_level=120.0
)
```

---

### StopOutError

**Raised when stop-out conditions are triggered.**

Indicates that the account has reached stop-out level and positions are being closed.

**Context Fields:**
- `margin_level` (float): Current margin level percentage
- `stop_out_level` (float): Stop-out threshold level
- `positions_closed` (int): Number of positions closed
- `closed_position_ids` (list): Position IDs that were closed
- `remaining_equity` (float): Equity after stop-out

**Example:**
```python
raise StopOutError(
    error_code="TRD-003",
    module="trading.margin",
    message="Stop-out triggered",
    margin_level=15.0,
    stop_out_level=20.0,
    positions_closed=3
)
```

---

## Broker Exceptions

### BrokerError

**Base class for all broker-related errors.**

Parent exception for broker connectivity, communication, and broker-specific errors.

**Error Code Prefix**: `BRK-`

---

### ConnectionError

**Raised when broker connection fails or is lost.**

Indicates connectivity issues with the broker.

**Context Fields:**
- `broker` (str): Broker name/identifier
- `endpoint` (str): Connection endpoint (host:port)
- `retry_count` (int): Number of retry attempts
- `last_error` (str): Last underlying error message
- `connection_state` (str): Current connection state

**Example:**
```python
raise ConnectionError(
    error_code="BRK-001",
    module="broker.mt5",
    message="Failed to connect to MT5 terminal",
    broker="MT5",
    endpoint="localhost:5555",
    retry_count=3
)
```

---

### TimeoutError

**Raised when broker operations time out.**

Indicates that a broker operation exceeded the allowed time limit.

**Context Fields:**
- `operation` (str): The operation that timed out
- `timeout_seconds` (float): Timeout threshold in seconds
- `elapsed_seconds` (float): Actual elapsed time
- `broker` (str): Broker name/identifier

**Example:**
```python
raise TimeoutError(
    error_code="BRK-002",
    module="broker.gateway",
    message="Order placement timed out",
    operation="place_order",
    timeout_seconds=30.0,
    elapsed_seconds=35.2
)
```

---

### ReconnectError

**Raised when broker reconnection attempts fail.**

Indicates that automatic reconnection attempts have been exhausted.

**Context Fields:**
- `broker` (str): Broker name/identifier
- `attempts` (int): Total reconnection attempts made
- `max_attempts` (int): Maximum allowed attempts
- `backoff_seconds` (float): Current backoff delay
- `last_error` (str): Error from the last attempt

**Example:**
```python
raise ReconnectError(
    error_code="BRK-003",
    module="broker.gateway",
    message="Failed to reconnect after 5 attempts",
    broker="MT5",
    attempts=5,
    max_attempts=5
)
```

---

## Engine Exceptions

### EngineError

**Raised when C++ core engine operations fail.**

Covers errors from the C++ core engine including event processing and state management.

**Error Code Prefix**: `ENG-`

**Context Fields:**
- `engine_state` (str): Current engine state
- `operation` (str): The operation that failed
- `tick_count` (int): Number of ticks processed
- `event_type` (str): Type of event being processed

**Example:**
```python
raise EngineError(
    error_code="ENG-001",
    module="engine.core",
    message="Engine initialization failed",
    engine_state="initializing"
)
```

---

### BridgeError

**Raised when Python-C++ bridge operations fail.**

Indicates errors in the Nanobind bridge layer, including type conversion and GIL issues.

**Error Code Prefix**: `BRG-`

**Context Fields:**
- `bridge_operation` (str): The bridge operation that failed
- `python_type` (str): Python type involved
- `cpp_type` (str): C++ type involved
- `conversion_direction` (str): "py_to_cpp" or "cpp_to_py"
- `gil_state` (str): GIL acquisition state

**Example:**
```python
raise BridgeError(
    error_code="BRG-001",
    module="bridge.types",
    message="Failed to convert Python object to C++",
    bridge_operation="convert_bar",
    conversion_direction="py_to_cpp"
)
```

---

## Configuration Exceptions

### ConfigError

**Base class for all configuration-related errors.**

Parent exception for configuration loading, parsing, validation, and access errors.

**Error Code Prefix**: `CFG-`

**Context Fields:**
- `config_file` (str): Configuration file path
- `config_key` (str): Specific configuration key
- `config_section` (str): Configuration section

---

### SchemaError

**Raised when configuration fails schema validation.**

Indicates that configuration data does not conform to the expected schema.

**Context Fields:**
- `schema_field` (str): Field that failed validation
- `expected_type` (str): Expected data type
- `actual_type` (str): Actual data type
- `constraint` (str): Constraint that was violated
- `validation_error` (str): Underlying validation error

**Example:**
```python
raise SchemaError(
    error_code="CFG-002",
    module="config.schema",
    message="Invalid configuration value",
    schema_field="engine.buffer_size",
    expected_type="int",
    actual_type="str"
)
```

---

### SecretError

**Raised when secrets management operations fail.**

Indicates errors in retrieving, storing, or decrypting secrets.

**Context Fields:**
- `secret_key` (str): The secret key being accessed
- `operation` (str): The operation that failed (get, set, delete)
- `backend` (str): Secrets backend (keyring, encrypted_file)
- `keyring_service` (str): OS keyring service name

**Example:**
```python
raise SecretError(
    error_code="CFG-003",
    module="config.secrets",
    message="Failed to retrieve API key",
    secret_key="broker.api_key",
    operation="get",
    backend="keyring"
)
```

---

## Error Code Conventions

### Prefixes

| Prefix | Category | Range |
|--------|----------|-------|
| `DAT-` | Data errors | DAT-001 to DAT-999 |
| `TRD-` | Trading errors | TRD-001 to TRD-999 |
| `BRK-` | Broker errors | BRK-001 to BRK-999 |
| `ENG-` | Engine errors | ENG-001 to ENG-999 |
| `BRG-` | Bridge errors | BRG-001 to BRG-999 |
| `CFG-` | Config errors | CFG-001 to CFG-999 |

### Severity Guidelines

- **001-199**: Validation and input errors (recoverable)
- **200-399**: Operational errors (potentially recoverable)
- **400-599**: System errors (requires intervention)
- **600-799**: Critical errors (immediate action required)
- **800-999**: Reserved for future use

---

## Best Practices

### 1. Always Include Context

Provide relevant context fields to aid debugging:

```python
# Good
raise OrderError(
    error_code="TRD-001",
    module="trading.orders",
    message="Order rejected by broker",
    order_id=order.id,
    symbol=order.symbol,
    reason="Insufficient margin"
)

# Bad
raise Exception("Order rejected")
```

### 2. Use Appropriate Exception Types

Use the most specific exception type available:

```python
# Good
raise ValidationError(
    error_code="DAT-001",
    module="data.validation",
    message="Invalid price",
    field="price",
    value=price
)

# Less specific
raise DataError(
    error_code="DAT-001",
    module="data",
    message="Invalid price"
)
```

### 3. Catch Specific Exceptions

Catch specific exception types when possible:

```python
try:
    process_order()
except MarginError as e:
    # Handle margin-specific logic
    log.error(f"Margin error: {e}")
except OrderError as e:
    # Handle other order errors
    log.error(f"Order error: {e}")
```

### 4. Log Exception Details

Use `to_dict()` for structured logging:

```python
try:
    risky_operation()
except HQTBaseError as e:
    logger.error("Operation failed", extra=e.to_dict())
    raise
```

---

## Exception Handling Patterns

### Pattern 1: Error Recovery

```python
from hqt.foundation.exceptions import ConnectionError, ReconnectError

try:
    broker.connect()
except ConnectionError:
    try:
        broker.reconnect()
    except ReconnectError as e:
        logger.critical("Failed to establish connection", extra=e.to_dict())
        raise
```

### Pattern 2: Error Translation

```python
from hqt.foundation.exceptions import DataError, EngineError

try:
    data = load_data()
except DataError as e:
    raise EngineError(
        error_code="ENG-100",
        module="engine.loader",
        message="Failed to initialize engine",
        cause=str(e),
        **e.context
    ) from e
```

### Pattern 3: Context Enrichment

```python
from hqt.foundation.exceptions import ValidationError

try:
    validate_bar(bar)
except ValidationError as e:
    # Re-raise with additional context
    e.context["validation_stage"] = "preprocessing"
    e.context["batch_id"] = batch_id
    raise
```

---

## Testing Exceptions

Example test pattern:

```python
import pytest
from hqt.foundation.exceptions import OrderError

def test_order_error():
    """Test OrderError with context."""
    with pytest.raises(OrderError) as exc_info:
        raise OrderError(
            error_code="TRD-001",
            module="test",
            message="Test error",
            order_id="TEST-123"
        )

    error = exc_info.value
    assert error.error_code == "TRD-001"
    assert error.context["order_id"] == "TEST-123"
    assert "TRD-001" in str(error)
```

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-10 | Initial exception hierarchy and reference documentation |

---

*End of Document — EXC-REF-001 v1.0.0*
