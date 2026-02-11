# Data Versioning & Lineage Documentation

## Overview

The HQT Data Versioning system provides reproducibility and auditability for backtests through content hashing, lineage tracking, and manifest generation. Every backtest records exactly which data versions were used, enabling exact reproduction of results.

## Features

- **Content Hashing**: SHA-256 hashes for all data files
- **Lineage Tracking**: Record what data was used in each backtest
- **Reproducibility Verification**: Check if a backtest can be exactly reproduced
- **Manifest Generation**: version manifest.json with all data hashes
- **Data Integrity**: Detect if data files have been modified
- **Impact Analysis**: Find all backtests using a specific data version

## Quick Start

```python
from hqt.data.versioning import DataLineage, DataManifest, compute_file_hash
from hqt.data.storage import DataCatalog

# 1. Hash computation is automatic in StorageManager
# But you can also compute manually
hash_value = compute_file_hash("data/parquet/EURUSD/H1/2024.parquet")
print(f"Data version: {hash_value}")

# 2. Record backtest lineage
lineage = DataLineage("data/lineage.db")
lineage.record_backtest_lineage(
    backtest_id=123,
    data_files=[
        {
            "file_path": "data/parquet/EURUSD/H1/2024.parquet",
            "version_hash": hash_value,
            "symbol": "EURUSD",
            "timeframe": "H1",
            "partition": "2024",
        }
    ],
)

# 3. Verify reproducibility
result = lineage.can_reproduce(backtest_id=123)
if result["reproducible"]:
    print("✓ Backtest can be exactly reproduced")
else:
    print(f"✗ Cannot reproduce: {result['issues']}")

# 4. Generate manifest
catalog = DataCatalog("data/catalog.db")
manifest = DataManifest(catalog)
manifest.generate("data/manifest.json")
```

---

## Content Hashing

### Hash Computation

SHA-256 hashes uniquely identify data file versions.

```python
from hqt.data.versioning import (
    compute_hash,
    compute_file_hash,
    compute_dataframe_hash,
    compute_hash_incremental,
)

# Hash bytes
data = b"Hello, World!"
hash_value = compute_hash(data)

# Hash file
hash_value = compute_file_hash("data.parquet")

# Hash DataFrame (uses timestamp + close/ask as signature)
import pandas as pd
bars = pd.DataFrame({...})
hash_value = compute_dataframe_hash(bars)

# Hash multiple files (combined)
files = ["file1.parquet", "file2.parquet"]
combined_hash = compute_hash_incremental(files)
```

### Hash Verification

```python
from hqt.data.versioning import verify_file_hash

# Record hash
original_hash = compute_file_hash("data.parquet")

# Later, verify file hasn't changed
is_valid = verify_file_hash("data.parquet", original_hash)
if not is_valid:
    print("Warning: Data file has been modified!")
```

---

## Data Lineage

### Recording Lineage

Track which data files were used in each backtest.

```python
from hqt.data.versioning import DataLineage

lineage = DataLineage("data/lineage.db")

# Record data used in backtest
lineage.record_backtest_lineage(
    backtest_id=123,
    data_files=[
        {
            "file_path": "data/parquet/EURUSD/H1/2024.parquet",
            "version_hash": "abc123...",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "partition": "2024",
        },
        {
            "file_path": "data/parquet/GBPUSD/H1/2024.parquet",
            "version_hash": "def456...",
            "symbol": "GBPUSD",
            "timeframe": "H1",
            "partition": "2024",
        },
    ],
)
```

### Retrieving Lineage

```python
# Get lineage for a backtest
lineage_info = lineage.get_lineage(backtest_id=123)

print(f"Backtest {lineage_info['backtest_id']}")
print(f"Used {lineage_info['total_files']} data files:")
for f in lineage_info['data_files']:
    print(f"  - {f['symbol']} {f['timeframe']} {f['partition']}")
    print(f"    Hash: {f['version_hash']}")
    print(f"    File: {f['data_file_path']}")
```

### Reproducibility Verification

```python
# Check if backtest can be reproduced
result = lineage.can_reproduce(backtest_id=123)

if result["reproducible"]:
    print(f"✓ Backtest can be reproduced")
    print(f"  Verified {result['verified_files']}/{result['total_files']} files")
else:
    print(f"✗ Cannot reproduce backtest:")
    for issue in result["issues"]:
        print(f"  - {issue}")
```

**Checks performed:**
1. All data files exist
2. File hashes match recorded hashes (data unchanged)

**Example output (success):**
```
✓ Backtest can be reproduced
  Verified 2/2 files
```

**Example output (failure):**
```
✗ Cannot reproduce backtest:
  - Missing file: data/parquet/EURUSD/H1/2024.parquet (EURUSD H1 2024)
  - Hash mismatch: data/parquet/GBPUSD/H1/2024.parquet (GBPUSD H1 2024) - data has been modified
```

### Impact Analysis

Find all backtests using a specific data version.

```python
# Which backtests used this data file?
backtests = lineage.find_backtests_using_data(
    version_hash="abc123..."
)
print(f"Data used in {len(backtests)} backtests: {backtests}")
```

**Use case:** When data is updated, identify which backtests need re-running.

---

## Manifest Generation

### Generate Manifest

Create manifest.json with all data versions.

```python
from hqt.data.versioning import DataManifest
from hqt.data.storage import DataCatalog

catalog = DataCatalog("data/catalog.db")
manifest = DataManifest(catalog)

# Generate manifest
result = manifest.generate("data/manifest.json")
print(f"Generated manifest:")
print(f"  Files: {result['total_files']}")
print(f"  Total size: {result['total_size_bytes'] / 1024 / 1024:.1f} MB")
```

**Manifest format:**
```json
{
  "generated_at": "2024-01-15T10:30:00Z",
  "hqt_version": "1.0.0",
  "total_files": 42,
  "total_size_bytes": 1234567890,
  "files": [
    {
      "symbol": "EURUSD",
      "timeframe": "H1",
      "partition": "2024",
      "file_path": "data/parquet/EURUSD/H1/2024.parquet",
      "version_hash": "abc123...",
      "row_count": 8760,
      "min_timestamp": 1704067200000000,
      "max_timestamp": 1735689599000000,
      "file_size_bytes": 524288,
      "data_source": "mt5"
    }
  ]
}
```

### Verify Manifest

Check data integrity against manifest.

```python
# Verify all files match manifest
result = manifest.verify(
    "data/manifest.json",
    check_hashes=True,  # Verify hashes (slow for many files)
)

if result["valid"]:
    print(f"✓ All {result['total_files']} files verified")
else:
    print(f"✗ Verification failed:")
    for issue in result["issues"]:
        print(f"  - {issue}")
```

### Update Manifest

Incrementally update manifest with new files.

```python
# After downloading new data
result = manifest.update("data/manifest.json")
print(f"Manifest updated:")
print(f"  Added: {result['added']} new files")
print(f"  Updated: {result['updated']} existing files")
print(f"  Total: {result['total_files']} files")
```

### Compare Manifests

Find differences between two manifests.

```python
# Compare old and new manifests
diff = manifest.diff(
    "data/manifest_2024-01.json",
    "data/manifest_2024-02.json"
)

print(f"Changes:")
print(f"  Added: {len(diff['added'])} files")
print(f"  Removed: {len(diff['removed'])} files")
print(f"  Modified: {len(diff['modified'])} files")
print(f"  Unchanged: {diff['unchanged']} files")

# Show modified files
for item in diff['modified']:
    print(f"  Modified: {item['file']['symbol']} {item['file']['timeframe']}")
    print(f"    Old hash: {item['old_hash']}")
    print(f"    New hash: {item['new_hash']}")
```

---

## Integration with Storage

### Automatic Hashing

StorageManager automatically computes hashes when storing data.

```python
from hqt.data.storage import StorageManager, ParquetStore, DataCatalog

store = ParquetStore("data/parquet")
catalog = DataCatalog("data/catalog.db")
manager = StorageManager(store, catalog)

# Download and store - hashes computed automatically
result = manager.download_and_store(
    provider=provider,
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    start=start,
    end=end,
)

# Hash is stored in catalog and returned
print(f"Data version: {result['version_hash']}")
```

### Catalog Integration

Data catalog stores version hashes for all files.

```python
from hqt.data.storage import DataCatalog

catalog = DataCatalog("data/catalog.db")

# Get metadata (includes hash)
metadata = catalog.get_metadata("EURUSD", Timeframe.H1, "2024")
print(f"File: {metadata['file_path']}")
print(f"Hash: {metadata['version_hash']}")
print(f"Rows: {metadata['row_count']}")
```

---

## Workflow Examples

### Complete Backtest Lineage Workflow

```python
from hqt.data.storage import StorageManager, ParquetStore, DataCatalog
from hqt.data.versioning import DataLineage
from hqt.data.models import Timeframe
from datetime import datetime, timedelta

# 1. Download and store data (auto-hashing)
store = ParquetStore("data/parquet")
catalog = DataCatalog("data/catalog.db")
manager = StorageManager(store, catalog)

provider = MT5DataProvider()
end = datetime.now()
start = end - timedelta(days=365)

result = manager.download_and_store(
    provider=provider,
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    start=start,
    end=end,
)

# 2. Run backtest (pseudocode)
backtest_results = run_backtest(
    symbol="EURUSD",
    timeframe=Timeframe.H1,
    strategy=my_strategy,
)
backtest_id = save_backtest_results(backtest_results)  # Get ID from database

# 3. Record lineage
lineage = DataLineage("data/lineage.db")

# Get data files used from catalog
entries = catalog.query_available(symbol="EURUSD", timeframe=Timeframe.H1)
data_files = [
    {
        "file_path": e["file_path"],
        "version_hash": e["version_hash"],
        "symbol": e["symbol"],
        "timeframe": e["timeframe"],
        "partition": e["partition"],
    }
    for e in entries
]

lineage.record_backtest_lineage(backtest_id, data_files)
print(f"Recorded lineage for backtest {backtest_id}")

# 4. Later: Verify reproducibility
result = lineage.can_reproduce(backtest_id)
if result["reproducible"]:
    print("✓ Backtest is reproducible")
else:
    print(f"✗ Cannot reproduce: {result['issues']}")
```

### Data Update Workflow

```python
from hqt.data.versioning import DataManifest, DataLineage
from hqt.data.storage import DataCatalog

catalog = DataCatalog("data/catalog.db")
lineage = DataLineage("data/lineage.db")
manifest = DataManifest(catalog)

# 1. Before updating: Find impacted backtests
old_metadata = catalog.get_metadata("EURUSD", Timeframe.H1, "2024")
old_hash = old_metadata["version_hash"]

impacted_backtests = lineage.find_backtests_using_data(old_hash)
print(f"Found {len(impacted_backtests)} backtests using this data")

# 2. Update data (download new version)
manager.download_and_store(...)  # Overwrites with new data

# 3. Generate new manifest
manifest.update("data/manifest.json")

# 4. Compare manifests
diff = manifest.diff("data/manifest_old.json", "data/manifest.json")
print(f"Modified files: {len(diff['modified'])}")

# 5. Re-run impacted backtests
for backtest_id in impacted_backtests:
    print(f"Re-running backtest {backtest_id}...")
    # Re-run backtest with new data
```

### Integrity Verification Workflow

```python
from hqt.data.versioning import DataManifest
from hqt.data.storage import DataCatalog

catalog = DataCatalog("data/catalog.db")
manifest = DataManifest(catalog)

# 1. Generate baseline manifest
manifest.generate("data/manifest_baseline.json")

# 2. Later: Verify data integrity
result = manifest.verify(
    "data/manifest_baseline.json",
    check_hashes=True,
)

if not result["valid"]:
    print("⚠ Data integrity issues detected:")
    for issue in result["issues"]:
        print(f"  - {issue}")

    # 3. Regenerate manifest if data intentionally updated
    manifest.generate("data/manifest_updated.json")

    # 4. Compare to see what changed
    diff = manifest.diff(
        "data/manifest_baseline.json",
        "data/manifest_updated.json"
    )
    print(f"Changes: {len(diff['modified'])} modified")
```

---

## Best Practices

### 1. Always Record Lineage

```python
# Good - Record lineage for every backtest
lineage.record_backtest_lineage(backtest_id, data_files)

# Bad - No lineage = cannot verify reproducibility
```

### 2. Generate Manifests Regularly

```python
# Good - Generate manifest after each data update
manifest.update("data/manifest.json")

# Also good - Scheduled manifest generation
# (e.g., daily cron job)
```

### 3. Verify Before Important Operations

```python
# Before production backtest
result = lineage.can_reproduce(baseline_backtest_id)
if not result["reproducible"]:
    raise ValueError("Cannot reproduce baseline - data may be corrupted")

# Before archiving
result = manifest.verify("data/manifest.json")
if not result["valid"]:
    raise ValueError("Data integrity check failed")
```

### 4. Use Impact Analysis

```python
# Before deleting old data
impacted = lineage.find_backtests_using_data(hash_value)
if impacted:
    print(f"Warning: {len(impacted)} backtests use this data")
    # Decide whether to proceed
```

### 5. Version Manifests

```python
# Include timestamp in manifest filename
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
manifest_path = f"data/manifests/manifest_{timestamp}.json"
manifest.generate(manifest_path)
```

---

## API Reference

### Hashing Functions

| Function | Purpose |
|----------|---------|
| `compute_hash(data)` | Hash bytes (SHA-256) |
| `compute_file_hash(path)` | Hash file content |
| `compute_dataframe_hash(df)` | Hash DataFrame (timestamp + price signature) |
| `compute_hash_incremental(files)` | Combined hash of multiple files |
| `verify_hash(data, hash)` | Verify bytes match hash |
| `verify_file_hash(path, hash)` | Verify file matches hash |

### DataLineage Methods

| Method | Purpose |
|--------|---------|
| `record_backtest_lineage(id, files)` | Record data files used |
| `get_lineage(id)` | Get lineage info |
| `can_reproduce(id)` | Check reproducibility |
| `get_data_versions(id)` | Get version hashes |
| `find_backtests_using_data(hash)` | Find backtests using data |
| `delete_lineage(id)` | Delete lineage records |
| `get_stats()` | Get database statistics |

### DataManifest Methods

| Method | Purpose |
|--------|---------|
| `generate(path)` | Generate new manifest |
| `verify(path, check_hashes)` | Verify manifest |
| `update(path)` | Update existing manifest |
| `diff(path1, path2)` | Compare manifests |

---

## Troubleshooting

### Problem: "No lineage found for backtest"

**Cause:** Lineage was not recorded when backtest was run.

**Solution:**
```python
# Always record lineage after saving backtest
lineage.record_backtest_lineage(backtest_id, data_files)
```

### Problem: "Hash mismatch" in can_reproduce

**Cause:** Data file has been modified since backtest was run.

**Investigation:**
```python
# Get lineage to see what changed
info = lineage.get_lineage(backtest_id)
for f in info['data_files']:
    # Check current hash
    current_hash = compute_file_hash(f['data_file_path'])
    if current_hash != f['version_hash']:
        print(f"Modified: {f['data_file_path']}")
        print(f"  Recorded: {f['version_hash']}")
        print(f"  Current:  {current_hash}")
```

### Problem: "Missing file" in verification

**Cause:** Data file has been deleted.

**Solution:**
- Restore from backup
- Or update manifest to reflect current state
- Or archive old backtests that cannot be reproduced

### Problem: Slow manifest verification

**Cause:** Hashing large files takes time.

**Solution:**
```python
# Skip hash verification for quick check
result = manifest.verify("data/manifest.json", check_hashes=False)

# Or verify in background
import threading
thread = threading.Thread(
    target=manifest.verify,
    args=("data/manifest.json",)
)
thread.start()
```

---

## See Also

- [Data Storage Documentation](data_storage.md) - Catalog integration
- [Data Models Documentation](data_models.md) - DataFrame structure
- [Data Providers Documentation](data_providers.md) - Data sources
