"""
Data validation checks for HQT Trading System.

This module implements all validation checks for market data quality.
Each check analyzes data for specific issues and returns ValidationIssue
objects.

[REQ: DAT-FR-006 through DAT-FR-012] Complete validation check implementation.
"""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd

from hqt.data.validation.models import IssueSeverity, IssueType, ValidationIssue


class Validator(ABC):
    """
    Base class for all data validation checks.

    Each validator implements a specific check and returns a list
    of ValidationIssue objects for any problems detected.
    """

    @abstractmethod
    def validate(
        self,
        df: pd.DataFrame,
        symbol: str,
        **kwargs: Any,
    ) -> list[ValidationIssue]:
        """
        Perform validation check on data.

        Args:
            df: DataFrame with OHLCV data (columns: timestamp, open, high, low, close, volume)
            symbol: Trading symbol being validated
            **kwargs: Additional configuration parameters

        Returns:
            List of ValidationIssue objects (empty if no issues found)
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this validator."""
        pass


class PriceSanityCheck(Validator):
    """
    Validates basic price sanity rules.

    Checks:
    - All prices are positive (> 0)
    - High >= max(open, close)
    - Low <= min(open, close)
    - High >= low
    - Prices are within reasonable bounds (configurable multiplier of median)

    [REQ: DAT-FR-006] Price sanity validation.
    """

    def __init__(
        self,
        price_bound_multiplier: float = 10.0,
        severity: IssueSeverity = IssueSeverity.CRITICAL,
    ):
        """
        Initialize price sanity checker.

        Args:
            price_bound_multiplier: Maximum allowed multiplier from median price
            severity: Severity level for detected issues
        """
        self.price_bound_multiplier = price_bound_multiplier
        self.severity = severity

    @property
    def name(self) -> str:
        return "PriceSanityCheck"

    def validate(
        self,
        df: pd.DataFrame,
        symbol: str,
        **kwargs: Any,
    ) -> list[ValidationIssue]:
        """Validate price sanity rules."""
        issues: list[ValidationIssue] = []

        if df.empty:
            return issues

        # Check 1: All prices must be positive
        negative_mask = (
            (df["open"] <= 0)
            | (df["high"] <= 0)
            | (df["low"] <= 0)
            | (df["close"] <= 0)
        )

        for idx in df[negative_mask].index:
            row = df.loc[idx]
            issues.append(
                ValidationIssue(
                    issue_type=IssueType.PRICE_SANITY,
                    severity=self.severity,
                    timestamp=int(row["timestamp"]),
                    symbol=symbol,
                    message=f"Non-positive price detected: O={row['open']}, H={row['high']}, L={row['low']}, C={row['close']}",
                    details={
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                    },
                    check_name=self.name,
                )
            )

        # Check 2: High >= max(open, close)
        max_oc = df[["open", "close"]].max(axis=1)
        high_violation_mask = df["high"] < max_oc

        for idx in df[high_violation_mask].index:
            row = df.loc[idx]
            issues.append(
                ValidationIssue(
                    issue_type=IssueType.OHLC_INCONSISTENCY,
                    severity=self.severity,
                    timestamp=int(row["timestamp"]),
                    symbol=symbol,
                    message=f"High ({row['high']}) < max(open, close) ({max_oc[idx]})",
                    details={
                        "high": float(row["high"]),
                        "open": float(row["open"]),
                        "close": float(row["close"]),
                        "max_oc": float(max_oc[idx]),
                    },
                    check_name=self.name,
                )
            )

        # Check 3: Low <= min(open, close)
        min_oc = df[["open", "close"]].min(axis=1)
        low_violation_mask = df["low"] > min_oc

        for idx in df[low_violation_mask].index:
            row = df.loc[idx]
            issues.append(
                ValidationIssue(
                    issue_type=IssueType.OHLC_INCONSISTENCY,
                    severity=self.severity,
                    timestamp=int(row["timestamp"]),
                    symbol=symbol,
                    message=f"Low ({row['low']}) > min(open, close) ({min_oc[idx]})",
                    details={
                        "low": float(row["low"]),
                        "open": float(row["open"]),
                        "close": float(row["close"]),
                        "min_oc": float(min_oc[idx]),
                    },
                    check_name=self.name,
                )
            )

        # Check 4: High >= low
        hl_violation_mask = df["high"] < df["low"]

        for idx in df[hl_violation_mask].index:
            row = df.loc[idx]
            issues.append(
                ValidationIssue(
                    issue_type=IssueType.OHLC_INCONSISTENCY,
                    severity=self.severity,
                    timestamp=int(row["timestamp"]),
                    symbol=symbol,
                    message=f"High ({row['high']}) < Low ({row['low']})",
                    details={
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                    },
                    check_name=self.name,
                )
            )

        # Check 5: Prices within reasonable bounds
        median_close = df["close"].median()
        upper_bound = median_close * self.price_bound_multiplier
        lower_bound = median_close / self.price_bound_multiplier

        out_of_bounds_mask = (
            (df["close"] > upper_bound) | (df["close"] < lower_bound)
        )

        for idx in df[out_of_bounds_mask].index:
            row = df.loc[idx]
            issues.append(
                ValidationIssue(
                    issue_type=IssueType.PRICE_SANITY,
                    severity=IssueSeverity.WARNING,  # Less severe than other sanity issues
                    timestamp=int(row["timestamp"]),
                    symbol=symbol,
                    message=f"Price {row['close']} outside reasonable bounds [{lower_bound:.5f}, {upper_bound:.5f}]",
                    details={
                        "close": float(row["close"]),
                        "median": float(median_close),
                        "lower_bound": float(lower_bound),
                        "upper_bound": float(upper_bound),
                    },
                    check_name=self.name,
                )
            )

        return issues


class GapDetector(Validator):
    """
    Detects large gaps between consecutive bars.

    A gap is defined as the distance between consecutive close prices
    exceeding a threshold multiple of the average range.

    [REQ: DAT-FR-007] Gap detection.
    """

    def __init__(
        self,
        threshold_multiplier: float = 10.0,
        severity: IssueSeverity = IssueSeverity.WARNING,
    ):
        """
        Initialize gap detector.

        Args:
            threshold_multiplier: Multiplier of average range to trigger gap detection
            severity: Severity level for detected gaps
        """
        self.threshold_multiplier = threshold_multiplier
        self.severity = severity

    @property
    def name(self) -> str:
        return "GapDetector"

    def validate(
        self,
        df: pd.DataFrame,
        symbol: str,
        **kwargs: Any,
    ) -> list[ValidationIssue]:
        """Detect price gaps."""
        issues: list[ValidationIssue] = []

        if len(df) < 2:
            return issues

        # Calculate bar ranges
        df_copy = df.copy()
        df_copy["range"] = df_copy["high"] - df_copy["low"]
        avg_range = df_copy["range"].mean()

        if avg_range == 0:
            return issues  # No range to compare against

        threshold = avg_range * self.threshold_multiplier

        # Calculate gaps (absolute difference between consecutive closes)
        df_copy["close_diff"] = df_copy["close"].diff().abs()

        # Find gaps exceeding threshold
        gap_mask = df_copy["close_diff"] > threshold

        for idx in df_copy[gap_mask].index:
            row = df_copy.loc[idx]
            prev_close = df_copy.loc[idx - 1, "close"] if idx > 0 else row["close"]

            issues.append(
                ValidationIssue(
                    issue_type=IssueType.GAP,
                    severity=self.severity,
                    timestamp=int(row["timestamp"]),
                    symbol=symbol,
                    message=f"Gap detected: {row['close_diff']:.5f} exceeds {self.threshold_multiplier}x avg range ({threshold:.5f})",
                    details={
                        "gap_size": float(row["close_diff"]),
                        "prev_close": float(prev_close),
                        "current_close": float(row["close"]),
                        "avg_range": float(avg_range),
                        "threshold": float(threshold),
                    },
                    check_name=self.name,
                )
            )

        return issues


class SpikeDetector(Validator):
    """
    Detects abnormal price spikes using ATR (Average True Range).

    A spike is detected when a bar's range exceeds a threshold multiple
    of the ATR.

    [REQ: DAT-FR-008] Spike detection using ATR.
    """

    def __init__(
        self,
        threshold_multiplier: float = 5.0,
        atr_period: int = 14,
        severity: IssueSeverity = IssueSeverity.WARNING,
    ):
        """
        Initialize spike detector.

        Args:
            threshold_multiplier: Multiplier of ATR to trigger spike detection
            atr_period: Period for ATR calculation
            severity: Severity level for detected spikes
        """
        self.threshold_multiplier = threshold_multiplier
        self.atr_period = atr_period
        self.severity = severity

    @property
    def name(self) -> str:
        return "SpikeDetector"

    def validate(
        self,
        df: pd.DataFrame,
        symbol: str,
        **kwargs: Any,
    ) -> list[ValidationIssue]:
        """Detect price spikes."""
        issues: list[ValidationIssue] = []

        if len(df) < self.atr_period:
            return issues  # Not enough data for ATR calculation

        df_copy = df.copy()

        # Calculate True Range
        df_copy["prev_close"] = df_copy["close"].shift(1)
        df_copy["tr1"] = df_copy["high"] - df_copy["low"]
        df_copy["tr2"] = abs(df_copy["high"] - df_copy["prev_close"])
        df_copy["tr3"] = abs(df_copy["low"] - df_copy["prev_close"])
        df_copy["true_range"] = df_copy[["tr1", "tr2", "tr3"]].max(axis=1)

        # Calculate ATR (simple moving average of True Range)
        df_copy["atr"] = df_copy["true_range"].rolling(window=self.atr_period).mean()

        # Calculate bar range
        df_copy["range"] = df_copy["high"] - df_copy["low"]

        # Find spikes (range > threshold * ATR)
        df_copy["spike_threshold"] = df_copy["atr"] * self.threshold_multiplier
        spike_mask = (df_copy["range"] > df_copy["spike_threshold"]) & (
            df_copy["atr"].notna()
        )

        for idx in df_copy[spike_mask].index:
            row = df_copy.loc[idx]

            issues.append(
                ValidationIssue(
                    issue_type=IssueType.SPIKE,
                    severity=self.severity,
                    timestamp=int(row["timestamp"]),
                    symbol=symbol,
                    message=f"Spike detected: range {row['range']:.5f} exceeds {self.threshold_multiplier}x ATR ({row['spike_threshold']:.5f})",
                    details={
                        "range": float(row["range"]),
                        "atr": float(row["atr"]),
                        "threshold_multiplier": self.threshold_multiplier,
                        "spike_threshold": float(row["spike_threshold"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                    },
                    check_name=self.name,
                )
            )

        return issues


class MissingTimestampDetector(Validator):
    """
    Detects missing timestamps based on expected interval.

    Checks for gaps in the timestamp sequence that exceed the expected
    interval between bars.

    [REQ: DAT-FR-009] Missing timestamp detection.
    """

    def __init__(
        self,
        expected_interval_seconds: int = 60,
        tolerance: float = 1.5,
        severity: IssueSeverity = IssueSeverity.WARNING,
    ):
        """
        Initialize missing timestamp detector.

        Args:
            expected_interval_seconds: Expected interval between bars in seconds
            tolerance: Multiplier for interval to allow some flexibility
            severity: Severity level for detected missing timestamps
        """
        self.expected_interval_seconds = expected_interval_seconds
        self.tolerance = tolerance
        self.severity = severity

    @property
    def name(self) -> str:
        return "MissingTimestampDetector"

    def validate(
        self,
        df: pd.DataFrame,
        symbol: str,
        **kwargs: Any,
    ) -> list[ValidationIssue]:
        """Detect missing timestamps."""
        issues: list[ValidationIssue] = []

        if len(df) < 2:
            return issues

        df_copy = df.copy()

        # Calculate time differences between consecutive timestamps
        df_copy["time_diff"] = df_copy["timestamp"].diff()

        # Threshold for detecting missing timestamps
        threshold = self.expected_interval_seconds * self.tolerance

        # Find gaps exceeding threshold
        missing_mask = df_copy["time_diff"] > threshold

        for idx in df_copy[missing_mask].index:
            row = df_copy.loc[idx]
            prev_timestamp = df_copy.loc[idx - 1, "timestamp"] if idx > 0 else row["timestamp"]
            gap_seconds = row["time_diff"]
            expected_bars = int(gap_seconds / self.expected_interval_seconds)

            issues.append(
                ValidationIssue(
                    issue_type=IssueType.MISSING_TIMESTAMP,
                    severity=self.severity,
                    timestamp=int(row["timestamp"]),
                    symbol=symbol,
                    message=f"Missing timestamps detected: {gap_seconds:.0f}s gap (expected ~{self.expected_interval_seconds}s, ~{expected_bars} bars missing)",
                    details={
                        "gap_seconds": float(gap_seconds),
                        "expected_interval": self.expected_interval_seconds,
                        "prev_timestamp": int(prev_timestamp),
                        "current_timestamp": int(row["timestamp"]),
                        "estimated_missing_bars": expected_bars,
                    },
                    check_name=self.name,
                )
            )

        return issues


class ZeroVolumeDetector(Validator):
    """
    Detects bars with zero or missing volume.

    Identifies bars where volume is zero, negative, or null, which
    may indicate data quality issues.

    [REQ: DAT-FR-010] Zero volume detection.
    """

    def __init__(
        self,
        severity: IssueSeverity = IssueSeverity.WARNING,
    ):
        """
        Initialize zero volume detector.

        Args:
            severity: Severity level for detected zero volume bars
        """
        self.severity = severity

    @property
    def name(self) -> str:
        return "ZeroVolumeDetector"

    def validate(
        self,
        df: pd.DataFrame,
        symbol: str,
        **kwargs: Any,
    ) -> list[ValidationIssue]:
        """Detect zero or missing volume."""
        issues: list[ValidationIssue] = []

        if df.empty:
            return issues

        # Check for zero, negative, or null volume
        zero_volume_mask = (
            (df["volume"] <= 0) | (df["volume"].isna())
        )

        for idx in df[zero_volume_mask].index:
            row = df.loc[idx]
            volume_value = row["volume"] if not pd.isna(row["volume"]) else None

            issues.append(
                ValidationIssue(
                    issue_type=IssueType.ZERO_VOLUME,
                    severity=self.severity,
                    timestamp=int(row["timestamp"]),
                    symbol=symbol,
                    message=f"Zero or invalid volume detected: {volume_value}",
                    details={
                        "volume": float(volume_value) if volume_value is not None else None,
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                    },
                    check_name=self.name,
                )
            )

        return issues


class DuplicateDetector(Validator):
    """
    Detects duplicate timestamps.

    Identifies cases where the same timestamp appears multiple times,
    which indicates data corruption or feed issues.

    [REQ: DAT-FR-011] Duplicate timestamp detection.
    """

    def __init__(
        self,
        severity: IssueSeverity = IssueSeverity.CRITICAL,
    ):
        """
        Initialize duplicate detector.

        Args:
            severity: Severity level for detected duplicates
        """
        self.severity = severity

    @property
    def name(self) -> str:
        return "DuplicateDetector"

    def validate(
        self,
        df: pd.DataFrame,
        symbol: str,
        **kwargs: Any,
    ) -> list[ValidationIssue]:
        """Detect duplicate timestamps."""
        issues: list[ValidationIssue] = []

        if df.empty:
            return issues

        # Find duplicate timestamps
        duplicate_mask = df["timestamp"].duplicated(keep=False)

        if not duplicate_mask.any():
            return issues

        # Group duplicates by timestamp
        duplicates = df[duplicate_mask].groupby("timestamp")

        for timestamp, group in duplicates:
            count = len(group)

            # Create issue for each duplicate occurrence
            for idx in group.index:
                row = df.loc[idx]

                issues.append(
                    ValidationIssue(
                        issue_type=IssueType.DUPLICATE,
                        severity=self.severity,
                        timestamp=int(timestamp),
                        symbol=symbol,
                        message=f"Duplicate timestamp detected: {timestamp} appears {count} times",
                        details={
                            "timestamp": int(timestamp),
                            "duplicate_count": count,
                            "open": float(row["open"]),
                            "high": float(row["high"]),
                            "low": float(row["low"]),
                            "close": float(row["close"]),
                            "volume": float(row["volume"]),
                        },
                        check_name=self.name,
                    )
                )

        return issues


class SpreadAnalyzer(Validator):
    """
    Detects abnormal spread widening.

    Identifies bars where the spread (high - low) exceeds a threshold
    multiple of the median spread, which may indicate data quality issues
    or unusual market conditions.

    [REQ: DAT-FR-012] Spread analysis and anomaly detection.
    """

    def __init__(
        self,
        threshold_multiplier: float = 3.0,
        min_periods: int = 20,
        severity: IssueSeverity = IssueSeverity.WARNING,
    ):
        """
        Initialize spread analyzer.

        Args:
            threshold_multiplier: Multiplier of median spread to trigger detection
            min_periods: Minimum number of bars required for analysis
            severity: Severity level for detected spread anomalies
        """
        self.threshold_multiplier = threshold_multiplier
        self.min_periods = min_periods
        self.severity = severity

    @property
    def name(self) -> str:
        return "SpreadAnalyzer"

    def validate(
        self,
        df: pd.DataFrame,
        symbol: str,
        **kwargs: Any,
    ) -> list[ValidationIssue]:
        """Detect abnormal spread widening."""
        issues: list[ValidationIssue] = []

        if len(df) < self.min_periods:
            return issues  # Not enough data for analysis

        df_copy = df.copy()

        # Calculate spread for each bar
        df_copy["spread"] = df_copy["high"] - df_copy["low"]

        # Calculate median spread
        median_spread = df_copy["spread"].median()

        if median_spread == 0:
            return issues  # Cannot calculate threshold with zero median

        # Threshold for abnormal spread
        threshold = median_spread * self.threshold_multiplier

        # Find bars with abnormal spread
        abnormal_mask = df_copy["spread"] > threshold

        for idx in df_copy[abnormal_mask].index:
            row = df_copy.loc[idx]
            spread_ratio = row["spread"] / median_spread

            issues.append(
                ValidationIssue(
                    issue_type=IssueType.SPREAD_ANOMALY,
                    severity=self.severity,
                    timestamp=int(row["timestamp"]),
                    symbol=symbol,
                    message=f"Abnormal spread detected: {row['spread']:.5f} is {spread_ratio:.2f}x median ({median_spread:.5f}), exceeds {self.threshold_multiplier}x threshold",
                    details={
                        "spread": float(row["spread"]),
                        "median_spread": float(median_spread),
                        "threshold": float(threshold),
                        "spread_ratio": float(spread_ratio),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                    },
                    check_name=self.name,
                )
            )

        return issues
