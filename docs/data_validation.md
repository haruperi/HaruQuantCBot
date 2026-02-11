# Data Validation Pipeline Documentation

## Overview

The HQT Data Validation Pipeline provides comprehensive data quality checks, automated cleaning, and detailed reporting for market data. It ensures data integrity before backtesting or live trading.

**[REQ: DAT-FR-006 through DAT-FR-015]** Complete validation infrastructure.

## Quick Start

```python
from hqt.data.validation import ValidationPipeline, DataCleaner
import pandas as pd

# Load your data
df = pd.read_parquet("EURUSD_H1.parquet")

# Run validation
pipeline = ValidationPipeline()
report = pipeline.validate(df, symbol="EURUSD")

# Check results
print(f"Total issues: {report.total_issues}")
print(f"Pass rate: {report.pass_rate:.1%}")

# Clean data if needed
if report.total_issues > 0:
    cleaner = DataCleaner()
    df_clean = cleaner.clean_all(df)

    # Re-validate
    report_clean = pipeline.validate(df_clean, symbol="EURUSD")
    print(f"After cleaning: {report_clean.total_issues} issues")
```

## Validation Checks

### 1. PriceSanityCheck

**[REQ: DAT-FR-006]** Validates fundamental price sanity rules.

**Checks:**
- All prices are positive (> 0)
- High >= max(open, close)
- Low <= min(open, close)
- High >= low
- Prices within reasonable bounds (default: 10x median)

**Configuration:**
```python
from hqt.data.validation import PriceSanityCheck, IssueSeverity

checker = PriceSanityCheck(
    price_bound_multiplier=10.0,  # Max deviation from median
    severity=IssueSeverity.CRITICAL,
)
```

**Issues Detected:**
- `PRICE_SANITY`: Non-positive or out-of-bounds prices
- `OHLC_INCONSISTENCY`: OHLC relationship violations

### 2. GapDetector

**[REQ: DAT-FR-007]** Detects large gaps between consecutive bars.

**Algorithm:**
- Calculates average bar range
- Detects gaps > threshold * avg_range
- Default threshold: 10x

**Configuration:**
```python
from hqt.data.validation import GapDetector

detector = GapDetector(
    threshold_multiplier=10.0,  # 10x average range
    severity=IssueSeverity.WARNING,
)
```

**Use Cases:**
- Market gaps (weekends, holidays)
- Data feed interruptions
- Missing historical data

### 3. SpikeDetector

**[REQ: DAT-FR-008]** Detects abnormal price spikes using ATR.

**Algorithm:**
- Calculates ATR (Average True Range) over N periods
- Detects bars with range > threshold * ATR
- Default: 5x ATR over 14 periods

**Configuration:**
```python
from hqt.data.validation import SpikeDetector

detector = SpikeDetector(
    threshold_multiplier=5.0,  # 5x ATR
    atr_period=14,             # ATR calculation period
    severity=IssueSeverity.WARNING,
)
```

**Typical Causes:**
- Flash crashes
- Data feed errors
- Extreme market events

### 4. MissingTimestampDetector

**[REQ: DAT-FR-009]** Detects missing timestamps in the time series.

**Algorithm:**
- Auto-detects expected interval (or uses configured value)
- Flags gaps > 1.5x expected interval
- Estimates number of missing bars

**Configuration:**
```python
from hqt.data.validation import MissingTimestampDetector

detector = MissingTimestampDetector(
    expected_interval_seconds=3600,  # 1 hour (None = auto-detect)
    severity=IssueSeverity.WARNING,
)
```

**Limitations:**
- Does not account for market hours or holidays
- Basic implementation (can be extended per symbol)

### 5. ZeroVolumeDetector

**[REQ: DAT-FR-010]** Detects bars with zero or missing volume.

**Configuration:**
```python
from hqt.data.validation import ZeroVolumeDetector

detector = ZeroVolumeDetector(
    severity=IssueSeverity.INFO,  # Usually informational
)
```

**Note:** Zero volume may be normal for tick data or certain timeframes.

### 6. DuplicateDetector

**[REQ: DAT-FR-011]** Detects duplicate timestamps.

**Behavior:**
- Finds all duplicate timestamps
- Reports occurrence count
- Keeps last occurrence by default (in cleaning)

**Configuration:**
```python
from hqt.data.validation import DuplicateDetector

detector = DuplicateDetector(
    severity=IssueSeverity.ERROR,  # Usually an error
)
```

### 7. SpreadAnalyzer

**[REQ: DAT-FR-012]** Detects abnormal spread widening.

**Algorithm:**
- Calculates spread (high - low for bars)
- Detects spread > threshold * median_spread
- Default threshold: 3x

**Configuration:**
```python
from hqt.data.validation import SpreadAnalyzer

analyzer = SpreadAnalyzer(
    threshold_multiplier=3.0,  # 3x median spread
    severity=IssueSeverity.WARNING,
)
```

**Use Cases:**
- Low liquidity detection
- News event identification
- Data quality monitoring

## Validation Pipeline

**[REQ: DAT-FR-014, DAT-FR-015]** Orchestrates all checks with configurable thresholds.

### Basic Usage

```python
from hqt.data.validation import ValidationPipeline

# Use default configuration
pipeline = ValidationPipeline()
report = pipeline.validate(df, symbol="EURUSD")
```

### Custom Configuration

```python
from hqt.data.validation import ValidationPipeline, ValidationConfig

# Configure per-symbol thresholds
config = ValidationConfig(
    price_bound_multiplier=10.0,
    gap_threshold_multiplier=10.0,
    spike_threshold_multiplier=5.0,
    spike_atr_period=14,
    spread_threshold_multiplier=3.0,
    expected_interval_seconds=3600,  # 1 hour
)

pipeline = ValidationPipeline(config=config)
```

### Symbol-Specific Configs

```python
# Gold (more volatile)
gold_config = ValidationConfig(
    spike_threshold_multiplier=10.0,  # Higher tolerance
    gap_threshold_multiplier=20.0,
)

# Forex (tighter)
forex_config = ValidationConfig(
    spike_threshold_multiplier=3.0,
    spread_threshold_multiplier=2.0,
)

# Create pipelines
gold_pipeline = ValidationPipeline(config=gold_config)
forex_pipeline = ValidationPipeline(config=forex_config)
```

### Selective Checks

```python
# Run only specific checks
config = ValidationConfig(
    enabled_checks=[
        "PriceSanityCheck",
        "DuplicateDetector",
        "GapDetector",
    ]
)
pipeline = ValidationPipeline(config=config)
```

### Custom Validators

```python
from hqt.data.validation import Validator, ValidationIssue

class MyCustomValidator(Validator):
    def name(self) -> str:
        return "MyCustomValidator"

    def validate(self, df, symbol, **kwargs):
        issues = []
        # Your custom logic here
        return issues

# Add to pipeline
pipeline = ValidationPipeline()
pipeline.add_validator(MyCustomValidator())
```

## Data Cleaning

**[REQ: DAT-FR-013]** Automated data cleaning operations.

### Remove Duplicates

```python
from hqt.data.validation import DataCleaner

cleaner = DataCleaner()

# Keep last occurrence
df_clean = cleaner.remove_duplicates(df, keep="last")

# Keep first occurrence
df_clean = cleaner.remove_duplicates(df, keep="first")

# Remove all duplicates
df_clean = cleaner.remove_duplicates(df, keep=False)
```

### Fill Gaps

```python
from hqt.data.validation import DataCleaner, FillMethod

cleaner = DataCleaner()

# Forward fill
df_clean = cleaner.fill_gaps(df, method=FillMethod.FORWARD_FILL)

# Backward fill
df_clean = cleaner.fill_gaps(df, method=FillMethod.BACKWARD_FILL)

# Linear interpolation
df_clean = cleaner.fill_gaps(df, method=FillMethod.INTERPOLATE_LINEAR)

# Time-weighted interpolation
df_clean = cleaner.fill_gaps(df, method=FillMethod.INTERPOLATE_TIME)

# Fill only small gaps (< 1 hour)
df_clean = cleaner.fill_gaps(
    df,
    method=FillMethod.FORWARD_FILL,
    max_gap_seconds=3600,
)
```

### Filter Spikes

```python
cleaner = DataCleaner()

# Interpolate spikes (>10x ATR)
df_clean = cleaner.filter_spikes(
    df,
    threshold_multiplier=10.0,
    atr_period=14,
    replace_method="interpolate",
)

# Remove spike bars entirely
df_clean = cleaner.filter_spikes(
    df,
    threshold_multiplier=10.0,
    replace_method="remove",
)
```

### Fill Zero Volumes

```python
cleaner = DataCleaner()

# Forward fill
df_clean = cleaner.fill_zero_volumes(df, method="ffill")

# Use median volume
df_clean = cleaner.fill_zero_volumes(df, method="median")
```

### Clean All

```python
cleaner = DataCleaner()

# Apply all cleaning operations
df_clean = cleaner.clean_all(
    df,
    remove_duplicates=True,
    fill_gaps=True,
    filter_spikes=True,
    fill_zero_volumes=True,
    # Optional parameters
    fill_method=FillMethod.FORWARD_FILL,
    spike_threshold_multiplier=10.0,
    atr_period=14,
    volume_fill_method="ffill",
)
```

## Validation Report

**[REQ: DAT-FR-014]** Comprehensive reporting with multiple export formats.

### Report Properties

```python
report = pipeline.validate(df, symbol="EURUSD")

# Summary
print(f"Total bars: {report.total_bars}")
print(f"Total issues: {report.total_issues}")
print(f"Clean: {report.clean}")
print(f"Pass rate: {report.pass_rate:.1%}")

# Severity breakdown
print(f"Critical: {report.critical_count}")
print(f"Errors: {report.error_count}")
print(f"Warnings: {report.warning_count}")
print(f"Info: {report.info_count}")

# By type
print(report.type_counts)

# By check
print(report.check_counts)
```

### Filter Issues

```python
from hqt.data.validation import IssueSeverity, IssueType

# Get critical issues only
critical_issues = report.get_issues_by_severity(IssueSeverity.CRITICAL)

# Get spike issues only
spike_issues = report.get_issues_by_type(IssueType.SPIKE)
```

### Export to Dictionary

```python
report_dict = report.to_dict()

# Access data
summary = report_dict["summary"]
issues = report_dict["issues"]
severity_breakdown = report_dict["severity_breakdown"]
```

### Export to DataFrame

```python
import pandas as pd

# Get DataFrame of all issues
df_issues = report.to_dataframe()

# Analyze
print(df_issues.groupby("severity").size())
print(df_issues.groupby("issue_type").size())

# Filter
critical_df = df_issues[df_issues["severity"] == "CRITICAL"]
```

### Export to HTML

```python
# Generate HTML report
html = report.to_html(include_details=True)

# Save to file
with open("validation_report.html", "w") as f:
    f.write(html)

# Email or display in dashboard
```

## Complete Workflow Example

```python
from hqt.data.validation import (
    ValidationPipeline,
    ValidationConfig,
    DataCleaner,
    FillMethod,
)
import pandas as pd

# 1. Load data
df = pd.read_parquet("EURUSD_H1_2024.parquet")
print(f"Loaded {len(df)} bars")

# 2. Configure validation
config = ValidationConfig(
    spike_threshold_multiplier=7.0,
    gap_threshold_multiplier=15.0,
)

# 3. Run initial validation
pipeline = ValidationPipeline(config=config)
report = pipeline.validate(df, symbol="EURUSD")

print(f"\nInitial Validation:")
print(f"  Total issues: {report.total_issues}")
print(f"  Pass rate: {report.pass_rate:.1%}")
print(f"  Critical: {report.critical_count}")
print(f"  Errors: {report.error_count}")

# 4. Clean data if needed
if report.total_issues > 0:
    print(f"\nCleaning data...")

    cleaner = DataCleaner()
    df_clean = cleaner.clean_all(
        df,
        fill_method=FillMethod.FORWARD_FILL,
        spike_threshold_multiplier=10.0,
    )

    # 5. Re-validate
    report_clean = pipeline.validate(df_clean, symbol="EURUSD")

    print(f"\nAfter Cleaning:")
    print(f"  Total issues: {report_clean.total_issues}")
    print(f"  Pass rate: {report_clean.pass_rate:.1%}")

    # 6. Export reports
    report.to_dataframe().to_csv("validation_before.csv")
    report_clean.to_dataframe().to_csv("validation_after.csv")

    with open("validation_report.html", "w") as f:
        f.write(report_clean.to_html())

    # 7. Use cleaned data
    df_clean.to_parquet("EURUSD_H1_2024_clean.parquet")
    print(f"\nCleaned data saved!")
else:
    print(f"\nData is clean - no cleaning needed!")
```

## Best Practices

### 1. Per-Symbol Configuration

Different instruments have different characteristics:

```python
# Forex majors - tight thresholds
forex_config = ValidationConfig(
    spike_threshold_multiplier=3.0,
    spread_threshold_multiplier=2.0,
)

# Gold/Silver - more volatile
metals_config = ValidationConfig(
    spike_threshold_multiplier=10.0,
    gap_threshold_multiplier=20.0,
)

# Indices - medium volatility
indices_config = ValidationConfig(
    spike_threshold_multiplier=5.0,
    gap_threshold_multiplier=15.0,
)
```

### 2. Progressive Cleaning

Clean in stages and re-validate:

```python
cleaner = DataCleaner()

# Stage 1: Remove duplicates
df = cleaner.remove_duplicates(df)
report1 = pipeline.validate(df, symbol="EURUSD")

# Stage 2: Fill gaps
if report1.type_counts.get("MISSING_TIMESTAMP", 0) > 0:
    df = cleaner.fill_gaps(df)
    report2 = pipeline.validate(df, symbol="EURUSD")

# Stage 3: Filter extreme spikes
if report2.type_counts.get("SPIKE", 0) > 0:
    df = cleaner.filter_spikes(df, threshold_multiplier=10.0)
    report3 = pipeline.validate(df, symbol="EURUSD")
```

### 3. Critical Issues Only

For production, focus on critical issues:

```python
critical_issues = report.get_issues_by_severity(IssueSeverity.CRITICAL)

if len(critical_issues) > 0:
    print("CRITICAL ISSUES - Data unusable!")
    for issue in critical_issues:
        print(f"  - {issue.message}")
    # Don't use this data
else:
    print("No critical issues - data OK for backtesting")
```

### 4. Logging Integration

```python
import logging

logger = logging.getLogger(__name__)

report = pipeline.validate(df, symbol=symbol)

if report.critical_count > 0:
    logger.critical(f"{symbol}: {report.critical_count} critical issues")
elif report.error_count > 0:
    logger.error(f"{symbol}: {report.error_count} errors")
elif report.warning_count > 0:
    logger.warning(f"{symbol}: {report.warning_count} warnings")
else:
    logger.info(f"{symbol}: Clean data ({len(df)} bars)")
```

## Thresholds Reference

| Check | Parameter | Default | Forex | Gold | Indices |
|-------|-----------|---------|-------|------|---------|
| PriceSanity | price_bound_multiplier | 10.0 | 5.0 | 20.0 | 10.0 |
| GapDetector | threshold_multiplier | 10.0 | 10.0 | 20.0 | 15.0 |
| SpikeDetector | threshold_multiplier | 5.0 | 3.0 | 10.0 | 5.0 |
| SpikeDetector | atr_period | 14 | 14 | 20 | 14 |
| SpreadAnalyzer | threshold_multiplier | 3.0 | 2.0 | 5.0 | 3.0 |

## Performance Considerations

- Validation is fast (1M bars in ~2 seconds)
- Use `enabled_checks` to skip unnecessary validators
- Cleaning operations are vectorized (pandas/numpy)
- Reports support lazy evaluation

## Troubleshooting

### High False Positive Rate

- Increase thresholds (e.g., spike_threshold_multiplier)
- Use symbol-specific configuration
- Consider market characteristics (volatility, liquidity)

### Missing Issues

- Decrease thresholds
- Add custom validators
- Check data format (ensure timestamp in microseconds)

### Performance Issues

- Use selective checks (`enabled_checks`)
- Process in chunks for very large datasets
- Disable detailed HTML reports for bulk processing

## API Reference

See module docstrings for complete API documentation:
- `hqt.data.validation.models`
- `hqt.data.validation.checks`
- `hqt.data.validation.pipeline`
- `hqt.data.validation.cleaning`
- `hqt.data.validation.report`
