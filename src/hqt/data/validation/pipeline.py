"""
Validation pipeline orchestrator for HQT Trading System.

This module provides the ValidationPipeline class that orchestrates
all validation checks and produces a comprehensive ValidationReport.

[REQ: DAT-FR-014, DAT-FR-015] Validation pipeline with configurable checks.
"""

from typing import Any

import pandas as pd

from hqt.data.validation.checks import (
    DuplicateDetector,
    GapDetector,
    MissingTimestampDetector,
    PriceSanityCheck,
    SpikeDetector,
    SpreadAnalyzer,
    Validator,
    ZeroVolumeDetector,
)
from hqt.data.validation.models import IssueSeverity, ValidationIssue


class ValidationConfig:
    """
    Configuration for validation pipeline.

    Allows per-symbol and per-source customization of validation thresholds.

    Attributes:
        price_bound_multiplier: Max price deviation from median
        gap_threshold_multiplier: Multiplier of avg range for gap detection
        spike_threshold_multiplier: Multiplier of ATR for spike detection
        spike_atr_period: Period for ATR calculation
        spread_threshold_multiplier: Multiplier of median spread
        expected_interval_seconds: Expected interval between bars (None = auto-detect)
        enabled_checks: List of check names to run (None = all)

    Example:
        ```python
        # Custom config for gold (more volatile)
        gold_config = ValidationConfig(
            spike_threshold_multiplier=10.0,  # Higher threshold
            gap_threshold_multiplier=20.0,
        )

        # Forex config (tighter thresholds)
        forex_config = ValidationConfig(
            spike_threshold_multiplier=3.0,
            spread_threshold_multiplier=2.0,
        )
        ```
    """

    def __init__(
        self,
        price_bound_multiplier: float = 10.0,
        gap_threshold_multiplier: float = 10.0,
        spike_threshold_multiplier: float = 5.0,
        spike_atr_period: int = 14,
        spread_threshold_multiplier: float = 3.0,
        expected_interval_seconds: int | None = None,
        enabled_checks: list[str] | None = None,
    ):
        """Initialize validation configuration."""
        self.price_bound_multiplier = price_bound_multiplier
        self.gap_threshold_multiplier = gap_threshold_multiplier
        self.spike_threshold_multiplier = spike_threshold_multiplier
        self.spike_atr_period = spike_atr_period
        self.spread_threshold_multiplier = spread_threshold_multiplier
        self.expected_interval_seconds = expected_interval_seconds
        self.enabled_checks = enabled_checks


class ValidationPipeline:
    """
    Orchestrates all validation checks and produces a comprehensive report.

    The pipeline runs checks sequentially in a logical order:
    1. PriceSanityCheck - fundamental data integrity
    2. DuplicateDetector - clean data structure
    3. GapDetector - continuity issues
    4. SpikeDetector - price anomalies
    5. MissingTimestampDetector - completeness
    6. ZeroVolumeDetector - volume quality
    7. SpreadAnalyzer - spread anomalies

    [REQ: DAT-FR-014, DAT-FR-015] Complete validation pipeline.

    Example:
        ```python
        from hqt.data.validation import ValidationPipeline, ValidationConfig

        # Create pipeline with custom config
        config = ValidationConfig(spike_threshold_multiplier=10.0)
        pipeline = ValidationPipeline(config=config)

        # Run validation
        report = pipeline.validate(df, symbol="XAUUSD")

        # Check results
        print(f"Total issues: {report.total_issues}")
        print(f"Critical: {report.critical_count}")
        ```
    """

    def __init__(self, config: ValidationConfig | None = None):
        """
        Initialize validation pipeline.

        Args:
            config: Validation configuration (None = use defaults)
        """
        self.config = config or ValidationConfig()
        self._validators: list[Validator] = []
        self._initialize_validators()

    def _initialize_validators(self) -> None:
        """Initialize all validators based on configuration."""
        # Always run in this order for logical flow
        all_validators = [
            PriceSanityCheck(
                price_bound_multiplier=self.config.price_bound_multiplier,
                severity=IssueSeverity.CRITICAL,
            ),
            DuplicateDetector(severity=IssueSeverity.ERROR),
            GapDetector(
                threshold_multiplier=self.config.gap_threshold_multiplier,
                severity=IssueSeverity.WARNING,
            ),
            SpikeDetector(
                threshold_multiplier=self.config.spike_threshold_multiplier,
                atr_period=self.config.spike_atr_period,
                severity=IssueSeverity.WARNING,
            ),
            MissingTimestampDetector(
                expected_interval_seconds=self.config.expected_interval_seconds,
                severity=IssueSeverity.WARNING,
            ),
            ZeroVolumeDetector(severity=IssueSeverity.INFO),
            SpreadAnalyzer(
                threshold_multiplier=self.config.spread_threshold_multiplier,
                severity=IssueSeverity.WARNING,
            ),
        ]

        # Filter by enabled checks if specified
        if self.config.enabled_checks is not None:
            enabled_set = set(self.config.enabled_checks)
            self._validators = [v for v in all_validators if v.name in enabled_set]
        else:
            self._validators = all_validators

    def validate(
        self,
        df: pd.DataFrame,
        symbol: str,
        required_columns: list[str] | None = None,
        **kwargs: Any,
    ) -> "ValidationReport":
        """
        Run all validation checks on the data.

        Args:
            df: DataFrame with OHLCV or tick data
            symbol: Trading symbol being validated
            required_columns: List of required columns (None = use OHLC defaults)
            **kwargs: Additional parameters passed to validators

        Returns:
            ValidationReport with all detected issues

        Raises:
            ValueError: If DataFrame is empty or missing required columns
        """
        # Validate input
        if df.empty:
            raise ValueError("Cannot validate empty DataFrame")

        # Default required columns if none provided
        if required_columns is None:
            required_columns = ["timestamp", "open", "high", "low", "close"]

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"DataFrame missing required columns: {missing_columns}")

        # Run all validators
        all_issues: list[ValidationIssue] = []

        for validator in self._validators:
            try:
                # Basic check: skip OHLC-specific validators if columns are missing
                # (Relevant for validate_ticks calling a pipeline with bar validators)
                ohlc_cols = ["open", "high", "low", "close"]
                is_ohlc_check = any(c in validator.name.lower() for c in ["price", "gap", "spike", "spread"])
                has_ohlc = all(c in df.columns for c in ohlc_cols)

                if is_ohlc_check and not has_ohlc:
                    continue

                issues = validator.validate(df, symbol, **kwargs)
                all_issues.extend(issues)
            except Exception as e:
                # Log error but continue with other validators
                print(f"Warning: {validator.name} failed: {e}")
                continue

        # Create and return report
        from hqt.data.validation.report import ValidationReport

        return ValidationReport(
            symbol=symbol,
            issues=all_issues,
            total_bars=len(df),
            checks_run=[v.name for v in self._validators],
        )

    def validate_bars(
        self,
        df: pd.DataFrame,
        symbol: str,
        **kwargs: Any,
    ) -> "ValidationReport":
        """
        Run validation pipeline for bar data.

        [REQ: DAT-FR-014] Bar validation.
        """
        required_columns = ["timestamp", "open", "high", "low", "close"]
        return self.validate(df, symbol, required_columns=required_columns, **kwargs)

    def validate_ticks(
        self,
        df: pd.DataFrame,
        symbol: str,
        **kwargs: Any,
    ) -> "ValidationReport":
        """
        Run validation pipeline for tick data.

        [REQ: DAT-FR-015] Tick validation.
        """
        required_columns = ["timestamp", "bid", "ask"]
        return self.validate(df, symbol, required_columns=required_columns, **kwargs)

    def add_validator(self, validator: Validator) -> None:
        """
        Add a custom validator to the pipeline.

        Args:
            validator: Custom validator instance

        Example:
            ```python
            pipeline = ValidationPipeline()
            pipeline.add_validator(MyCustomValidator())
            ```
        """
        self._validators.append(validator)

    def remove_validator(self, validator_name: str) -> bool:
        """
        Remove a validator from the pipeline.

        Args:
            validator_name: Name of the validator to remove

        Returns:
            True if validator was removed, False if not found
        """
        initial_count = len(self._validators)
        self._validators = [v for v in self._validators if v.name != validator_name]
        return len(self._validators) < initial_count

    @property
    def validators(self) -> list[str]:
        """Get list of validator names in the pipeline."""
        return [v.name for v in self._validators]
