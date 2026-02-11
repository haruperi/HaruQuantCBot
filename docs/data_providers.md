# Data Providers Documentation

## Overview

The HQT Data Provider system enables fetching historical market data from multiple sources through a unified interface. All providers implement the same `DataProvider` abstract base class, making them interchangeable and easy to use.

## Features

- **Unified Interface**: All providers share the same API
- **Multiple Sources**: MetaTrader 5, Dukascopy (more coming soon)
- **Incremental Downloads**: Only fetch new data to avoid re-downloading
- **Progress Callbacks**: Real-time progress updates for UI integration
- **Automatic Retry**: Network failures handled with exponential backoff
- **Context Manager Support**: Automatic resource cleanup

## Quick Start

```python
from hqt.data.providers import get_provider
from hqt.data.models import Timeframe
from datetime import datetime, timedelta

# Create a provider
provider = get_provider("mt5")

# Fetch daily bars
end = datetime.now()
start = end - timedelta(days=365)
bars = provider.fetch_bars(
    symbol="EURUSD",
    timeframe=Timeframe.D1,
    start=start,
    end=end,
)

print(f"Fetched {len(bars)} bars")
```

---

## Available Providers

### MetaTrader 5 (MT5)

Downloads historical data directly from MetaTrader 5 terminal.

**Pros:**
- Official MT5 API
- High data quality
- Supports both bars and ticks
- All timeframes available
- Real-time connection to broker

**Cons:**
- Requires MT5 terminal installed and running
- Must be logged in to broker account
- Windows only (Linux via Wine)
- Limited by broker's historical data depth

**Installation:**

```bash
pip install MetaTrader5
```

**Requirements:**
- MetaTrader 5 terminal installed
- Active MT5 account (demo or live)
- Terminal must be running and logged in

### Dukascopy

Downloads historical tick data from Dukascopy's free public feeds.

**Pros:**
- Free historical tick data
- No account required
- High-quality institutional data
- Deep history (10+ years for major pairs)
- Cross-platform (no MT5 needed)

**Cons:**
- Tick data only (no bars)
- Limited symbols (forex + some CFDs)
- Slower downloads (one file per hour)
- Some hours may be missing

**Installation:**

```bash
pip install requests
```

**Requirements:**
- Internet connection
- No account needed

---

## Provider API Reference

### DataProvider Base Class

All providers inherit from `DataProvider` and implement these methods:

#### `fetch_bars(symbol, timeframe, start, end, progress_callback=None)`

Fetch historical OHLCV bar data.

**Parameters:**
- `symbol` (str): Trading symbol (e.g., "EURUSD", "BTCUSD")
- `timeframe` (Timeframe): Bar timeframe (M1, M5, H1, D1, etc.)
- `start` (datetime): Start datetime (UTC)
- `end` (datetime): End datetime (UTC)
- `progress_callback` (callable, optional): Progress callback function

**Returns:**
- `pd.DataFrame` with columns:
  - `timestamp` (int64): Unix timestamp in microseconds
  - `open` (float64): Open price
  - `high` (float64): High price
  - `low` (float64): Low price
  - `close` (float64): Close price
  - `tick_volume` (int64): Tick volume
  - `real_volume` (int64): Real volume (0 if unavailable)
  - `spread` (int32): Spread in points

**Example:**

```python
from hqt.data.providers import MT5DataProvider
from hqt.data.models import Timeframe
from datetime import datetime

provider = MT5DataProvider()
bars = provider.fetch_bars(
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31),
)
print(f"Fetched {len(bars)} hourly bars")
```

#### `fetch_ticks(symbol, start, end, progress_callback=None)`

Fetch historical tick data.

**Parameters:**
- `symbol` (str): Trading symbol
- `start` (datetime): Start datetime (UTC)
- `end` (datetime): End datetime (UTC)
- `progress_callback` (callable, optional): Progress callback function

**Returns:**
- `pd.DataFrame` with columns:
  - `timestamp` (int64): Unix timestamp in microseconds
  - `bid` (float64): Bid price
  - `ask` (float64): Ask price
  - `bid_volume` (int64): Bid volume (0 if unavailable)
  - `ask_volume` (int64): Ask volume (0 if unavailable)

**Example:**

```python
from hqt.data.providers import DukascopyProvider
from datetime import datetime

provider = DukascopyProvider()
ticks = provider.fetch_ticks(
    symbol="EURUSD",
    start=datetime(2024, 1, 1),
    end=datetime(2024, 1, 2),
)
print(f"Fetched {len(ticks)} ticks")
```

#### `get_available_symbols()`

Get list of symbols available from this provider.

**Returns:**
- `list[str]`: Symbol names

**Example:**

```python
symbols = provider.get_available_symbols()
print(f"Provider offers {len(symbols)} symbols:")
for symbol in symbols[:10]:
    print(f"  - {symbol}")
```

#### `get_available_timeframes(symbol)`

Get list of timeframes available for a symbol.

**Parameters:**
- `symbol` (str): Trading symbol

**Returns:**
- `list[Timeframe]`: Available timeframes

**Example:**

```python
timeframes = provider.get_available_timeframes("EURUSD")
print(f"EURUSD timeframes: {[tf.name for tf in timeframes]}")
```

---

## Usage Examples

### MT5DataProvider

#### Basic Usage

```python
from hqt.data.providers import MT5DataProvider
from hqt.data.models import Timeframe
from datetime import datetime, timedelta

# Create provider
provider = MT5DataProvider()

# Fetch 1 year of daily bars
end = datetime.now()
start = end - timedelta(days=365)
bars = provider.fetch_bars(
    symbol="EURUSD",
    timeframe=Timeframe.D1,
    start=start,
    end=end,
)

print(f"Fetched {len(bars)} daily bars")
print(bars.head())
```

#### With Custom MT5 Configuration

```python
provider = MT5DataProvider(
    path="C:/Program Files/MT5/terminal64.exe",
    login=12345678,
    password="MyPassword",
    server="BrokerServer-Demo",
)
```

#### With Progress Callback

```python
def progress(current, total, eta):
    pct = 100 * current / total
    print(f"\rProgress: {pct:.1f}% (ETA: {eta:.0f}s)", end="")

bars = provider.fetch_bars(
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    start=start,
    end=end,
    progress_callback=progress,
)
print()  # New line after progress
```

#### Context Manager (Recommended)

```python
# Automatically closes connection when done
with MT5DataProvider() as provider:
    bars = provider.fetch_bars("EURUSD", Timeframe.D1, start, end)
    ticks = provider.fetch_ticks("EURUSD", start, end)
# Connection automatically closed
```

#### Fetch Multiple Symbols

```python
symbols = ["EURUSD", "GBPUSD", "USDJPY"]
all_bars = {}

with MT5DataProvider() as provider:
    for symbol in symbols:
        bars = provider.fetch_bars(
            symbol=symbol,
            timeframe=Timeframe.D1,
            start=start,
            end=end,
        )
        all_bars[symbol] = bars
        print(f"{symbol}: {len(bars)} bars")
```

### DukascopyProvider

#### Basic Usage

```python
from hqt.data.providers import DukascopyProvider
from datetime import datetime, timedelta

# Create provider
provider = DukascopyProvider()

# Fetch 7 days of tick data
end = datetime.now()
start = end - timedelta(days=7)
ticks = provider.fetch_ticks(
    symbol="EURUSD",
    start=start,
    end=end,
)

print(f"Fetched {len(ticks)} ticks")
print(ticks.head())
```

#### With Custom Timeout and Retries

```python
provider = DukascopyProvider(
    timeout=60,      # 60 seconds timeout
    max_retries=5,   # 5 retry attempts
)
```

#### With Progress Callback

```python
def progress(current, total, eta):
    pct = 100 * current / total
    bar_width = 50
    filled = int(bar_width * current / total)
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"\r[{bar}] {pct:.1f}% ({current}/{total} hours, ETA: {eta:.0f}s)", end="")

ticks = provider.fetch_ticks(
    symbol="EURUSD",
    start=start,
    end=end,
    progress_callback=progress,
)
print()  # New line
```

#### Resample Ticks to Bars

```python
# Fetch ticks
ticks = provider.fetch_ticks("EURUSD", start, end)

# Convert timestamp to datetime index
ticks['datetime'] = pd.to_datetime(ticks['timestamp'], unit='us')
ticks = ticks.set_index('datetime')

# Resample to 1-hour bars
bars_1h = ticks['bid'].resample('1H').ohlc()
bars_1h['volume'] = ticks['bid_volume'].resample('1H').sum()

print(f"Resampled {len(ticks)} ticks to {len(bars_1h)} hourly bars")
```

---

## Provider Factory

### get_provider()

Create providers by name without importing specific classes.

```python
from hqt.data.providers import get_provider

# Create MT5 provider
mt5 = get_provider("mt5")

# Create MT5 provider with config
mt5 = get_provider(
    "mt5",
    login=12345,
    password="secret",
    server="BrokerServer-Demo",
)

# Create Dukascopy provider
duka = get_provider("dukascopy", timeout=60, max_retries=5)
```

### get_available_providers()

Get metadata about available providers.

```python
from hqt.data.providers import get_available_providers

providers = get_available_providers()
for name, info in providers.items():
    print(f"\n{info['name']}:")
    print(f"  Description: {info['description']}")
    print(f"  Supports bars: {info['supports_bars']}")
    print(f"  Supports ticks: {info['supports_ticks']}")
    print(f"  Incremental: {info['supports_incremental']}")
    print(f"  Config params: {', '.join(info['config_params'])}")
```

### download_with_progress()

Convenience function with automatic progress display.

```python
from hqt.data.providers import get_provider, download_with_progress
from hqt.data.models import Timeframe
from datetime import datetime, timedelta

provider = get_provider("mt5")
end = datetime.now()
start = end - timedelta(days=365)

# Progress bar automatically displayed
bars = download_with_progress(
    provider,
    symbol="EURUSD",
    start=start,
    end=end,
    fetch_type="bars",
    timeframe=Timeframe.D1,
)
```

---

## Progress Callbacks

Progress callbacks enable UI integration and allow tracking download progress.

### Callback Signature

```python
def progress_callback(current: int, total: int, eta_seconds: float) -> None:
    """
    Args:
        current: Current progress (e.g., bars downloaded, hours processed)
        total: Total items to download
        eta_seconds: Estimated time remaining in seconds
    """
    pass
```

### Examples

#### Simple Percentage Display

```python
def progress(current, total, eta):
    if total > 0:
        pct = 100 * current / total
        print(f"\rProgress: {pct:.1f}%", end="")
```

#### Progress Bar

```python
def progress_bar(current, total, eta):
    if total > 0:
        pct = 100 * current / total
        bar_width = 40
        filled = int(bar_width * current / total)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"\r[{bar}] {pct:.1f}% (ETA: {eta:.0f}s)", end="")
        if current == total:
            print()  # New line when complete
```

#### Rich Progress Bar (requires `rich` package)

```python
from rich.progress import Progress

with Progress() as progress_ui:
    task = progress_ui.add_task("[cyan]Downloading...", total=100)

    def progress(current, total, eta):
        progress_ui.update(task, completed=current)

    bars = provider.fetch_bars(
        symbol="EURUSD",
        timeframe=Timeframe.D1,
        start=start,
        end=end,
        progress_callback=progress,
    )
```

---

## Incremental Downloads

Both providers support incremental downloads - only fetching data newer than what you already have.

### How It Works

1. Determine latest timestamp in your stored data
2. Set `start` parameter to latest timestamp
3. Provider only downloads new data

### Example

```python
from hqt.data.providers import MT5DataProvider
from hqt.data.models import Timeframe
from datetime import datetime
import pandas as pd

provider = MT5DataProvider()

# Initial download
bars = provider.fetch_bars(
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 6, 30),
)
bars.to_parquet("eurusd_h1.parquet")
print(f"Initial: {len(bars)} bars")

# Later: incremental update
existing = pd.read_parquet("eurusd_h1.parquet")
last_timestamp = existing['timestamp'].max()
last_datetime = pd.to_datetime(last_timestamp, unit='us')

new_bars = provider.fetch_bars(
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    start=last_datetime,
    end=datetime.now(),
)

# Append new bars
updated = pd.concat([existing, new_bars]).drop_duplicates('timestamp')
updated.to_parquet("eurusd_h1.parquet")
print(f"Added {len(new_bars)} new bars")
```

---

## Retry Logic

Network operations can fail. The providers include automatic retry with exponential backoff.

### Built-in Retry

Dukascopy provider has built-in retry logic:

```python
# Retries up to 3 times with exponential backoff
provider = DukascopyProvider(max_retries=3)
```

### Custom Retry Decorator

For custom network operations:

```python
from hqt.data.providers import with_retry
import requests

@with_retry(
    max_retries=5,
    initial_delay=1.0,
    max_delay=30.0,
    backoff_factor=2.0,
)
def fetch_custom_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

# Automatically retries on failure
data = fetch_custom_data("https://api.example.com/data")
```

### Retry Parameters

- `max_retries`: Maximum retry attempts (default: 3)
- `initial_delay`: Initial delay in seconds (default: 0.5)
- `max_delay`: Maximum delay in seconds (default: 30.0)
- `backoff_factor`: Exponential multiplier (default: 2.0)

Delay sequence example:
- Attempt 1: immediate
- Attempt 2: wait 0.5s
- Attempt 3: wait 1.0s
- Attempt 4: wait 2.0s

---

## Best Practices

### 1. Use Context Managers

```python
# Good - automatic cleanup
with MT5DataProvider() as provider:
    bars = provider.fetch_bars(...)

# Avoid - manual cleanup required
provider = MT5DataProvider()
bars = provider.fetch_bars(...)
provider.close()
```

### 2. Handle Missing Data

```python
try:
    bars = provider.fetch_bars("EURUSD", Timeframe.D1, start, end)
    if len(bars) == 0:
        print("No data available for this period")
except ValueError as e:
    print(f"Invalid symbol or timeframe: {e}")
except ConnectionError as e:
    print(f"Connection failed: {e}")
```

### 3. Download in Chunks for Large Ranges

```python
from datetime import timedelta

def download_in_chunks(provider, symbol, timeframe, start, end, chunk_days=30):
    """Download large date range in smaller chunks."""
    all_bars = []
    current = start

    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days), end)
        bars = provider.fetch_bars(symbol, timeframe, current, chunk_end)
        all_bars.append(bars)
        current = chunk_end

    return pd.concat(all_bars, ignore_index=True)
```

### 4. Cache Downloaded Data

```python
from pathlib import Path

def get_cached_bars(symbol, timeframe, start, end):
    """Load from cache or download if missing."""
    cache_file = Path(f"cache/{symbol}_{timeframe.name}.parquet")

    if cache_file.exists():
        return pd.read_parquet(cache_file)

    with MT5DataProvider() as provider:
        bars = provider.fetch_bars(symbol, timeframe, start, end)

    cache_file.parent.mkdir(exist_ok=True)
    bars.to_parquet(cache_file)
    return bars
```

### 5. Validate Downloaded Data

```python
from hqt.data.validation import ValidationPipeline

# Download data
bars = provider.fetch_bars("EURUSD", Timeframe.H1, start, end)

# Validate before using
pipeline = ValidationPipeline()
report = pipeline.validate_bars(bars, "EURUSD")

if report.has_critical_issues():
    print("Critical issues found:")
    print(report.to_dataframe())
else:
    print("Data quality OK")
```

---

## Troubleshooting

### MT5 Provider

**Problem:** "Failed to initialize MT5"

**Solutions:**
- Ensure MT5 terminal is installed and running
- Check MT5 terminal is logged in to account
- Try specifying full path to terminal executable:
  ```python
  MT5DataProvider(path="C:/Program Files/MT5/terminal64.exe")
  ```

**Problem:** "Symbol not found"

**Solutions:**
- Check symbol name spelling (case-sensitive)
- Ensure symbol is visible in MT5 Market Watch
- Try adding symbol to Market Watch manually in MT5

**Problem:** Empty result but no error

**Solutions:**
- Broker may not have data for requested period
- Try shorter date range
- Check symbol has historical data in MT5

### Dukascopy Provider

**Problem:** "Failed to download" errors

**Solutions:**
- Check internet connection
- Some hours may be missing (weekends, holidays) - this is normal
- Increase timeout: `DukascopyProvider(timeout=60)`
- Increase retries: `DukascopyProvider(max_retries=5)`

**Problem:** "Symbol not supported"

**Solutions:**
- Check available symbols:
  ```python
  provider.get_available_symbols()
  ```
- Dukascopy only supports forex and some CFDs
- Use MT5 provider for other instruments

**Problem:** Slow downloads

**Solutions:**
- Dukascopy downloads one file per hour - large ranges take time
- Download smaller date ranges
- Use multiprocessing for parallel downloads (advanced)

### General

**Problem:** Memory errors with large datasets

**Solutions:**
- Download in smaller chunks
- Use generators for processing
- Save to disk incrementally:
  ```python
  for chunk in download_chunks():
      chunk.to_parquet(f"data_{i}.parquet")
  ```

**Problem:** Timezone issues

**Solutions:**
- Always use UTC for start/end datetimes
- Convert timezone-aware datetimes to UTC:
  ```python
  from datetime import timezone
  dt_utc = dt_local.astimezone(timezone.utc)
  ```

---

## Performance Tips

### MT5 Provider

- Fetching bars is very fast (< 1 second for years of data)
- Tick downloads can be slow for large ranges
- Connection overhead minimal - reuse provider instance

### Dukascopy Provider

- Downloads one HTTP request per hour
- Use progress callbacks for long downloads
- Consider caching downloaded data
- Parallel downloads possible with multiprocessing

### Optimal Download Sizes

| Provider | Data Type | Recommended Range |
|----------|-----------|-------------------|
| MT5 | Bars (M1-H1) | Up to 1 year |
| MT5 | Bars (H4-D1) | Unlimited |
| MT5 | Ticks | Up to 1 week |
| Dukascopy | Ticks | Up to 1 month |

---

## API Reference Summary

| Method | MT5 | Dukascopy | Returns |
|--------|-----|-----------|---------|
| `fetch_bars()` | ✅ | ❌ | DataFrame |
| `fetch_ticks()` | ✅ | ✅ | DataFrame |
| `get_available_symbols()` | ✅ | ✅ | list[str] |
| `get_available_timeframes()` | ✅ | ❌ | list[Timeframe] |
| `supports_incremental_download()` | ✅ | ✅ | bool |
| `close()` | ✅ | ✅ | None |

---

## See Also

- [Data Models Documentation](data_models.md) - Tick, Bar, SymbolSpecification
- [Data Validation Documentation](data_validation.md) - Quality checks and cleaning
- [Configuration Documentation](configuration.md) - Provider configuration
