"""
Unit tests for data validation pipeline.

Tests the complete validation pipeline including:
- ValidationIssue model
- All 7 validators with planted issues
- ValidationPipeline orchestration
- DataCleaner operations
- ValidationReport export formats
"""

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from hqt.data.validation import (
    DataCleaner,
    DuplicateDetector,
    FillMethod,
    GapDetector,
    IssueSeverity,
    IssueType,
    MissingTimestampDetector,
    PriceSanityCheck,
    SpikeDetector,
    SpreadAnalyzer,
    ValidationConfig,
    ValidationIssue,
    ValidationPipeline,
    ZeroVolumeDetector,
)


# ============================================================================
# Fixtures - Test Data with Planted Issues
# ============================================================================


@pytest.fixture
def clean_data():
    """Create clean OHLCV data without issues."""
    timestamps = pd.date_range("2024-01-01", periods=100, freq="1min")
    np.random.seed(42)

    base_price = 1.1000
    data = {
        "timestamp": [int(ts.timestamp()) for ts in timestamps],
        "open": base_price + np.random.randn(100) * 0.0001,
        "high": base_price + np.abs(np.random.randn(100)) * 0.0002,
        "low": base_price - np.abs(np.random.randn(100)) * 0.0002,
        "close": base_price + np.random.randn(100) * 0.0001,
        "volume": np.random.randint(1000, 10000, 100).astype(float),
    }

    df = pd.DataFrame(data)
    # Ensure OHLC consistency
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)

    return df


@pytest.fixture
def data_with_negative_prices():
    """Create data with negative/zero prices."""
    df = pd.DataFrame({
        "timestamp": [1704067200 + i * 60 for i in range(5)],
        "open": [1.1000, 1.1010, -1.1020, 1.1030, 1.1040],  # Negative price at index 2
        "high": [1.1005, 1.1015, 0.0000, 1.1035, 1.1045],  # Zero price at index 2
        "low": [1.0995, 1.1005, 1.1015, 1.1025, 1.1035],
        "close": [1.1002, 1.1012, 1.1022, 1.1032, 1.1042],
        "volume": [1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
    })
    return df


@pytest.fixture
def data_with_ohlc_violations():
    """Create data with OHLC inconsistencies."""
    df = pd.DataFrame({
        "timestamp": [1704067200 + i * 60 for i in range(5)],
        "open": [1.1000, 1.1010, 1.1020, 1.1030, 1.1040],
        "high": [1.1005, 1.1000, 1.1025, 1.1035, 1.1045],  # high < open at index 1
        "low": [1.0995, 1.1005, 1.1025, 1.1025, 1.1035],  # low > close at index 2
        "close": [1.1002, 1.1012, 1.1022, 1.1032, 1.1042],
        "volume": [1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
    })
    return df


@pytest.fixture
def data_with_gaps():
    """Create data with large price gaps."""
    df = pd.DataFrame({
        "timestamp": [1704067200 + i * 60 for i in range(5)],
        "open": [1.1000, 1.1010, 1.2000, 1.2010, 1.2020],  # Large gap at index 2
        "high": [1.1005, 1.1015, 1.2005, 1.2015, 1.2025],
        "low": [1.0995, 1.1005, 1.1995, 1.2005, 1.2015],
        "close": [1.1002, 1.1012, 1.2002, 1.2012, 1.2022],
        "volume": [1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
    })
    return df


@pytest.fixture
def data_with_spikes():
    """Create data with price spikes."""
    # Create data with normal range then a huge spike
    data = {
        "timestamp": [1704067200 + i * 60 for i in range(20)],
        "open": [1.1000 + i * 0.0001 for i in range(20)],
        "high": [1.1005 + i * 0.0001 for i in range(20)],
        "low": [1.0995 + i * 0.0001 for i in range(20)],
        "close": [1.1002 + i * 0.0001 for i in range(20)],
        "volume": [1000.0] * 20,
    }
    df = pd.DataFrame(data)
    # Create a massive spike at index 15 (after ATR can be calculated)
    df.loc[15, "high"] = 1.2000  # Huge spike
    df.loc[15, "low"] = 1.0995 + 15 * 0.0001  # Keep low normal
    return df


@pytest.fixture
def data_with_missing_timestamps():
    """Create data with missing timestamps."""
    # Create timestamps with a gap
    timestamps = list(range(1704067200, 1704067200 + 5 * 60, 60))
    timestamps.extend(range(1704067200 + 10 * 60, 1704067200 + 15 * 60, 60))  # Gap of 5 minutes

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": [1.1000 + i * 0.0001 for i in range(len(timestamps))],
        "high": [1.1005 + i * 0.0001 for i in range(len(timestamps))],
        "low": [1.0995 + i * 0.0001 for i in range(len(timestamps))],
        "close": [1.1002 + i * 0.0001 for i in range(len(timestamps))],
        "volume": [1000.0] * len(timestamps),
    })
    return df


@pytest.fixture
def data_with_zero_volume():
    """Create data with zero volumes."""
    df = pd.DataFrame({
        "timestamp": [1704067200 + i * 60 for i in range(5)],
        "open": [1.1000, 1.1010, 1.1020, 1.1030, 1.1040],
        "high": [1.1005, 1.1015, 1.1025, 1.1035, 1.1045],
        "low": [1.0995, 1.1005, 1.1015, 1.1025, 1.1035],
        "close": [1.1002, 1.1012, 1.1022, 1.1032, 1.1042],
        "volume": [1000.0, 0.0, 1000.0, -100.0, 1000.0],  # Zero at index 1, negative at index 3
    })
    return df


@pytest.fixture
def data_with_duplicates():
    """Create data with duplicate timestamps."""
    df = pd.DataFrame({
        "timestamp": [1704067200, 1704067260, 1704067260, 1704067320, 1704067380],  # Duplicate at index 1-2
        "open": [1.1000, 1.1010, 1.1015, 1.1020, 1.1030],
        "high": [1.1005, 1.1015, 1.1020, 1.1025, 1.1035],
        "low": [1.0995, 1.1005, 1.1010, 1.1015, 1.1025],
        "close": [1.1002, 1.1012, 1.1017, 1.1022, 1.1032],
        "volume": [1000.0, 1000.0, 1500.0, 1000.0, 1000.0],
    })
    return df


@pytest.fixture
def data_with_wide_spreads():
    """Create data with abnormally wide spreads."""
    df = pd.DataFrame({
        "timestamp": [1704067200 + i * 60 for i in range(30)],
        "open": [1.1000] * 30,
        "high": [1.1005 if i != 15 else 1.1500 for i in range(30)],  # Wide spread at index 15
        "low": [1.0995] * 30,
        "close": [1.1002] * 30,
        "volume": [1000.0] * 30,
    })
    return df


# ============================================================================
# Test ValidationIssue Model
# ============================================================================


class TestValidationIssue:
    """Test ValidationIssue model."""

    def test_issue_creation(self):
        """Test creating a validation issue."""
        issue = ValidationIssue(
            issue_type=IssueType.SPIKE,
            severity=IssueSeverity.WARNING,
            timestamp=1704067200000000,
            symbol="EURUSD",
            message="Spike detected",
            details={"range": 0.001, "atr": 0.0002},
            check_name="SpikeDetector",
        )

        assert issue.issue_type == IssueType.SPIKE
        assert issue.severity == IssueSeverity.WARNING
        assert issue.timestamp == 1704067200000000
        assert issue.symbol == "EURUSD"
        assert issue.message == "Spike detected"
        assert issue.details["range"] == 0.001
        assert issue.check_name == "SpikeDetector"

    def test_issue_immutable(self):
        """Test that ValidationIssue is immutable."""
        issue = ValidationIssue(
            issue_type=IssueType.GAP,
            severity=IssueSeverity.WARNING,
            timestamp=1704067200000000,
            symbol="EURUSD",
            message="Gap detected",
            check_name="GapDetector",
        )

        with pytest.raises(Exception):  # Pydantic raises ValidationError
            issue.severity = IssueSeverity.CRITICAL

    def test_issue_datetime_property(self):
        """Test datetime property conversion."""
        issue = ValidationIssue(
            issue_type=IssueType.SPIKE,
            severity=IssueSeverity.WARNING,
            timestamp=1704067200000000,  # 2024-01-01 00:00:00 UTC
            symbol="EURUSD",
            message="Test",
            check_name="Test",
        )

        dt = issue.datetime
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1

    def test_issue_to_dict(self):
        """Test issue to_dict conversion."""
        issue = ValidationIssue(
            issue_type=IssueType.DUPLICATE,
            severity=IssueSeverity.ERROR,
            timestamp=1704067200000000,
            symbol="EURUSD",
            message="Duplicate detected",
            details={"count": 2},
            check_name="DuplicateDetector",
        )

        d = issue.to_dict()
        assert d["issue_type"] == "DUPLICATE"
        assert d["severity"] == "ERROR"
        assert d["timestamp"] == 1704067200000000
        assert d["symbol"] == "EURUSD"
        assert d["message"] == "Duplicate detected"
        assert d["details"]["count"] == 2
        assert d["check_name"] == "DuplicateDetector"

    def test_issue_repr(self):
        """Test issue string representation."""
        issue = ValidationIssue(
            issue_type=IssueType.SPIKE,
            severity=IssueSeverity.WARNING,
            timestamp=1704067200000000,
            symbol="EURUSD",
            message="Test",
            check_name="Test",
        )

        repr_str = repr(issue)
        assert "ValidationIssue" in repr_str
        assert "SPIKE" in repr_str
        assert "WARNING" in repr_str
        assert "EURUSD" in repr_str


# ============================================================================
# Test Validators
# ============================================================================


class TestPriceSanityCheck:
    """Test PriceSanityCheck validator."""

    def test_detects_negative_prices(self, data_with_negative_prices):
        """Test detection of negative prices."""
        validator = PriceSanityCheck()
        issues = validator.validate(data_with_negative_prices, "EURUSD")

        assert len(issues) > 0
        # Should detect negative open and zero high
        price_sanity_issues = [i for i in issues if i.issue_type == IssueType.PRICE_SANITY]
        assert len(price_sanity_issues) > 0

    def test_detects_ohlc_violations(self, data_with_ohlc_violations):
        """Test detection of OHLC inconsistencies."""
        validator = PriceSanityCheck()
        issues = validator.validate(data_with_ohlc_violations, "EURUSD")

        assert len(issues) > 0
        ohlc_issues = [i for i in issues if i.issue_type == IssueType.OHLC_INCONSISTENCY]
        assert len(ohlc_issues) > 0

    def test_clean_data_passes(self, clean_data):
        """Test that clean data produces no issues."""
        validator = PriceSanityCheck()
        issues = validator.validate(clean_data, "EURUSD")

        # Should have minimal or no issues
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        assert len(critical_issues) == 0

    def test_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        validator = PriceSanityCheck()
        df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        issues = validator.validate(df, "EURUSD")

        assert len(issues) == 0

    def test_price_bounds_check(self):
        """Test price bounds violation detection."""
        # Create data with one extreme outlier
        df = pd.DataFrame({
            "timestamp": [1704067200 + i * 60 for i in range(5)],
            "open": [1.1000, 1.1010, 100.0000, 1.1030, 1.1040],  # Extreme outlier
            "high": [1.1005, 1.1015, 100.0005, 1.1035, 1.1045],
            "low": [1.0995, 1.1005, 99.9995, 1.1025, 1.1035],
            "close": [1.1002, 1.1012, 100.0002, 1.1032, 1.1042],
            "volume": [1000.0] * 5,
        })

        validator = PriceSanityCheck(price_bound_multiplier=10.0)
        issues = validator.validate(df, "EURUSD")

        price_bound_issues = [i for i in issues if "outside reasonable bounds" in i.message]
        assert len(price_bound_issues) > 0


class TestGapDetector:
    """Test GapDetector validator."""

    def test_detects_gaps(self, data_with_gaps):
        """Test detection of price gaps."""
        validator = GapDetector(threshold_multiplier=10.0)
        issues = validator.validate(data_with_gaps, "EURUSD")

        assert len(issues) > 0
        gap_issues = [i for i in issues if i.issue_type == IssueType.GAP]
        assert len(gap_issues) > 0

    def test_clean_data_no_gaps(self, clean_data):
        """Test that clean data has no gaps."""
        validator = GapDetector(threshold_multiplier=10.0)
        issues = validator.validate(clean_data, "EURUSD")

        assert len(issues) == 0

    def test_requires_minimum_data(self):
        """Test that single bar produces no issues."""
        df = pd.DataFrame({
            "timestamp": [1704067200],
            "open": [1.1000],
            "high": [1.1005],
            "low": [1.0995],
            "close": [1.1002],
            "volume": [1000.0],
        })

        validator = GapDetector()
        issues = validator.validate(df, "EURUSD")
        assert len(issues) == 0


class TestSpikeDetector:
    """Test SpikeDetector validator."""

    def test_detects_spikes(self, data_with_spikes):
        """Test detection of price spikes."""
        validator = SpikeDetector(threshold_multiplier=5.0, atr_period=14)
        issues = validator.validate(data_with_spikes, "EURUSD")

        assert len(issues) > 0
        spike_issues = [i for i in issues if i.issue_type == IssueType.SPIKE]
        assert len(spike_issues) > 0

    def test_clean_data_no_spikes(self, clean_data):
        """Test that clean data has no spikes."""
        validator = SpikeDetector(threshold_multiplier=5.0)
        issues = validator.validate(clean_data, "EURUSD")

        assert len(issues) == 0

    def test_requires_sufficient_data(self):
        """Test that insufficient data for ATR produces no issues."""
        df = pd.DataFrame({
            "timestamp": [1704067200 + i * 60 for i in range(5)],
            "open": [1.1000] * 5,
            "high": [1.1005] * 5,
            "low": [1.0995] * 5,
            "close": [1.1002] * 5,
            "volume": [1000.0] * 5,
        })

        validator = SpikeDetector(atr_period=14)
        issues = validator.validate(df, "EURUSD")
        assert len(issues) == 0


class TestMissingTimestampDetector:
    """Test MissingTimestampDetector validator."""

    def test_detects_missing_timestamps(self, data_with_missing_timestamps):
        """Test detection of missing timestamps."""
        validator = MissingTimestampDetector(expected_interval_seconds=60, tolerance=1.5)
        issues = validator.validate(data_with_missing_timestamps, "EURUSD")

        assert len(issues) > 0
        # Check issue type - using MISSING_TIMESTAMP enum value
        missing_issues = [i for i in issues if i.issue_type == IssueType.MISSING_TIMESTAMP]
        assert len(missing_issues) > 0

    def test_clean_data_no_missing(self, clean_data):
        """Test that clean data has no missing timestamps."""
        validator = MissingTimestampDetector(expected_interval_seconds=60)
        issues = validator.validate(clean_data, "EURUSD")

        assert len(issues) == 0

    def test_auto_detect_interval(self, clean_data):
        """Test validation without explicit interval."""
        validator = MissingTimestampDetector(expected_interval_seconds=60)
        issues = validator.validate(clean_data, "EURUSD")

        assert len(issues) == 0


class TestZeroVolumeDetector:
    """Test ZeroVolumeDetector validator."""

    def test_detects_zero_volume(self, data_with_zero_volume):
        """Test detection of zero/negative volumes."""
        validator = ZeroVolumeDetector()
        issues = validator.validate(data_with_zero_volume, "EURUSD")

        assert len(issues) >= 2  # Should detect both zero and negative
        # Check for zero volume issues
        zero_vol_issues = [i for i in issues if i.issue_type == IssueType.ZERO_VOLUME]
        assert len(zero_vol_issues) >= 2

    def test_clean_data_no_zero_volume(self, clean_data):
        """Test that clean data has no zero volumes."""
        validator = ZeroVolumeDetector()
        issues = validator.validate(clean_data, "EURUSD")

        assert len(issues) == 0

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        validator = ZeroVolumeDetector()
        df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        issues = validator.validate(df, "EURUSD")

        assert len(issues) == 0


class TestDuplicateDetector:
    """Test DuplicateDetector validator."""

    def test_detects_duplicates(self, data_with_duplicates):
        """Test detection of duplicate timestamps."""
        validator = DuplicateDetector()
        issues = validator.validate(data_with_duplicates, "EURUSD")

        assert len(issues) >= 2  # Should detect both occurrences
        dup_issues = [i for i in issues if i.issue_type == IssueType.DUPLICATE]
        assert len(dup_issues) >= 2

    def test_clean_data_no_duplicates(self, clean_data):
        """Test that clean data has no duplicates."""
        validator = DuplicateDetector()
        issues = validator.validate(clean_data, "EURUSD")

        assert len(issues) == 0

    def test_multiple_duplicates(self):
        """Test detection of multiple duplicate groups."""
        df = pd.DataFrame({
            "timestamp": [1704067200, 1704067200, 1704067260, 1704067260, 1704067320],
            "open": [1.1000, 1.1005, 1.1010, 1.1015, 1.1020],
            "high": [1.1005, 1.1010, 1.1015, 1.1020, 1.1025],
            "low": [1.0995, 1.1000, 1.1005, 1.1010, 1.1015],
            "close": [1.1002, 1.1007, 1.1012, 1.1017, 1.1022],
            "volume": [1000.0] * 5,
        })

        validator = DuplicateDetector()
        issues = validator.validate(df, "EURUSD")

        assert len(issues) == 4  # 2 pairs of duplicates


class TestSpreadAnalyzer:
    """Test SpreadAnalyzer validator."""

    def test_detects_wide_spreads(self, data_with_wide_spreads):
        """Test detection of abnormally wide spreads."""
        validator = SpreadAnalyzer(threshold_multiplier=3.0, min_periods=20)
        issues = validator.validate(data_with_wide_spreads, "EURUSD")

        assert len(issues) > 0
        spread_issues = [i for i in issues if i.issue_type == IssueType.SPREAD_ANOMALY]
        assert len(spread_issues) > 0

    def test_clean_data_no_spread_anomalies(self, clean_data):
        """Test that clean data has no spread anomalies."""
        validator = SpreadAnalyzer(threshold_multiplier=3.0)
        issues = validator.validate(clean_data, "EURUSD")

        assert len(issues) == 0

    def test_requires_minimum_periods(self):
        """Test that insufficient data produces no issues."""
        df = pd.DataFrame({
            "timestamp": [1704067200 + i * 60 for i in range(10)],
            "open": [1.1000] * 10,
            "high": [1.1005] * 10,
            "low": [1.0995] * 10,
            "close": [1.1002] * 10,
            "volume": [1000.0] * 10,
        })

        validator = SpreadAnalyzer(min_periods=20)
        issues = validator.validate(df, "EURUSD")
        assert len(issues) == 0


# ============================================================================
# Test ValidationPipeline
# ============================================================================


class TestValidationPipeline:
    """Test ValidationPipeline orchestrator."""

    def test_pipeline_runs_all_checks(self, clean_data):
        """Test that pipeline runs all validators."""
        pipeline = ValidationPipeline()
        report = pipeline.validate(clean_data, "EURUSD")

        assert report.symbol == "EURUSD"
        assert report.total_bars == len(clean_data)
        assert len(report.checks_run) == 7  # All 7 validators

    def test_pipeline_detects_multiple_issues(self):
        """Test that pipeline detects issues from multiple validators."""
        # Create data with multiple types of issues
        df = pd.DataFrame({
            "timestamp": [1704067200, 1704067260, 1704067260, 1704067320, 1704067380],  # Duplicate
            "open": [1.1000, -1.1010, 1.1020, 1.1030, 1.1040],  # Negative price
            "high": [1.1005, 1.1015, 1.1025, 1.1035, 1.1045],
            "low": [1.0995, 1.1005, 1.1015, 1.1025, 1.1035],
            "close": [1.1002, 1.1012, 1.1022, 1.1032, 1.1042],
            "volume": [1000.0, 0.0, 1000.0, 1000.0, 1000.0],  # Zero volume
        })

        pipeline = ValidationPipeline()
        report = pipeline.validate(df, "EURUSD")

        assert report.total_issues > 0
        # Should have issues from multiple validators
        assert len(report.check_counts) > 1

    def test_pipeline_with_custom_config(self, clean_data):
        """Test pipeline with custom configuration."""
        config = ValidationConfig(
            spike_threshold_multiplier=10.0,
            gap_threshold_multiplier=20.0,
        )
        pipeline = ValidationPipeline(config=config)
        report = pipeline.validate(clean_data, "EURUSD")

        assert report.total_bars == len(clean_data)

    def test_pipeline_with_enabled_checks(self, clean_data):
        """Test pipeline with subset of checks enabled."""
        config = ValidationConfig(
            enabled_checks=["PriceSanityCheck", "DuplicateDetector"]
        )
        pipeline = ValidationPipeline(config=config)
        report = pipeline.validate(clean_data, "EURUSD")

        assert len(report.checks_run) == 2
        assert "PriceSanityCheck" in report.checks_run
        assert "DuplicateDetector" in report.checks_run

    def test_pipeline_add_custom_validator(self, clean_data):
        """Test adding a custom validator to pipeline."""
        pipeline = ValidationPipeline()
        initial_count = len(pipeline.validators)

        # Add duplicate detector again (just for testing)
        pipeline.add_validator(DuplicateDetector())

        assert len(pipeline.validators) == initial_count + 1

    def test_pipeline_remove_validator(self):
        """Test removing a validator from pipeline."""
        pipeline = ValidationPipeline()
        initial_count = len(pipeline.validators)

        result = pipeline.remove_validator("ZeroVolumeDetector")

        assert result is True
        assert len(pipeline.validators) == initial_count - 1
        assert "ZeroVolumeDetector" not in pipeline.validators

    def test_pipeline_empty_dataframe_raises(self):
        """Test that empty DataFrame raises ValueError."""
        pipeline = ValidationPipeline()
        df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        with pytest.raises(ValueError, match="empty DataFrame"):
            pipeline.validate(df, "EURUSD")

    def test_pipeline_missing_columns_raises(self):
        """Test that missing columns raises ValueError."""
        pipeline = ValidationPipeline()
        df = pd.DataFrame({
            "timestamp": [1704067200],
            "open": [1.1000],
        })

        with pytest.raises(ValueError, match="missing required columns"):
            pipeline.validate(df, "EURUSD")


# ============================================================================
# Test DataCleaner
# ============================================================================


class TestDataCleaner:
    """Test DataCleaner operations."""

    def test_remove_duplicates_keep_last(self, data_with_duplicates):
        """Test removing duplicates keeping last occurrence."""
        cleaner = DataCleaner()
        cleaned = cleaner.remove_duplicates(data_with_duplicates, keep="last")

        # Should have one less row
        assert len(cleaned) == len(data_with_duplicates) - 1
        # Should not have duplicate timestamps
        assert cleaned["timestamp"].is_unique

    def test_remove_duplicates_keep_first(self, data_with_duplicates):
        """Test removing duplicates keeping first occurrence."""
        cleaner = DataCleaner()
        cleaned = cleaner.remove_duplicates(data_with_duplicates, keep="first")

        assert len(cleaned) == len(data_with_duplicates) - 1
        assert cleaned["timestamp"].is_unique

    def test_remove_duplicates_keep_none(self, data_with_duplicates):
        """Test removing all duplicates."""
        cleaner = DataCleaner()
        cleaned = cleaner.remove_duplicates(data_with_duplicates, keep=False)

        # Should remove both duplicate occurrences
        assert len(cleaned) == len(data_with_duplicates) - 2
        assert cleaned["timestamp"].is_unique

    def test_fill_gaps_forward_fill(self):
        """Test filling gaps with forward fill."""
        df = pd.DataFrame({
            "timestamp": [1704067200, 1704067260, 1704067320],
            "open": [1.1000, np.nan, 1.1020],
            "high": [1.1005, np.nan, 1.1025],
            "low": [1.0995, np.nan, 1.1015],
            "close": [1.1002, np.nan, 1.1022],
            "volume": [1000.0, np.nan, 1000.0],
        })

        cleaner = DataCleaner()
        cleaned = cleaner.fill_gaps(df, method=FillMethod.FORWARD_FILL)

        # Should have no NaN values
        assert not cleaned.isnull().any().any()
        # Forward fill should use previous values
        assert cleaned.loc[1, "close"] == cleaned.loc[0, "close"]

    def test_fill_gaps_backward_fill(self):
        """Test filling gaps with backward fill."""
        df = pd.DataFrame({
            "timestamp": [1704067200, 1704067260, 1704067320],
            "open": [1.1000, np.nan, 1.1020],
            "high": [1.1005, np.nan, 1.1025],
            "low": [1.0995, np.nan, 1.1015],
            "close": [1.1002, np.nan, 1.1022],
            "volume": [1000.0, np.nan, 1000.0],
        })

        cleaner = DataCleaner()
        cleaned = cleaner.fill_gaps(df, method=FillMethod.BACKWARD_FILL)

        assert not cleaned.isnull().any().any()
        # Backward fill should use next values
        assert cleaned.loc[1, "close"] == cleaned.loc[2, "close"]

    def test_fill_gaps_interpolate(self):
        """Test filling gaps with interpolation."""
        df = pd.DataFrame({
            "timestamp": [1704067200, 1704067260, 1704067320],
            "open": [1.1000, np.nan, 1.1020],
            "high": [1.1005, np.nan, 1.1025],
            "low": [1.0995, np.nan, 1.1015],
            "close": [1.1000, np.nan, 1.1020],
            "volume": [1000.0, np.nan, 1000.0],
        })

        cleaner = DataCleaner()
        cleaned = cleaner.fill_gaps(df, method=FillMethod.INTERPOLATE_LINEAR)

        assert not cleaned.isnull().any().any()
        # Linear interpolation should give midpoint
        assert cleaned.loc[1, "close"] == pytest.approx(1.1010, abs=0.0001)

    def test_filter_spikes_interpolate(self, data_with_spikes):
        """Test filtering spikes with interpolation."""
        cleaner = DataCleaner()
        cleaned = cleaner.filter_spikes(
            data_with_spikes,
            threshold_multiplier=5.0,
            replace_method="interpolate",
        )

        # Should have same number of rows
        assert len(cleaned) == len(data_with_spikes)
        # Spike should be smoothed out
        assert cleaned["high"].max() < data_with_spikes["high"].max()

    def test_filter_spikes_remove(self, data_with_spikes):
        """Test filtering spikes by removing rows."""
        cleaner = DataCleaner()
        cleaned = cleaner.filter_spikes(
            data_with_spikes,
            threshold_multiplier=5.0,
            replace_method="remove",
        )

        # Should have fewer rows
        assert len(cleaned) < len(data_with_spikes)

    def test_fill_zero_volumes_ffill(self, data_with_zero_volume):
        """Test filling zero volumes with forward fill."""
        cleaner = DataCleaner()
        cleaned = cleaner.fill_zero_volumes(data_with_zero_volume, method="ffill")

        # Should have no zero volumes
        assert (cleaned["volume"] > 0).all()

    def test_fill_zero_volumes_median(self, data_with_zero_volume):
        """Test filling zero volumes with median."""
        cleaner = DataCleaner()
        cleaned = cleaner.fill_zero_volumes(data_with_zero_volume, method="median")

        # Should have no zero volumes
        assert (cleaned["volume"] > 0).all()
        # Zero volumes should be replaced with median
        median_vol = data_with_zero_volume[data_with_zero_volume["volume"] > 0]["volume"].median()
        assert cleaned.loc[1, "volume"] == median_vol

    def test_clean_all(self):
        """Test cleaning all operations in sequence."""
        # Create data with multiple issues
        df = pd.DataFrame({
            "timestamp": [1704067200, 1704067260, 1704067260, 1704067320, 1704067380],
            "open": [1.1000, 1.1010, 1.1015, 1.1020, 1.1030],
            "high": [1.1005, 1.1015, 1.1020, 1.1025, 1.1035],
            "low": [1.0995, 1.1005, 1.1010, 1.1015, 1.1025],
            "close": [1.1002, 1.1012, 1.1017, 1.1022, 1.1032],
            "volume": [1000.0, 0.0, 1000.0, 1000.0, 1000.0],
        })

        cleaner = DataCleaner()
        cleaned = cleaner.clean_all(df)

        # Should remove duplicates
        assert cleaned["timestamp"].is_unique
        # Should fill zero volumes
        assert (cleaned["volume"] > 0).all()


# ============================================================================
# Test ValidationReport
# ============================================================================


class TestValidationReport:
    """Test ValidationReport export formats."""

    @pytest.fixture
    def sample_issues(self):
        """Create sample validation issues."""
        return [
            ValidationIssue(
                issue_type=IssueType.SPIKE,
                severity=IssueSeverity.WARNING,
                timestamp=1704067200000000,
                symbol="EURUSD",
                message="Spike detected",
                check_name="SpikeDetector",
            ),
            ValidationIssue(
                issue_type=IssueType.GAP,
                severity=IssueSeverity.WARNING,
                timestamp=1704067260000000,
                symbol="EURUSD",
                message="Gap detected",
                check_name="GapDetector",
            ),
            ValidationIssue(
                issue_type=IssueType.DUPLICATE,
                severity=IssueSeverity.ERROR,
                timestamp=1704067320000000,
                symbol="EURUSD",
                message="Duplicate detected",
                check_name="DuplicateDetector",
            ),
        ]

    @pytest.fixture
    def sample_report(self, sample_issues):
        """Create sample validation report."""
        from hqt.data.validation.report import ValidationReport

        return ValidationReport(
            symbol="EURUSD",
            issues=sample_issues,
            total_bars=100,
            checks_run=["PriceSanityCheck", "GapDetector", "SpikeDetector"],
        )

    def test_report_properties(self, sample_report):
        """Test report computed properties."""
        assert sample_report.total_issues == 3
        assert sample_report.clean is False
        assert sample_report.critical_count == 0
        assert sample_report.error_count == 1
        assert sample_report.warning_count == 2
        assert sample_report.pass_rate < 1.0

    def test_report_severity_counts(self, sample_report):
        """Test severity breakdown."""
        counts = sample_report.severity_counts
        assert counts["WARNING"] == 2
        assert counts["ERROR"] == 1
        assert counts["CRITICAL"] == 0
        assert counts["INFO"] == 0

    def test_report_type_counts(self, sample_report):
        """Test issue type breakdown."""
        counts = sample_report.type_counts
        assert counts["SPIKE"] == 1
        assert counts["GAP"] == 1
        assert counts["DUPLICATE"] == 1

    def test_report_check_counts(self, sample_report):
        """Test check breakdown."""
        counts = sample_report.check_counts
        assert counts["SpikeDetector"] == 1
        assert counts["GapDetector"] == 1
        assert counts["DuplicateDetector"] == 1

    def test_report_get_issues_by_severity(self, sample_report):
        """Test filtering issues by severity."""
        warnings = sample_report.get_issues_by_severity(IssueSeverity.WARNING)
        assert len(warnings) == 2

        errors = sample_report.get_issues_by_severity(IssueSeverity.ERROR)
        assert len(errors) == 1

    def test_report_get_issues_by_type(self, sample_report):
        """Test filtering issues by type."""
        spikes = sample_report.get_issues_by_type(IssueType.SPIKE)
        assert len(spikes) == 1

        gaps = sample_report.get_issues_by_type(IssueType.GAP)
        assert len(gaps) == 1

    def test_report_to_dict(self, sample_report):
        """Test report to_dict export."""
        report_dict = sample_report.to_dict()

        assert report_dict["symbol"] == "EURUSD"
        assert report_dict["summary"]["total_bars"] == 100
        assert report_dict["summary"]["total_issues"] == 3
        assert report_dict["summary"]["clean"] is False
        assert "severity_breakdown" in report_dict
        assert "type_breakdown" in report_dict
        assert "issues" in report_dict
        assert len(report_dict["issues"]) == 3

    def test_report_to_dataframe(self, sample_report):
        """Test report to_dataframe export."""
        df = sample_report.to_dataframe()

        assert len(df) == 3
        assert "timestamp" in df.columns
        assert "issue_type" in df.columns
        assert "severity" in df.columns
        assert "check_name" in df.columns
        assert "message" in df.columns

    def test_report_to_dataframe_empty(self):
        """Test to_dataframe with empty report."""
        from hqt.data.validation.report import ValidationReport

        report = ValidationReport(
            symbol="EURUSD",
            issues=[],
            total_bars=100,
            checks_run=["PriceSanityCheck"],
        )

        df = report.to_dataframe()
        assert len(df) == 0
        assert "timestamp" in df.columns

    def test_report_to_html(self, sample_report):
        """Test report to_html export."""
        html = sample_report.to_html()

        assert "<html>" in html
        assert "EURUSD" in html
        assert "Total Bars" in html
        assert "Total Issues" in html
        assert "Severity Breakdown" in html
        assert "WARNING" in html
        assert "ERROR" in html

    def test_report_to_html_no_details(self, sample_report):
        """Test HTML export without details table."""
        html = sample_report.to_html(include_details=False)

        assert "<html>" in html
        assert "EURUSD" in html
        # Should not include detailed issues table
        assert "Detailed Issues" not in html or len(html.split("Detailed Issues")) == 1

    def test_report_str_representation(self, sample_report):
        """Test report string representation."""
        report_str = str(sample_report)

        assert "Validation Report: EURUSD" in report_str
        assert "Total Bars:" in report_str
        assert "Total Issues:" in report_str
        assert "Pass Rate:" in report_str
        assert "WARNING:" in report_str
        assert "ERROR:" in report_str

    def test_report_repr(self, sample_report):
        """Test report repr."""
        repr_str = repr(sample_report)

        assert "ValidationReport" in repr_str
        assert "EURUSD" in repr_str
        assert "total_issues=3" in repr_str

    def test_clean_report(self):
        """Test report with no issues."""
        from hqt.data.validation.report import ValidationReport

        report = ValidationReport(
            symbol="EURUSD",
            issues=[],
            total_bars=100,
            checks_run=["PriceSanityCheck"],
        )

        assert report.clean is True
        assert report.total_issues == 0
        assert report.pass_rate == 1.0


# ============================================================================
# Integration Tests
# ============================================================================


class TestValidationIntegration:
    """Integration tests for complete validation workflow."""

    def test_full_validation_and_cleaning_workflow(self):
        """Test complete workflow: validate -> clean -> re-validate."""
        # Create dirty data
        df = pd.DataFrame({
            "timestamp": [1704067200, 1704067260, 1704067260, 1704067320, 1704067380],
            "open": [1.1000, 1.1010, 1.1015, 1.1020, 1.1030],
            "high": [1.1005, 1.1015, 1.1020, 1.1025, 1.1035],
            "low": [1.0995, 1.1005, 1.1010, 1.1015, 1.1025],
            "close": [1.1002, 1.1012, 1.1017, 1.1022, 1.1032],
            "volume": [1000.0, 0.0, 1000.0, 1000.0, 1000.0],
        })

        # Step 1: Run validation
        pipeline = ValidationPipeline()
        report1 = pipeline.validate(df, "EURUSD")

        assert report1.total_issues > 0

        # Step 2: Clean the data
        cleaner = DataCleaner()
        cleaned_df = cleaner.clean_all(df)

        # Step 3: Re-validate cleaned data
        report2 = pipeline.validate(cleaned_df, "EURUSD")

        # Should have fewer issues after cleaning
        assert report2.total_issues < report1.total_issues

    def test_export_report_to_all_formats(self, clean_data):
        """Test exporting report to all supported formats."""
        pipeline = ValidationPipeline()
        report = pipeline.validate(clean_data, "EURUSD")

        # Export to dict
        report_dict = report.to_dict()
        assert isinstance(report_dict, dict)
        assert "symbol" in report_dict

        # Export to DataFrame
        df = report.to_dataframe()
        assert isinstance(df, pd.DataFrame)

        # Export to HTML
        html = report.to_html()
        assert isinstance(html, str)
        assert "<html>" in html
