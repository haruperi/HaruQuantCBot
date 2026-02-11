"""
Data versioning and lineage tracking for HQT Trading System.

This module provides content hashing, lineage tracking, and manifest
generation for data reproducibility and version control.

[REQ: DAT-FR-026 through DAT-FR-029]
[SDD: §5.2] Data Storage Architecture
"""

from hqt.data.versioning.hasher import (
    compute_dataframe_hash,
    compute_file_hash,
    compute_hash,
    compute_hash_incremental,
    verify_file_hash,
    verify_hash,
)
from hqt.data.versioning.lineage import DataLineage
from hqt.data.versioning.manifest import DataManifest

__all__ = [
    # Hashing
    "compute_hash",
    "compute_file_hash",
    "compute_dataframe_hash",
    "compute_hash_incremental",
    "verify_hash",
    "verify_file_hash",
    # Lineage
    "DataLineage",
    # Manifest
    "DataManifest",
]
