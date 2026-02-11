# HQT Nanobind Bridge

This directory contains the Python bindings for the HaruQuant Trading System C++ core engine using [nanobind](https://github.com/wjakob/nanobind).

## Overview

The bridge exposes the high-performance C++ backtesting engine to Python, allowing you to:
- Write trading strategies in Python
- Execute backtests at C++ speed (1M+ ticks/sec)
- Access all engine functionality through a Pythonic API
- Use decorator-style callback registration

## Building

### Prerequisites

- Python 3.11+ with development headers
- CMake 3.25+
- C++20 compatible compiler (MSVC 2022, GCC 11+, Clang 14+)

### Build Steps

```bash
# Configure with CMake
cmake -B build -DCMAKE_BUILD_TYPE=Release

# Build the bridge module
cmake --build build --config Release

# The module will be built as:
# Windows: build/bridge/Release/hqt_core.pyd
# Linux:   build/bridge/hqt_core.so
```

### Installation

After building, the module can be imported if the build directory is in your Python path:

```bash
# Add to PYTHONPATH (temporary)
export PYTHONPATH=$PYTHONPATH:build/bridge/Release  # Windows
export PYTHONPATH=$PYTHONPATH:build/bridge          # Linux

# Or install to site-packages
cmake --install build
```

## Usage

### Basic Example

```python
import hqt_core

# Create engine
engine = hqt_core.Engine(initial_balance=10000.0, currency="USD", leverage=100)

# Load symbol
symbol = hqt_core.SymbolInfo()
symbol.name("EURUSD")
symbol.set_point(0.00001)
# ... configure symbol

engine.load_symbol("EURUSD", symbol)

# Register callbacks
@engine.on_bar
def on_bar(bar, symbol, timeframe):
    print(f"Bar closed: {symbol.name()} @ {hqt_core.to_price(bar.close)}")

# Run backtest
engine.run()  # Releases GIL during execution

# Get results
account = engine.account()
print(f"Final balance: {hqt_core.to_price(account.balance())}")
```

### Decorator Style

```python
@engine.on_tick
def on_tick(tick, symbol):
    bid = hqt_core.to_price(tick.bid)
    ask = hqt_core.to_price(tick.ask)
    print(f"{symbol.name()}: {bid}/{ask}")

@engine.on_trade
def on_trade(deal):
    profit = hqt_core.to_price(deal.profit())
    print(f"Trade executed: profit={profit}")
```

### Function Style

```python
def my_tick_handler(tick, symbol):
    # Handle tick
    pass

engine.set_on_tick(my_tick_handler)
```

## Module Structure

### `src/module.cpp`
Main module entry point, defines the `hqt_core` Python module.

### `src/bind_types.cpp`
Bindings for data structures:
- `Tick`, `Bar` (market data)
- `SymbolInfo` (symbol specification)
- `AccountInfo`, `PositionInfo`, `OrderInfo`, `DealInfo` (trading state)
- Enums: `Timeframe`, `PositionType`, `OrderType`, `DealType`

### `src/bind_engine.cpp`
Bindings for the `Engine` class:
- Configuration: `load_symbol()`, `load_conversion_pair()`
- Run control: `run()`, `run_steps()`, `pause()`, `resume()`, `stop()`
- Trading: `buy()`, `sell()`, `modify()`, `close()`, `cancel()`
- State access: `account()`, `positions()`, `orders()`, `deals()`

### `src/bind_callbacks.cpp`
Callback registration with GIL management:
- `set_on_tick()` / `on_tick()`
- `set_on_bar()` / `on_bar()`
- `set_on_trade()` / `on_trade()`
- `set_on_order()` / `on_order()`

### `src/bind_commands.cpp`
Exception handling and helper functions:
- Exception types: `EngineError`, `DataFeedError`, `MmapError`
- Helpers: `to_price()`, `from_price()`, `validate_volume()`, `round_to_tick()`

## Testing

```bash
# Run bridge import tests
pytest bridge/tests/test_bridge_import.py -v
```

## GIL Management

The bridge handles Python's Global Interpreter Lock (GIL) correctly:

- **GIL Released**: `engine.run()`, `engine.run_steps()` release the GIL during long-running C++ execution, allowing other Python threads to run concurrently.

- **GIL Acquired**: Callbacks (`on_tick`, `on_bar`, etc.) automatically acquire the GIL before calling Python code.

This ensures thread safety and allows efficient concurrent execution.

## Performance

- **Zero-copy data access**: C++ structures are exposed directly to Python
- **Minimal overhead**: Nanobind is optimized for low latency
- **Throughput**: 1M+ ticks/sec even with Python callbacks
- **GIL release**: Long-running operations don't block Python interpreter

## Error Handling

C++ exceptions are automatically translated to Python exceptions:

```python
try:
    engine.buy(volume=1000.0, symbol="EURUSD")  # Too large
except hqt_core.EngineError as e:
    print(f"Engine error: {e}")
```

## Lifetime Management

- **Reference counting**: Python objects hold strong references to C++ objects
- **Return policies**: Appropriate `nb::rv_policy` prevents dangling pointers
- **RAII**: C++ resources (file handles, memory maps) are automatically cleaned up

## Documentation

See `docs/bridge.md` for complete API reference and usage guide.

## License

MIT License - see LICENSE file in project root.
