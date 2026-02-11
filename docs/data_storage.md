# Data Storage Documentation

## Overview

The HQT Data Storage Layer provides efficient persistent storage for tick and bar data with multiple backend options, metadata catalog, and automated management. The system uses columnar storage formats optimized for time-series data with memory-mapped access support for C++.

## Features

- **Multiple Backends**: Apache Parquet (recommended) and HDF5
- **Columnar Access**: Read only needed columns without loading full records
- **Predicate Pushdown**: Filter data at read time for efficiency
- **Fixed-Point Precision**: INT64 encoding for exact price representation (6 decimals)
- **Automatic Partitioning**: Monthly for ticks, yearly for intraday bars
- **Metadata Catalog**: SQLite-based tracking of all stored data
- **Data Compaction**: Merge incremental downloads into optimized files
- **Version Tracking**: SHA-256 content hashes for reproducibility

## Quick Start

```python
from hqt.data.storage import ParquetStore, DataCatalog, StorageManager
from hqt.data.providers import MT5DataProvider
from hqt.data.models import Timeframe
from datetime import datetime, timedelta

# Initialize storage
store = ParquetStore("data/parquet")
catalog = DataCatalog("data/catalog.db")
manager = StorageManager(store, catalog)

# Download and store with full pipeline
provider = MT5DataProvider()
end = datetime.now()
start = end - timedelta(days=30)

result = manager.download_and_store(
    provider=provider,
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    start=start,
    end=end,
    validate=True,  # Run validation
)

print(f"Stored {result['total_rows']} rows in {len(result['partitions'])} partitions")

# Read data back
bars = manager.read_bars(
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31),
)
```

---

## Storage Backends

### Apache Parquet (Recommended)

High-performance columnar storage using PyArrow.

**Pros:**
- Excellent compression (DELTA_BINARY_PACKED for prices)
- Very fast columnar reads
- Wide ecosystem support
- Memory-mapped access for C++
- Standard format (portable across tools)

**Cons:**
- Slightly larger files than HDF5
- Write-once (updates require rewrite)

**Example:**

```python
from hqt.data.storage import ParquetStore
from hqt.data.models import Timeframe
import pandas as pd

store = ParquetStore("data/parquet")

# Write bars
bars = pd.DataFrame({
    'timestamp': [...],
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'tick_volume': [...],
    'real_volume': [...],
    'spread': [...],
})

store.write_bars("EURUSD", Timeframe.H1, bars, partition="2024")

# Read all columns
all_bars = store.read_bars("EURUSD", Timeframe.H1)

# Read only close prices (columnar access)
closes = store.read_bars(
    "EURUSD",
    Timeframe.H1,
    columns=["timestamp", "close"],
)

# Read time range (predicate pushdown)
q1_bars = store.read_bars(
    "EURUSD",
    Timeframe.H1,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 3, 31),
)
```

### HDF5

Hierarchical Data Format using h5py.

**Pros:**
- Better compression ratios
- Native chunked storage
- Direct memory-mapped access
- Established scientific computing format

**Cons:**
- Slower than Parquet for columnar reads
- Less widespread tooling

**Example:**

```python
from hqt.data.storage import HDF5Store

store = HDF5Store("data/hdf5")

# Same API as ParquetStore
store.write_bars("EURUSD", Timeframe.H1, bars, partition="2024")
bars = store.read_bars("EURUSD", Timeframe.H1)
```

### Choosing a Backend

| Use Case | Recommended Backend |
|----------|---------------------|
| General use | Parquet |
| C++ memory-mapped access | Parquet or HDF5 |
| Maximum compression | HDF5 |
| Interoperability | Parquet |
| Large datasets (>10GB) | Parquet |

---

## File Organization

### Directory Structure

```
data/
├── parquet/                    # Parquet backend
│   ├── EURUSD/
│   │   ├── ticks/
│   │   │   ├── 2024-01.parquet  # Monthly (ticks)
│   │   │   ├── 2024-02.parquet
│   │   │   └── 2024-03.parquet
│   │   ├── M1/
│   │   │   ├── 2024.parquet     # Yearly (M1)
│   │   │   └── 2025.parquet
│   │   ├── H1/
│   │   │   └── 2024.parquet     # Yearly (H1)
│   │   └── D1/
│   │       └── all.parquet      # Single file (D1+)
│   ├── GBPUSD/
│   │   └── ...
│   └── XAUUSD/
│       └── ...
├── hdf5/                       # HDF5 backend (same structure)
│   └── ...
└── catalog.db                  # SQLite metadata catalog
```

### Partitioning Strategy

Data is automatically partitioned based on timeframe:

| Timeframe | Partition Size | Example |
|-----------|---------------|---------|
| Ticks | Monthly | 2024-01, 2024-02, ... |
| M1-M30 | Yearly | 2024, 2025, ... |
| H1-H12 | Yearly | 2024, 2025, ... |
| D1+ | Single file | all |

**Rationale:**
- Ticks: ~1-2M rows/month → monthly partitions prevent huge files
- M1: ~525K rows/year → yearly manageable
- H1: ~8.7K rows/year → yearly optimal
- D1: ~250 rows/year → single file efficient

---

## Data Catalog

SQLite-based metadata tracking for all stored data.

### Schema

```sql
CREATE TABLE catalog (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT,           -- NULL for ticks
    partition TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    storage_format TEXT NOT NULL,  -- 'parquet' or 'hdf5'
    row_count INTEGER NOT NULL,
    min_timestamp INTEGER NOT NULL,
    max_timestamp INTEGER NOT NULL,
    data_source TEXT,         -- 'mt5', 'dukascopy', etc.
    download_timestamp INTEGER NOT NULL,
    version_hash TEXT,        -- SHA-256 content hash
    file_size_bytes INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
```

### Usage

```python
from hqt.data.storage import DataCatalog
from hqt.data.models import Timeframe

catalog = DataCatalog("data/catalog.db")

# Query available data
entries = catalog.query_available(
    symbol="EURUSD",
    timeframe=Timeframe.H1,
)

for entry in entries:
    print(f"Partition: {entry['partition']}")
    print(f"Rows: {entry['row_count']}")
    print(f"Date range: {entry['min_timestamp']} to {entry['max_timestamp']}")

# Get specific file metadata
metadata = catalog.get_metadata("EURUSD", Timeframe.H1, "2024")
print(f"File: {metadata['file_path']}")
print(f"Source: {metadata['data_source']}")
print(f"Hash: {metadata['version_hash']}")

# List symbols
symbols = catalog.list_symbols()
print(f"Stored symbols: {symbols}")

# Get statistics
stats = catalog.get_stats()
print(f"Total entries: {stats['total_entries']}")
print(f"Total rows: {stats['total_rows']}")
print(f"Total size: {stats['total_size_bytes'] / 1024 / 1024:.1f} MB")
```

---

## Storage Manager

Orchestrates the complete data pipeline: download → validate → store → catalog.

### Full Pipeline

```python
from hqt.data.storage import ParquetStore, DataCatalog, StorageManager
from hqt.data.providers import get_provider
from hqt.data.models import Timeframe
from datetime import datetime, timedelta

# Initialize
store = ParquetStore("data/parquet")
catalog = DataCatalog("data/catalog.db")
manager = StorageManager(store, catalog)

# Download and store
provider = get_provider("mt5")
end = datetime.now()
start = end - timedelta(days=365)

def progress(current, total, eta):
    pct = 100 * current / total
    print(f"\rProgress: {pct:.1f}% (ETA: {eta:.0f}s)", end="")

result = manager.download_and_store(
    provider=provider,
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    start=start,
    end=end,
    validate=True,             # Run validation pipeline
    validate_critical_only=True,  # Only fail on critical issues
    data_source="mt5",         # Track source
    progress_callback=progress,
)

print(f"\nStored {result['total_rows']} rows")
print(f"Partitions: {result['partitions']}")
print(f"Version hash: {result['version_hash']}")

# Validation report
if result['validation_report']:
    report = result['validation_report']
    print(f"Validation: {report.total_issues} issues")
```

### Data Compaction

Merge incremental downloads into optimized files.

```python
# After multiple incremental downloads
result = manager.compact(
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    partition="2024",
)

print(f"Compacted {result['files_merged']} files")
print(f"Rows: {result['rows_before']} → {result['rows_after']}")
```

### Reading Data

```python
# Read bars
bars = manager.read_bars(
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31),
    columns=["timestamp", "close"],  # Optional: columnar access
)

# Read ticks
ticks = manager.read_ticks(
    symbol="EURUSD",
    start=datetime(2024, 1, 1),
    end=datetime(2024, 1, 2),
)
```

### Deleting Data

```python
# Delete specific partition
manager.delete(
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    partition="2024",
)

# Delete all H1 data
manager.delete(
    symbol="EURUSD",
    timeframe=Timeframe.H1,
)

# Delete all data for symbol
manager.delete(symbol="EURUSD")
```

---

## Price Precision

All prices are stored as **INT64 with 6 decimal places** for exact precision.

```python
# Storage: multiply by 1,000,000
stored_price = int(1.23456 * 1_000_000)  # 1234560

# Retrieval: divide by 1,000,000
actual_price = stored_price / 1_000_000  # 1.23456
```

**Why fixed-point?**
- Avoids floating-point rounding errors
- Exact representation for forex (5 decimals) and metals (3 decimals)
- Efficient DELTA encoding in Parquet
- Compatible with C++ integer arithmetic

**Examples:**

| Value | Float64 | INT64 (×1M) | Error |
|-------|---------|-------------|-------|
| 1.23456 | 1.234560000000001 | 1234560 | 0 |
| 0.00001 | 0.000009999... | 10 | 0 |
| 1234.567 | 1234.567 | 1234567000 | 0 |

---

## Best Practices

### 1. Use StorageManager

```python
# Good - Complete pipeline
manager = StorageManager(store, catalog)
manager.download_and_store(provider, ...)

# Avoid - Manual steps
data = provider.fetch_bars(...)
store.write_bars(...)
catalog.register_file(...)
```

### 2. Enable Validation

```python
# Always validate new data
result = manager.download_and_store(
    ...,
    validate=True,
    validate_critical_only=True,  # Don't fail on warnings
)
```

### 3. Regular Compaction

```python
# Compact after multiple incremental downloads
manager.compact(symbol, timeframe, partition)
```

### 4. Use Columnar Access

```python
# Good - Only load needed columns
closes = store.read_bars("EURUSD", Timeframe.H1, columns=["timestamp", "close"])

# Avoid - Loading all columns when only needing one
bars = store.read_bars("EURUSD", Timeframe.H1)
closes = bars[["timestamp", "close"]]
```

### 5. Leverage Predicate Pushdown

```python
# Good - Filter at read time
bars = store.read_bars(
    "EURUSD",
    Timeframe.H1,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31),
)

# Avoid - Load all then filter
bars = store.read_bars("EURUSD", Timeframe.H1)
bars = bars[(bars['timestamp'] >= start_ts) & (bars['timestamp'] < end_ts)]
```

### 6. Check Catalog Before Downloading

```python
# Check what's already stored
entries = catalog.query_available(symbol="EURUSD", timeframe=Timeframe.H1)
if entries:
    latest = max(e['max_timestamp'] for e in entries)
    start = datetime.fromtimestamp(latest / 1_000_000)
    # Download only new data
```

---

## Performance Tips

### Read Performance

**Columnar Access:**
```python
# Fast - Only reads timestamp + close columns
closes = store.read_bars("EURUSD", Timeframe.H1, columns=["timestamp", "close"])

# Slow - Reads all 8 columns
bars = store.read_bars("EURUSD", Timeframe.H1)
```

**Predicate Pushdown:**
```python
# Fast - Filters during read
bars = store.read_bars("EURUSD", Timeframe.H1, start=..., end=...)

# Slow - Loads all then filters in Python
bars = store.read_bars("EURUSD", Timeframe.H1)
bars = bars[mask]
```

### Write Performance

**Batch Writes:**
```python
# Good - Single write per partition
store.write_bars("EURUSD", Timeframe.H1, all_2024_data, partition="2024")

# Avoid - Many small writes
for month_data in monthly_chunks:
    store.write_bars(...)  # Rewrites file each time
```

### Storage Size

**Compression:**
```python
# Parquet with Snappy: 3-5x compression
# HDF5 with GZIP: 5-8x compression

# Typical sizes (EURUSD H1, 1 year):
# Raw CSV: ~2.5 MB
# Parquet: ~600 KB
# HDF5: ~400 KB
```

---

## Troubleshooting

### Problem: "Missing required columns"

**Solution:**
Ensure DataFrame has all required columns before writing.

```python
# Bars require:
required = ['timestamp', 'open', 'high', 'low', 'close', 'tick_volume', 'real_volume', 'spread']

# Ticks require:
required = ['timestamp', 'bid', 'ask', 'bid_volume', 'ask_volume']

# Check before writing
missing = set(required) - set(df.columns)
if missing:
    print(f"Missing columns: {missing}")
```

### Problem: "Cannot write empty DataFrame"

**Solution:**
Check data before writing.

```python
if len(df) > 0:
    store.write_bars(...)
else:
    print("No data to write")
```

### Problem: "File not found" when reading

**Solution:**
Check catalog to see what's available.

```python
# Check available data
entries = catalog.query_available(symbol="EURUSD")
if not entries:
    print("No data stored for EURUSD")
```

### Problem: "Chunk shape must not be greater than data shape" (HDF5)

**Solution:**
Fixed in HDF5Store - now uses dynamic chunk sizing.

```python
# Old (failed for small datasets):
chunks=(CHUNK_SIZE,)

# New (works for any size):
chunk_size = min(len(array), CHUNK_SIZE)
chunks=(chunk_size,) if chunk_size > 0 else None
```

### Problem: Large file sizes

**Solution:**
1. Use compaction to remove duplicates
2. Consider HDF5 for better compression
3. Archive old partitions

```python
# Compact to remove duplicates
manager.compact(symbol, timeframe, partition)

# Check file sizes
info = store.get_file_info(symbol, timeframe, partition)
print(f"File size: {info['size_bytes'] / 1024 / 1024:.1f} MB")
```

---

## API Reference Summary

### ParquetStore / HDF5Store

| Method | Description |
|--------|-------------|
| `write_bars(symbol, timeframe, data, partition)` | Write bar data |
| `write_ticks(symbol, data, partition)` | Write tick data |
| `read_bars(symbol, timeframe, start, end, columns, partition)` | Read bars |
| `read_ticks(symbol, start, end, columns, partition)` | Read ticks |
| `list_symbols()` | List all symbols |
| `list_timeframes(symbol)` | List timeframes for symbol |
| `list_partitions(symbol, timeframe)` | List partitions |
| `delete_data(symbol, timeframe, partition)` | Delete data |
| `get_file_info(symbol, timeframe, partition)` | Get file metadata |

### DataCatalog

| Method | Description |
|--------|-------------|
| `register_file(...)` | Register file in catalog |
| `query_available(symbol, timeframe, start, end, format)` | Query catalog |
| `get_metadata(symbol, timeframe, partition)` | Get entry metadata |
| `get_file_path(symbol, timeframe, partition)` | Get file path |
| `list_symbols()` | List symbols |
| `list_timeframes(symbol)` | List timeframes |
| `list_partitions(symbol, timeframe)` | List partitions |
| `delete_entry(symbol, timeframe, partition)` | Delete catalog entry |
| `get_stats()` | Get catalog statistics |

### StorageManager

| Method | Description |
|--------|-------------|
| `download_and_store(provider, symbol, ...)` | Full pipeline |
| `compact(symbol, timeframe, partition)` | Compact data |
| `read_bars(symbol, timeframe, start, end, columns)` | Read bars |
| `read_ticks(symbol, start, end, columns)` | Read ticks |
| `delete(symbol, timeframe, partition)` | Delete data |
| `get_stats()` | Get statistics |

---

## See Also

- [Data Models Documentation](data_models.md) - Tick, Bar, dtypes
- [Data Validation Documentation](data_validation.md) - Quality checks
- [Data Providers Documentation](data_providers.md) - MT5, Dukascopy
