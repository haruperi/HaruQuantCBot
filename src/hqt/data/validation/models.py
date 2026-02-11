"""
Validation data models for HQT Trading System.

This module defines the data structures for validation issues and results.

[REQ: DAT-FR-014] ValidationIssue model for reporting detected issues.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IssueSeverity(str, Enum):
    """
    Severity levels for validation issues.

    Attributes:
        INFO: Informational, does not affect data quality
        WARNING: Potentially problematic, should be reviewed
        ERROR: Significant data quality issue that should be fixed
        CRITICAL: Severe data quality issue that makes data unusable
    """

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class IssueType(str, Enum):
    """
    Types of validation issues that can be detected.

    Attributes:
        PRICE_SANITY: Price values violate sanity checks
        GAP: Large gap detected between consecutive bars
        SPIKE: Abnormal price spike detected
        MISSING_TIMESTAMP: Missing expected timestamp
        ZERO_VOLUME: Bar has zero volume
        DUPLICATE: Duplicate timestamp detected
        SPREAD_ANOMALY: Abnormal spread widening
        OHLC_INCONSISTENCY: OHLC values are inconsistent
    """

    PRICE_SANITY = "PRICE_SANITY"
    GAP = "GAP"
    SPIKE = "SPIKE"
    MISSING_TIMESTAMP = "MISSING_TIMESTAMP"
    ZERO_VOLUME = "ZERO_VOLUME"
    DUPLICATE = "DUPLICATE"
    SPREAD_ANOMALY = "SPREAD_ANOMALY"
    OHLC_INCONSISTENCY = "OHLC_INCONSISTENCY"


class ValidationIssue(BaseModel):
    """
    Represents a single data validation issue.

    A validation issue captures details about a data quality problem
    detected during validation, including the type, severity, location,
    and diagnostic information.

    Attributes:
        issue_type: Type of validation issue
        severity: Severity level of the issue
        timestamp: Timestamp where the issue occurred (microseconds)
        symbol: Trading symbol where the issue occurred
        message: Human-readable description of the issue
        details: Additional diagnostic information (optional)
        check_name: Name of the validation check that detected the issue

    Example:
        ```python
        issue = ValidationIssue(
            issue_type=IssueType.SPIKE,
            severity=IssueSeverity.WARNING,
            timestamp=1704067200000000,
            symbol="EURUSD",
            message="Price spike detected: range 0.00150 exceeds 5x ATR",
            details={"range": 0.00150, "atr": 0.00025, "threshold": 5.0},
            check_name="SpikeDetector",
        )
        ```
    """

    model_config = ConfigDict(
        frozen=True,  # Make instances immutable
        validate_assignment=True,
    )

    issue_type: IssueType = Field(..., description="Type of validation issue")
    severity: IssueSeverity = Field(..., description="Severity level")
    timestamp: int = Field(..., description="Timestamp in microseconds")
    symbol: str = Field(..., description="Trading symbol")
    message: str = Field(..., description="Human-readable issue description")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional diagnostic info")
    check_name: str = Field(..., description="Name of validation check")

    @property
    def datetime(self) -> datetime:
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(self.timestamp / 1_000_000.0)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert issue to dictionary representation.

        Returns:
            Dictionary with all issue fields.
        """
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "message": self.message,
            "details": self.details,
            "check_name": self.check_name,
        }

    def __repr__(self) -> str:
        """Return string representation of the validation issue."""
        return (
            f"ValidationIssue(type={self.issue_type.value}, "
            f"severity={self.severity.value}, symbol={self.symbol}, "
            f"timestamp={self.timestamp})"
        )
