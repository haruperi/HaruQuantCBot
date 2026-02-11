"""
Data validation pipeline for HQT Trading System.

This module provides comprehensive data validation, cleaning, and reporting.

[REQ: DAT-FR-006 through DAT-FR-015] Complete validation infrastructure.
"""

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
from hqt.data.validation.cleaning import DataCleaner, FillMethod
from hqt.data.validation.models import (
    IssueSeverity,
    IssueType,
    ValidationIssue,
)
from hqt.data.validation.pipeline import ValidationConfig, ValidationPipeline
from hqt.data.validation.report import ValidationReport

__all__ = [
    # Models
    "ValidationIssue",
    "IssueSeverity",
    "IssueType",
    # Validators
    "Validator",
    "PriceSanityCheck",
    "GapDetector",
    "SpikeDetector",
    "MissingTimestampDetector",
    "ZeroVolumeDetector",
    "DuplicateDetector",
    "SpreadAnalyzer",
    # Pipeline
    "ValidationPipeline",
    "ValidationConfig",
    # Report
    "ValidationReport",
    # Cleaning
    "DataCleaner",
    "FillMethod",
]
