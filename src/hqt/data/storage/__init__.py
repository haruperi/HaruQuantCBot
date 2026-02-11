"""
Data storage layer for HQT Trading System.

This module provides persistent storage for tick and bar data with multiple
backends (Parquet, HDF5), metadata catalog, and storage management.

[REQ: DAT-FR-021 through DAT-FR-025]
[SDD: §5.2] Data Storage Architecture
"""

from hqt.data.storage.base import DataStore
from hqt.data.storage.catalog import DataCatalog
from hqt.data.storage.hdf5_store import HDF5Store
from hqt.data.storage.manager import PartitionStrategy, StorageManager
from hqt.data.storage.parquet_store import ParquetStore

__all__ = [
    # Base
    "DataStore",
    # Backends
    "ParquetStore",
    "HDF5Store",
    # Catalog
    "DataCatalog",
    # Management
    "StorageManager",
    "PartitionStrategy",
]
