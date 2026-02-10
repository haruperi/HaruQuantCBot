"""
General helper utilities for the HQT trading system.

This module provides general-purpose utility functions for common operations
like deep merging dictionaries, generating UUIDs, hashing files, and formatting sizes.
"""

import hashlib
import uuid
from pathlib import Path
from typing import Any


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge two dictionaries.

    Recursively merges overlay into base. For nested dictionaries, performs
    deep merge. For other values, overlay takes precedence.

    Args:
        base: Base dictionary
        overlay: Overlay dictionary (values take precedence)

    Returns:
        Merged dictionary (new dict, does not modify inputs)

    Example:
        ```python
        from hqt.foundation.utils import deep_merge

        base = {
            "a": 1,
            "b": {"x": 10, "y": 20},
            "c": [1, 2, 3]
        }

        overlay = {
            "b": {"y": 25, "z": 30},
            "d": 4
        }

        merged = deep_merge(base, overlay)
        # {
        #     "a": 1,
        #     "b": {"x": 10, "y": 25, "z": 30},  # Deep merged
        #     "c": [1, 2, 3],
        #     "d": 4
        # }
        ```
    """
    import copy

    result = copy.deepcopy(base)

    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = deep_merge(result[key], value)
        else:
            # Overlay value takes precedence
            result[key] = copy.deepcopy(value)

    return result


def flatten_dict(
    d: dict[str, Any],
    parent_key: str = "",
    sep: str = ".",
) -> dict[str, Any]:
    """
    Flatten a nested dictionary.

    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix (used internally for recursion)
        sep: Separator for flattened keys (default ".")

    Returns:
        Flattened dictionary

    Example:
        ```python
        from hqt.foundation.utils import flatten_dict

        nested = {
            "a": 1,
            "b": {
                "x": 10,
                "y": {
                    "z": 20
                }
            },
            "c": [1, 2, 3]
        }

        flat = flatten_dict(nested)
        # {
        #     "a": 1,
        #     "b.x": 10,
        #     "b.y.z": 20,
        #     "c": [1, 2, 3]  # Lists are not flattened
        # }

        # Custom separator
        flat = flatten_dict(nested, sep="_")
        # {
        #     "a": 1,
        #     "b_x": 10,
        #     "b_y_z": 20,
        #     "c": [1, 2, 3]
        # }
        ```
    """
    items: list[tuple[str, Any]] = []

    for key, value in d.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key

        if isinstance(value, dict):
            # Recursively flatten nested dict
            items.extend(flatten_dict(value, new_key, sep).items())
        else:
            items.append((new_key, value))

    return dict(items)


def unflatten_dict(
    d: dict[str, Any],
    sep: str = ".",
) -> dict[str, Any]:
    """
    Unflatten a dictionary (reverse of flatten_dict).

    Args:
        d: Flattened dictionary
        sep: Separator used in flattened keys (default ".")

    Returns:
        Nested dictionary

    Example:
        ```python
        from hqt.foundation.utils import unflatten_dict

        flat = {
            "a": 1,
            "b.x": 10,
            "b.y.z": 20,
            "c": [1, 2, 3]
        }

        nested = unflatten_dict(flat)
        # {
        #     "a": 1,
        #     "b": {
        #         "x": 10,
        #         "y": {
        #             "z": 20
        #         }
        #     },
        #     "c": [1, 2, 3]
        # }
        ```
    """
    result: dict[str, Any] = {}

    for key, value in d.items():
        parts = key.split(sep)
        current = result

        # Navigate/create nested structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set final value
        current[parts[-1]] = value

    return result


def generate_uuid(prefix: str = "", use_hex: bool = False) -> str:
    """
    Generate a UUID.

    Args:
        prefix: Optional prefix for the UUID
        use_hex: If True, return hex string without dashes (default False)

    Returns:
        UUID string

    Example:
        ```python
        from hqt.foundation.utils import generate_uuid

        # Standard UUID
        id1 = generate_uuid()
        print(id1)  # '550e8400-e29b-41d4-a716-446655440000'

        # With prefix
        id2 = generate_uuid(prefix="trade_")
        print(id2)  # 'trade_550e8400-e29b-41d4-a716-446655440000'

        # Hex format (no dashes)
        id3 = generate_uuid(use_hex=True)
        print(id3)  # '550e8400e29b41d4a716446655440000'
        ```
    """
    uid = uuid.uuid4()

    if use_hex:
        uid_str = uid.hex
    else:
        uid_str = str(uid)

    if prefix:
        return f"{prefix}{uid_str}"

    return uid_str


def hash_file(
    file_path: str | Path,
    algorithm: str = "sha256",
    chunk_size: int = 8192,
) -> str:
    """
    Calculate hash of a file.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, sha1, md5, etc.)
        chunk_size: Size of chunks to read (bytes, default 8192)

    Returns:
        Hex digest of file hash

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If algorithm is not supported

    Example:
        ```python
        from hqt.foundation.utils import hash_file

        # Calculate SHA-256 hash
        sha256 = hash_file("data.csv")
        print(f"SHA-256: {sha256}")

        # Calculate MD5 hash
        md5 = hash_file("data.csv", algorithm="md5")
        print(f"MD5: {md5}")

        # Large files (larger chunks)
        sha256 = hash_file("large_file.bin", chunk_size=65536)
        ```
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get hash function
    try:
        hasher = hashlib.new(algorithm)
    except ValueError as e:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}") from e

    # Read file in chunks
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)

    return hasher.hexdigest()


def hash_string(
    text: str,
    algorithm: str = "sha256",
    encoding: str = "utf-8",
) -> str:
    """
    Calculate hash of a string.

    Args:
        text: String to hash
        algorithm: Hash algorithm (sha256, sha1, md5, etc.)
        encoding: Text encoding (default "utf-8")

    Returns:
        Hex digest of string hash

    Raises:
        ValueError: If algorithm is not supported

    Example:
        ```python
        from hqt.foundation.utils import hash_string

        # Hash a string
        text = "Hello, World!"
        hash_val = hash_string(text)
        print(f"SHA-256: {hash_val}")

        # Use MD5
        hash_val = hash_string(text, algorithm="md5")
        print(f"MD5: {hash_val}")
        ```
    """
    try:
        hasher = hashlib.new(algorithm)
    except ValueError as e:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}") from e

    hasher.update(text.encode(encoding))
    return hasher.hexdigest()


def sizeof_fmt(
    num: float,
    suffix: str = "B",
    binary: bool = True,
) -> str:
    """
    Format size in human-readable format.

    Args:
        num: Size in bytes
        suffix: Suffix to append (default "B" for bytes)
        binary: If True, use binary units (1024), else decimal (1000)

    Returns:
        Formatted size string

    Example:
        ```python
        from hqt.foundation.utils import sizeof_fmt

        # Binary units (1024)
        print(sizeof_fmt(1024))       # "1.0 KiB"
        print(sizeof_fmt(1536))       # "1.5 KiB"
        print(sizeof_fmt(1048576))    # "1.0 MiB"
        print(sizeof_fmt(1073741824)) # "1.0 GiB"

        # Decimal units (1000)
        print(sizeof_fmt(1000, binary=False))  # "1.0 KB"
        print(sizeof_fmt(1500, binary=False))  # "1.5 KB"

        # Custom suffix
        print(sizeof_fmt(1024, suffix="iB"))  # "1.0 KiB"
        ```
    """
    if binary:
        units = ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]
        divisor = 1024.0
    else:
        units = ["", "K", "M", "G", "T", "P", "E", "Z"]
        divisor = 1000.0

    for unit in units:
        if abs(num) < divisor:
            return f"{num:.1f} {unit}{suffix}"
        num /= divisor

    return f"{num:.1f} Yi{suffix}"


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamp value to range [min_value, max_value].

    Args:
        value: Value to clamp
        min_value: Minimum value
        max_value: Maximum value

    Returns:
        Clamped value

    Raises:
        ValueError: If min_value > max_value

    Example:
        ```python
        from hqt.foundation.utils import clamp

        # Clamp to range [0, 10]
        print(clamp(5, 0, 10))   # 5 (in range)
        print(clamp(-5, 0, 10))  # 0 (below min)
        print(clamp(15, 0, 10))  # 10 (above max)

        # Clamp percentage
        print(clamp(1.5, 0.0, 1.0))  # 1.0
        ```
    """
    if min_value > max_value:
        raise ValueError(f"min_value ({min_value}) > max_value ({max_value})")

    return max(min_value, min(value, max_value))


def safe_divide(
    numerator: float,
    denominator: float,
    default: float = 0.0,
) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: Numerator
        denominator: Denominator
        default: Value to return if denominator is zero (default 0.0)

    Returns:
        numerator / denominator, or default if denominator is zero

    Example:
        ```python
        from hqt.foundation.utils import safe_divide

        # Normal division
        print(safe_divide(10, 2))  # 5.0

        # Division by zero (returns default)
        print(safe_divide(10, 0))  # 0.0
        print(safe_divide(10, 0, default=float('inf')))  # inf

        # Very small denominator
        print(safe_divide(10, 1e-10))  # 1e11
        ```
    """
    if denominator == 0:
        return default

    return numerator / denominator


def lerp(a: float, b: float, t: float) -> float:
    """
    Linear interpolation between two values.

    Args:
        a: Start value
        b: End value
        t: Interpolation factor (0.0 = a, 1.0 = b)

    Returns:
        Interpolated value

    Example:
        ```python
        from hqt.foundation.utils import lerp

        # Interpolate between 0 and 100
        print(lerp(0, 100, 0.0))   # 0.0
        print(lerp(0, 100, 0.5))   # 50.0
        print(lerp(0, 100, 1.0))   # 100.0

        # Extrapolation (t outside [0,1])
        print(lerp(0, 100, 1.5))   # 150.0
        print(lerp(0, 100, -0.5))  # -50.0
        ```
    """
    return a + (b - a) * t


def normalize(
    value: float,
    min_value: float,
    max_value: float,
) -> float:
    """
    Normalize value to range [0, 1].

    Args:
        value: Value to normalize
        min_value: Minimum value of range
        max_value: Maximum value of range

    Returns:
        Normalized value in [0, 1]

    Raises:
        ValueError: If min_value >= max_value

    Example:
        ```python
        from hqt.foundation.utils import normalize

        # Normalize to [0, 1]
        print(normalize(50, 0, 100))   # 0.5
        print(normalize(0, 0, 100))    # 0.0
        print(normalize(100, 0, 100))  # 1.0

        # Price normalization
        price = 1.1500
        min_price = 1.1000
        max_price = 1.2000
        normalized = normalize(price, min_price, max_price)
        print(normalized)  # 0.5
        ```
    """
    if min_value >= max_value:
        raise ValueError(f"min_value ({min_value}) >= max_value ({max_value})")

    return (value - min_value) / (max_value - min_value)


def denormalize(
    normalized: float,
    min_value: float,
    max_value: float,
) -> float:
    """
    Denormalize value from [0, 1] to original range.

    Args:
        normalized: Normalized value in [0, 1]
        min_value: Minimum value of range
        max_value: Maximum value of range

    Returns:
        Denormalized value

    Example:
        ```python
        from hqt.foundation.utils import denormalize

        # Denormalize from [0, 1]
        print(denormalize(0.5, 0, 100))  # 50.0
        print(denormalize(0.0, 0, 100))  # 0.0
        print(denormalize(1.0, 0, 100))  # 100.0
        ```
    """
    return min_value + normalized * (max_value - min_value)
