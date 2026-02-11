"""
Content hashing utilities for HQT Trading System.

This module provides SHA-256 hashing functions for data versioning and
reproducibility verification.

[REQ: DAT-FR-026] Version identifier (content hash)
[SDD: §5.2] Data Storage Architecture
"""

import hashlib
from pathlib import Path

import pandas as pd


def compute_hash(data: bytes) -> str:
    """
    Compute SHA-256 hash of bytes.

    Args:
        data: Bytes to hash

    Returns:
        Hexadecimal hash string (64 characters)

    Example:
        ```python
        from hqt.data.versioning import compute_hash

        data = b"Hello, World!"
        hash_value = compute_hash(data)
        print(f"Hash: {hash_value}")
        # Hash: dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f
        ```
    """
    return hashlib.sha256(data).hexdigest()


def compute_file_hash(file_path: str | Path, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 hash of a file.

    Reads file in chunks to handle large files efficiently.

    Args:
        file_path: Path to file
        chunk_size: Read chunk size in bytes (default: 8192)

    Returns:
        Hexadecimal hash string

    Raises:
        FileNotFoundError: File not found

    Example:
        ```python
        from hqt.data.versioning import compute_file_hash

        hash_value = compute_file_hash("data/parquet/EURUSD/H1/2024.parquet")
        print(f"File hash: {hash_value}")
        ```
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)

    return sha256.hexdigest()


def compute_dataframe_hash(df: pd.DataFrame) -> str:
    """
    Compute SHA-256 hash of DataFrame content.

    Uses timestamp and representative price columns (close/ask) as signature
    to avoid hashing all columns. This provides sufficient uniqueness while
    being efficient.

    Args:
        df: DataFrame to hash

    Returns:
        Hexadecimal hash string

    Example:
        ```python
        from hqt.data.versioning import compute_dataframe_hash
        import pandas as pd

        bars = pd.DataFrame({
            'timestamp': [1000, 2000, 3000],
            'close': [1.1, 1.2, 1.3],
            ...
        })

        hash_value = compute_dataframe_hash(bars)
        print(f"DataFrame hash: {hash_value}")
        ```

    Note:
        For bars: uses timestamp + close
        For ticks: uses timestamp + ask
        Fallback: uses timestamp only if close/ask not present
    """
    if len(df) == 0:
        return hashlib.sha256(b"").hexdigest()

    # Select columns for signature
    if "close" in df.columns:
        # Bars
        signature = df[["timestamp", "close"]].to_numpy().tobytes()
    elif "ask" in df.columns:
        # Ticks
        signature = df[["timestamp", "ask"]].to_numpy().tobytes()
    else:
        # Fallback: timestamp only
        signature = df["timestamp"].to_numpy().tobytes()

    return hashlib.sha256(signature).hexdigest()


def compute_hash_incremental(
    file_paths: list[str | Path],
    chunk_size: int = 8192,
) -> str:
    """
    Compute combined SHA-256 hash of multiple files.

    Useful for hashing a collection of data files as a single version.

    Args:
        file_paths: List of file paths to hash
        chunk_size: Read chunk size in bytes

    Returns:
        Hexadecimal hash string

    Raises:
        FileNotFoundError: Any file not found

    Example:
        ```python
        from hqt.data.versioning import compute_hash_incremental

        files = [
            "data/parquet/EURUSD/H1/2024.parquet",
            "data/parquet/EURUSD/H1/2025.parquet",
        ]

        combined_hash = compute_hash_incremental(files)
        print(f"Combined hash: {combined_hash}")
        ```

    Note:
        Files are hashed in the order provided. Different order produces
        different hash.
    """
    sha256 = hashlib.sha256()

    for file_path in file_paths:
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256.update(chunk)

    return sha256.hexdigest()


def verify_hash(data: bytes, expected_hash: str) -> bool:
    """
    Verify data matches expected hash.

    Args:
        data: Bytes to verify
        expected_hash: Expected SHA-256 hash (hexadecimal)

    Returns:
        True if hash matches, False otherwise

    Example:
        ```python
        from hqt.data.versioning import compute_hash, verify_hash

        data = b"Hello, World!"
        hash_value = compute_hash(data)

        # Later, verify data hasn't changed
        is_valid = verify_hash(data, hash_value)
        print(f"Valid: {is_valid}")  # True
        ```
    """
    actual_hash = compute_hash(data)
    return actual_hash == expected_hash


def verify_file_hash(file_path: str | Path, expected_hash: str) -> bool:
    """
    Verify file matches expected hash.

    Args:
        file_path: Path to file
        expected_hash: Expected SHA-256 hash (hexadecimal)

    Returns:
        True if hash matches, False otherwise

    Raises:
        FileNotFoundError: File not found

    Example:
        ```python
        from hqt.data.versioning import compute_file_hash, verify_file_hash

        # Record hash
        hash_value = compute_file_hash("data.parquet")

        # Later, verify file hasn't changed
        is_valid = verify_file_hash("data.parquet", hash_value)
        if not is_valid:
            print("Warning: File has been modified!")
        ```
    """
    actual_hash = compute_file_hash(file_path)
    return actual_hash == expected_hash
