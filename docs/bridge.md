# Nanobind Bridge Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Building](#building)
4. [API Reference](#api-reference)
5. [GIL Management](#gil-management)
6. [Memory & Lifetime Rules](#memory--lifetime-rules)
7. [Error Handling](#error-handling)
8. [Performance Considerations](#performance-considerations)
9. [Examples](#examples)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The HQT Nanobind Bridge provides Python bindings for the high-performance C++ backtesting engine. It enables writing trading strategies in Python while executing backtests at C++ speed.

### Key Features

- **High Performance**: 1M+ ticks/sec throughput even with Python callbacks
- **Zero-Copy**: Direct access to C++ data structures without copying
- **Thread-Safe**: Proper GIL management for concurrent execution
- **Pythonic API**: Decorator-style callbacks and intuitive interfaces
- **Type-Safe**: Full type hints support (coming in future release)

### Design Goals

1. **Minimize Overhead**: Keep bridge layer thin
2. **Safety**: Prevent memory leaks and crashes
3. **Pythonic**: Feel natural to Python developers
4. **Performance**: Match C++ speed where possible

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────┐
│          Python Strategy Layer                   │
│  (User code: strategies, indicators, etc.)       │
└───────────────┬─────────────────────────────────┘
                │ Python Calls
                ▼
┌─────────────────────────────────────────────────┐
│         hqt_core (Nanobind Module)               │
│  ┌──────────────────────────────────────────┐   │
│  │  bind_types.cpp (Data Structures)        │   │
│  │  • Tick, Bar, SymbolInfo                 │   │
│  │  • AccountInfo, PositionInfo, etc.       │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  bind_engine.cpp (Engine Class)          │   │
│  │  • run(), run_steps() [GIL release]      │   │
│  │  • buy(), sell(), modify(), close()      │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  bind_callbacks.cpp (Callbacks)          │   │
│  │  • set_on_tick() [GIL acquire]           │   │
│  │  • set_on_bar() [GIL acquire]            │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  bind_commands.cpp (Helpers & Errors)    │   │
│  │  • to_price(), from_price()              │   │
│  │  • Exception registration                │   │
│  └──────────────────────────────────────────┘   │
└───────────────┬─────────────────────────────────┘
                │ C++ Calls
                ▼
┌─────────────────────────────────────────────────┐
│           C++ Engine (hqt_core_lib)              │
│  EventLoop • CostsEngine • CTrade • DataFeed     │
└─────────────────────────────────────────────────┘
```

### Execution Flow

1. **Initialization**: Python creates `Engine` instance
2. **Configuration**: Python calls `load_symbol()`, `load_conversion_pair()`
3. **Callback Registration**: Python registers `on_tick`, `on_bar`, etc.
4. **Execution**: `engine.run()` releases GIL, C++ processes events
5. **Callbacks**: C++ acquires GIL, calls Python functions
6. **Completion**: `run()` returns, GIL re-acquired, results accessible

---

## Building

### Prerequisites

```bash
# Python requirements
pip install nanobind pytest numpy

# System requirements
# - CMake 3.25+
# - C++20 compiler
# - Python 3.11+ with development headers
```

### Build Commands

```bash
# Configure
cmake -B build -DCMAKE_BUILD_TYPE=Release

# Build
cmake --build build --config Release --target hqt_core

# Output
# Windows: build/bridge/Release/hqt_core.pyd
# Linux:   build/bridge/hqt_core.so
```

### Development Build

```bash
# Debug build with symbols
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --config Debug

# Build with verbose output
cmake --build build --config Release --verbose
```

### Installing Module

```bash
# Temporary (current session)
export PYTHONPATH=$PYTHONPATH:build/bridge/Release

# Or copy to site-packages
cp build/bridge/Release/hqt_core.* $(python -c "import site; print(site.getsitepackages()[0])")
```

---

## API Reference

### Module-Level Constants

```python
import hqt_core

hqt_core.__version__   # Module version (e.g., "0.3.0")
hqt_core.VERSION       # Same as __version__
hqt_core.BUILD_DATE    # Build date string
hqt_core.BUILD_TIME    # Build time string
```

### Enumerations

#### Timeframe

```python
hqt_core.Timeframe.TICK   # Tick data
hqt_core.Timeframe.M1     # 1 minute
hqt_core.Timeframe.M5     # 5 minutes
hqt_core.Timeframe.M15    # 15 minutes
hqt_core.Timeframe.M30    # 30 minutes
hqt_core.Timeframe.H1     # 1 hour
hqt_core.Timeframe.H4     # 4 hours
hqt_core.Timeframe.D1     # 1 day
hqt_core.Timeframe.W1     # 1 week
hqt_core.Timeframe.MN1    # 1 month
```

#### PositionType

```python
hqt_core.PositionType.BUY    # Long position
hqt_core.PositionType.SELL   # Short position
```

#### OrderType

```python
hqt_core.OrderType.BUY              # Market buy
hqt_core.OrderType.SELL             # Market sell
hqt_core.OrderType.BUY_LIMIT        # Buy limit order
hqt_core.OrderType.SELL_LIMIT       # Sell limit order
hqt_core.OrderType.BUY_STOP         # Buy stop order
hqt_core.OrderType.SELL_STOP        # Sell stop order
hqt_core.OrderType.BUY_STOP_LIMIT   # Buy stop-limit
hqt_core.OrderType.SELL_STOP_LIMIT  # Sell stop-limit
```

### Data Types

#### Tick

Read-only tick data structure.

```python
tick.timestamp_us  # int: Timestamp in microseconds
tick.symbol_id     # int: Symbol ID
tick.bid           # int: Bid price (fixed-point, divide by 1e6)
tick.ask           # int: Ask price (fixed-point)
tick.bid_volume    # int: Bid volume
tick.ask_volume    # int: Ask volume
tick.spread        # int: Spread in points

# Convert to readable format
bid_price = hqt_core.to_price(tick.bid)
ask_price = hqt_core.to_price(tick.ask)
```

#### Bar

Read-only bar (candlestick) structure.

```python
bar.timestamp_us  # int: Bar open time in microseconds
bar.symbol_id     # int: Symbol ID
bar.open          # int: Open price (fixed-point)
bar.high          # int: High price (fixed-point)
bar.low           # int: Low price (fixed-point)
bar.close         # int: Close price (fixed-point)
bar.tick_volume   # int: Tick volume
bar.spread        # int: Average spread
bar.real_volume   # int: Real volume

# Convert to readable format
open_price = hqt_core.to_price(bar.open)
close_price = hqt_core.to_price(bar.close)
```

#### SymbolInfo

Symbol specification (read-only access).

```python
symbol.name()             # str: Symbol name (e.g., "EURUSD")
symbol.symbol_id()        # int: Symbol ID
symbol.digits()           # int: Price decimal places
symbol.point()            # float: Point size
symbol.contract_size()    # float: Contract size
symbol.tick_size()        # float: Tick size
symbol.tick_value()       # float: Tick value
symbol.currency_base()    # str: Base currency
symbol.currency_profit()  # str: Profit currency
symbol.currency_margin()  # str: Margin currency
symbol.bid()              # float: Current bid
symbol.ask()              # float: Current ask
symbol.spread()           # int: Current spread
symbol.volume_min()       # float: Minimum volume
symbol.volume_max()       # float: Maximum volume
symbol.volume_step()      # float: Volume step
```

#### AccountInfo

Account state (read-only).

```python
account.balance()       # int: Balance (fixed-point)
account.equity()        # int: Equity (fixed-point)
account.margin()        # int: Used margin (fixed-point)
account.margin_free()   # int: Free margin (fixed-point)
account.margin_level()  # float: Margin level percentage
account.profit()        # int: Total profit (fixed-point)
account.currency()      # str: Account currency
account.leverage()      # int: Leverage

# Convert to readable format
balance = hqt_core.to_price(account.balance())
equity = hqt_core.to_price(account.equity())
```

#### PositionInfo

Open position information (read-only).

```python
pos.ticket()         # int: Position ticket
pos.symbol()         # str: Symbol name
pos.type()           # PositionType: BUY or SELL
pos.volume()         # float: Volume in lots
pos.price_open()     # float: Open price
pos.price_current()  # float: Current price
pos.stop_loss()      # float: Stop loss
pos.take_profit()    # float: Take profit
pos.profit()         # int: Profit (fixed-point)
pos.swap()           # int: Swap (fixed-point)
pos.commission()     # int: Commission (fixed-point)
pos.time()           # int: Open time (microseconds)
pos.time_update()    # int: Last update time
pos.magic()          # int: Magic number
pos.comment()        # str: Comment
```

#### OrderInfo

Pending order information (read-only).

```python
order.ticket()           # int: Order ticket
order.symbol()           # str: Symbol name
order.type()             # OrderType: Order type
order.volume()           # float: Volume
order.price_open()       # float: Order price
order.stop_loss()        # float: Stop loss
order.take_profit()      # float: Take profit
order.time_setup()       # int: Setup time
order.time_expiration()  # int: Expiration time
order.magic()            # int: Magic number
order.comment()          # str: Comment
```

#### DealInfo

Deal (trade execution) information (read-only).

```python
deal.ticket()       # int: Deal ticket
deal.order()        # int: Order ticket
deal.symbol()       # str: Symbol name
deal.type()         # DealType: Deal type
deal.position_id()  # int: Position ID
deal.volume()       # float: Volume
deal.price()        # float: Execution price
deal.profit()       # int: Profit (fixed-point)
deal.swap()         # int: Swap (fixed-point)
deal.commission()   # int: Commission (fixed-point)
deal.time()         # int: Execution time
deal.magic()        # int: Magic number
deal.comment()      # str: Comment
```

### Engine Class

#### Constructor

```python
engine = hqt_core.Engine(
    initial_balance=10000.0,  # Starting balance
    currency="USD",            # Account currency
    leverage=100               # Leverage (1:100)
)
```

#### Configuration Methods

```python
# Load symbol
symbol = hqt_core.SymbolInfo()
# ... configure symbol ...
engine.load_symbol("EURUSD", symbol)

# Load currency conversion
engine.load_conversion_pair("EUR", "USD", rate=1.10)
```

#### Run Loop Control

```python
# Run until completion (releases GIL)
engine.run()

# Run N steps (releases GIL)
processed = engine.run_steps(steps=1000)

# Pause/resume
engine.pause()
engine.resume()

# Stop
engine.stop()

# Check status
is_running = engine.is_running()
is_paused = engine.is_paused()
```

#### Trading Commands

```python
# Open BUY position
success = engine.buy(
    volume=0.1,
    symbol="EURUSD",
    sl=1.09000,      # Stop loss (optional)
    tp=1.11000,      # Take profit (optional)
    comment="test"   # Comment (optional)
)

# Open SELL position
success = engine.sell(
    volume=0.1,
    symbol="EURUSD",
    sl=1.11000,
    tp=1.09000,
    comment="test"
)

# Modify position
success = engine.modify(ticket=12345, sl=1.09500, tp=1.10500)

# Close position
success = engine.close(ticket=12345)

# Cancel order
success = engine.cancel(ticket=12345)
```

#### State Access

```python
# Get account info
account = engine.account()

# Get all open positions
positions = engine.positions()  # list[PositionInfo]

# Get all pending orders
orders = engine.orders()        # list[OrderInfo]

# Get all deals
deals = engine.deals()          # list[DealInfo]

# Get symbol info
symbol = engine.get_symbol("EURUSD")  # SymbolInfo or None

# Get current time
time_us = engine.current_time()
```

#### Callback Registration (Function Style)

```python
def on_tick_handler(tick, symbol):
    bid = hqt_core.to_price(tick.bid)
    print(f"{symbol.name()}: {bid}")

engine.set_on_tick(on_tick_handler)

# Similarly for other callbacks
engine.set_on_bar(on_bar_handler)
engine.set_on_trade(on_trade_handler)
engine.set_on_order(on_order_handler)

# Clear callback
engine.set_on_tick(None)
```

#### Callback Registration (Decorator Style)

```python
@engine.on_tick
def on_tick(tick, symbol):
    # Handle tick
    pass

@engine.on_bar
def on_bar(bar, symbol, timeframe):
    # Handle bar close
    pass

@engine.on_trade
def on_trade(deal):
    # Handle trade execution
    pass

@engine.on_order
def on_order(order):
    # Handle order state change
    pass
```

### Helper Functions

#### Price Conversion

```python
# Fixed-point to double
price = hqt_core.to_price(fixed_point_price, digits=5)

# Double to fixed-point
fixed = hqt_core.from_price(price)
```

#### Validation

```python
# Validate volume
is_valid = hqt_core.validate_volume(volume=0.1, symbol=symbol_info)

# Validate price
is_valid = hqt_core.validate_price(price=1.10000, symbol=symbol_info)
```

#### Rounding

```python
# Round price to tick
rounded_price = hqt_core.round_to_tick(price=1.100005, symbol=symbol_info)

# Round volume to step
rounded_vol = hqt_core.round_to_volume_step(volume=0.15, symbol=symbol_info)
```

### Exceptions

```python
# Engine errors
try:
    engine.buy(volume=1000.0, symbol="EURUSD")
except hqt_core.EngineError as e:
    print(f"Engine error: {e}")

# Data feed errors
try:
    bars = data_feed.get_bars(...)
except hqt_core.DataFeedError as e:
    print(f"Data error: {e}")

# Memory map errors
try:
    reader = hqt_core.MmapReader("file.bin")
except hqt_core.MmapError as e:
    print(f"Mmap error: {e}")
```

---

## GIL Management

### Overview

The Global Interpreter Lock (GIL) is Python's mechanism for thread synchronization. Proper GIL management is critical for:
- **Safety**: Preventing crashes from concurrent Python access
- **Performance**: Allowing parallel execution
- **Correctness**: Ensuring data consistency

### GIL States in Bridge

| Operation | GIL State | Reason |
|-----------|-----------|--------|
| `engine.run()` | Released | Allow concurrent Python threads |
| `engine.run_steps()` | Released | Same as run() |
| Callback invocation | Acquired | Must hold GIL to call Python |
| State access | Held | Quick operations, no release needed |
| Trading commands | Held | Quick operations |

### Detailed Behavior

#### GIL Release (Long Operations)

```cpp
// In bind_engine.cpp
.def("run", [](Engine& self) {
    nb::gil_scoped_release release;  // Release GIL
    self.run();                       // C++ executes freely
    // GIL automatically re-acquired when release goes out of scope
})
```

**Benefits**:
- Other Python threads can run
- Multiprocessing works correctly
- UI remains responsive

**Example**:

```python
import threading

def run_backtest():
    engine.run()  # GIL released, doesn't block other threads

def monitor_progress():
    while engine.is_running():
        print("Still running...")
        time.sleep(1)

# Both threads run concurrently
t1 = threading.Thread(target=run_backtest)
t2 = threading.Thread(target=monitor_progress)
t1.start()
t2.start()
```

#### GIL Acquire (Python Callbacks)

```cpp
// In bind_callbacks.cpp
self.set_on_tick([callback](const Tick& tick, const SymbolInfo& symbol) {
    nb::gil_scoped_acquire acquire;  // Acquire GIL
    try {
        callback(tick, symbol);       // Safe to call Python
    } catch (const nb::python_error& e) {
        // Handle Python exceptions
    }
});
```

**Safety**:
- GIL held before touching Python objects
- Exceptions caught and handled
- No Python calls without GIL

### Multithreading Example

```python
import hqt_core
import threading

# Create engine
engine = hqt_core.Engine()

# Shared state (protected by GIL when accessed from callbacks)
tick_count = 0
lock = threading.Lock()

@engine.on_tick
def on_tick(tick, symbol):
    global tick_count
    with lock:
        tick_count += 1

# Run in background thread
def run_engine():
    engine.run()  # GIL released during execution

thread = threading.Thread(target=run_engine)
thread.start()

# Monitor from main thread
while thread.is_alive():
    with lock:
        print(f"Processed {tick_count} ticks")
    time.sleep(1)

thread.join()
print(f"Total ticks: {tick_count}")
```

---

## Memory & Lifetime Rules

### Reference Counting

Python uses reference counting for memory management. The bridge ensures:

1. **Python holds strong references to C++**: When you create an `Engine`, Python owns it
2. **C++ doesn't hold references to Python**: Callbacks are stored as weak references
3. **No circular references**: Prevents memory leaks

### Object Lifetime

#### Owned by Python

```python
engine = hqt_core.Engine()
# Python owns engine, will delete when reference count hits zero
```

#### Borrowed References (Return Policies)

```python
# account() returns reference_internal
# Lifetime tied to engine
account = engine.account()

# Safe: engine still alive
balance = account.balance()

# Danger: engine deleted, account is dangling
engine = None
balance = account.balance()  # May crash!
```

**Rule**: Don't store references to objects returned with `reference_internal` beyond the parent's lifetime.

### Safe Patterns

```python
# Pattern 1: Use immediately
balance = engine.account().balance()

# Pattern 2: Keep parent alive
engine = hqt_core.Engine()
account = engine.account()
# ... use account ...
# Keep engine in scope

# Pattern 3: Copy data if needed
positions = list(engine.positions())  # Copies list
```

### Callback Lifetime

```python
@engine.on_tick
def on_tick(tick, symbol):
    # tick and symbol are temporary
    # Don't store references beyond callback
    pass

# Dangerous
stored_tick = None

@engine.on_tick
def on_tick(tick, symbol):
    global stored_tick
    stored_tick = tick  # BAD: tick may be invalidated

# Safe
stored_bid = None

@engine.on_tick
def on_tick(tick, symbol):
    global stored_bid
    stored_bid = hqt_core.to_price(tick.bid)  # OK: copied value
```

---

## Error Handling

### Exception Hierarchy

```
Exception
├── hqt_core.EngineError      (General engine errors)
├── hqt_core.DataFeedError    (Data access errors)
└── hqt_core.MmapError        (File mapping errors)
```

### Error Handling Patterns

```python
# Specific exception
try:
    engine.buy(volume=1000.0, symbol="EURUSD")
except hqt_core.EngineError as e:
    print(f"Insufficient margin: {e}")

# Multiple exceptions
try:
    # ... operations ...
except hqt_core.EngineError as e:
    handle_engine_error(e)
except hqt_core.DataFeedError as e:
    handle_data_error(e)
except Exception as e:
    handle_unknown_error(e)

# Callback exceptions
@engine.on_tick
def on_tick(tick, symbol):
    try:
        # ... strategy logic ...
        pass
    except Exception as e:
        # Log error, don't let it crash backtest
        print(f"Strategy error: {e}")
```

### Exception in Callbacks

Exceptions in callbacks are caught by the bridge and printed but don't crash the engine:

```python
@engine.on_bar
def on_bar(bar, symbol, timeframe):
    raise ValueError("Oops!")  # Printed but doesn't stop backtest

engine.run()  # Continues despite callback error
```

**Output**:
```
Python callback error: ValueError: Oops!
```

---

## Performance Considerations

### Throughput

- **Target**: 1M+ ticks/sec with Python callbacks
- **Overhead**: Nanobind adds <10ns per call
- **GIL Impact**: Minimal if callbacks are fast

### Optimization Tips

1. **Minimize Callback Work**
   ```python
   # Slow
   @engine.on_tick
   def on_tick(tick, symbol):
       calculate_indicators()  # Heavy computation
       check_signals()
       maybe_trade()

   # Fast
   tick_buffer = []

   @engine.on_tick
   def on_tick(tick, symbol):
       tick_buffer.append(tick.bid)  # Just append

   @engine.on_bar
   def on_bar(bar, symbol, timeframe):
       # Do heavy work on bar close
       signals = analyze(tick_buffer)
       tick_buffer.clear()
   ```

2. **Batch Operations**
   ```python
   # Slow: Query state in callback
   @engine.on_tick
   def on_tick(tick, symbol):
       positions = engine.positions()  # Repeated calls

   # Fast: Cache when needed
   positions_cache = []

   @engine.on_bar
   def on_bar(bar, symbol, timeframe):
       nonlocal positions_cache
       positions_cache = engine.positions()  # Cache once per bar
   ```

3. **Use NumPy for Heavy Math**
   ```python
   import numpy as np

   prices = np.array([hqt_core.to_price(bar.close) for bar in bars])
   sma = np.mean(prices[-20:])  # Fast numpy operation
   ```

### Memory Usage

- **Zero-copy**: Reading C++ structures doesn't copy data
- **Callback overhead**: ~200 bytes per registered callback
- **Engine memory**: Same as C++ (no Python overhead)

---

## Examples

### Complete Backtest

```python
import hqt_core

# Create engine
engine = hqt_core.Engine(initial_balance=10000.0, currency="USD", leverage=100)

# Load symbol
symbol = hqt_core.SymbolInfo()
symbol.name("EURUSD")
symbol.symbol_id(1)
symbol.set_point(0.00001)
symbol.set_contract_size(100000.0)
symbol.set_digits(5)
symbol.update_price(1.10000, 1.10015, 0)
engine.load_symbol("EURUSD", symbol)

# Strategy state
sma_fast = []
sma_slow = []

@engine.on_bar
def on_bar(bar, symbol, timeframe):
    if timeframe != hqt_core.Timeframe.M15:
        return

    close = hqt_core.to_price(bar.close)
    sma_fast.append(close)
    sma_slow.append(close)

    # Keep only last N values
    if len(sma_fast) > 20:
        sma_fast.pop(0)
    if len(sma_slow) > 50:
        sma_slow.pop(0)

    # Need enough data
    if len(sma_slow) < 50:
        return

    # Calculate averages
    fast_avg = sum(sma_fast) / len(sma_fast)
    slow_avg = sum(sma_slow) / len(sma_slow)

    # Get current positions
    positions = [p for p in engine.positions() if p.symbol() == "EURUSD"]

    # Trading logic
    if fast_avg > slow_avg and not positions:
        # Buy signal
        engine.buy(volume=0.1, symbol="EURUSD")
    elif fast_avg < slow_avg and positions:
        # Sell signal
        for pos in positions:
            engine.close(pos.ticket())

# Run backtest
print("Starting backtest...")
engine.run()

# Print results
account = engine.account()
print(f"Final balance: {hqt_core.to_price(account.balance()):.2f}")
print(f"Final equity: {hqt_core.to_price(account.equity()):.2f}")
print(f"Total trades: {len(engine.deals())}")
```

### Multi-Symbol Strategy

```python
import hqt_core

engine = hqt_core.Engine()

# Load multiple symbols
for symbol_name in ["EURUSD", "GBPUSD", "USDJPY"]:
    symbol = create_symbol(symbol_name)  # Helper function
    engine.load_symbol(symbol_name, symbol)

# Track state per symbol
symbol_state = {}

@engine.on_bar
def on_bar(bar, symbol, timeframe):
    name = symbol.name()

    if name not in symbol_state:
        symbol_state[name] = {"prices": []}

    close = hqt_core.to_price(bar.close)
    symbol_state[name]["prices"].append(close)

    # Individual strategy logic per symbol
    analyze_and_trade(name, symbol_state[name], engine)

engine.run()
```

---

## Troubleshooting

### Build Issues

**Problem**: `nanobind not found`

```bash
# Solution: Install nanobind
pip install nanobind
```

**Problem**: `Python.h not found`

```bash
# Solution: Install development headers
# Ubuntu/Debian
sudo apt-get install python3-dev

# macOS
brew install python@3.11

# Windows
# Reinstall Python with "Install development files" checked
```

### Runtime Issues

**Problem**: `ImportError: DLL load failed`

```bash
# Solution: Check PATH includes build directory
export PATH=$PATH:build/bridge/Release  # Windows
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:build/bridge  # Linux
```

**Problem**: Segmentation fault

**Possible causes**:
1. Dangling pointer (using object after parent deleted)
2. GIL not held when calling Python
3. Exception in C++ not caught

**Debug**:
```bash
# Build debug version
cmake -B build -DCMAKE_BUILD_TYPE=Debug
gdb python
(gdb) run script.py
```

**Problem**: Slow performance

**Check**:
1. Callbacks doing heavy work?
2. GIL released during run()?
3. Repeated state queries in callbacks?

---

## Conclusion

The Nanobind Bridge provides a high-performance, safe interface between Python and C++. Key takeaways:

- **Use GIL correctly**: Released for long operations, acquired for callbacks
- **Manage lifetimes**: Don't store borrowed references beyond parent lifetime
- **Handle exceptions**: Catch errors in callbacks to prevent crashes
- **Optimize callbacks**: Keep callback work minimal for throughput

For more examples, see `bridge/tests/` and `examples/`.

---

*Document Version: 1.0 | Last Updated: 2026-02-11*
