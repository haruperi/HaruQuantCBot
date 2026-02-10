"""
Validation utilities for trading parameters.

This module provides validation and normalization functions for trading
parameters like symbols, volumes, prices, and quantities.
"""

import re
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Any


def validate_symbol(symbol: str, strict: bool = True) -> str:
    """
    Validate and normalize a trading symbol.

    Args:
        symbol: Trading symbol (e.g., "EURUSD", "EUR/USD", "BTCUSD")
        strict: If True, only allow standard Forex pairs (6 chars, uppercase)

    Returns:
        Normalized symbol (uppercase, no slashes/spaces)

    Raises:
        ValueError: If symbol is invalid

    Example:
        ```python
        from hqt.foundation.utils import validate_symbol

        # Valid symbols
        symbol = validate_symbol("eurusd")  # Returns "EURUSD"
        symbol = validate_symbol("EUR/USD")  # Returns "EURUSD"
        symbol = validate_symbol("GBP-USD")  # Returns "GBPUSD"

        # Strict mode (only Forex pairs)
        symbol = validate_symbol("EURUSD", strict=True)  # OK
        symbol = validate_symbol("BTCUSD", strict=True)  # Raises ValueError

        # Non-strict mode (allows crypto, stocks, etc.)
        symbol = validate_symbol("BTCUSD", strict=False)  # OK
        ```
    """
    if not symbol:
        raise ValueError("Symbol cannot be empty")

    # Remove common separators
    normalized = symbol.upper().replace("/", "").replace("-", "").replace(" ", "").replace("_", "")

    # Check length
    if len(normalized) < 2:
        raise ValueError(f"Symbol too short: {symbol}")

    if len(normalized) > 12:
        raise ValueError(f"Symbol too long: {symbol}")

    # Check characters (alphanumeric only)
    if not re.match(r"^[A-Z0-9]+$", normalized):
        raise ValueError(f"Symbol contains invalid characters: {symbol}")

    # Strict mode: only standard Forex pairs (6 characters)
    if strict:
        if len(normalized) != 6:
            raise ValueError(f"Invalid Forex pair length (expected 6 chars): {symbol}")

        # Check that it's all letters (no numbers in Forex pairs)
        if not normalized.isalpha():
            raise ValueError(f"Forex pairs must be alphabetic: {symbol}")

    return normalized


def validate_volume(
    volume: float,
    min_volume: float = 0.01,
    max_volume: float = 100.0,
    volume_step: float = 0.01,
    round_mode: str = "down",
) -> float:
    """
    Validate and normalize trading volume (lot size).

    Rounds volume to the nearest step and clamps to min/max range.

    Args:
        volume: Volume to validate (in lots)
        min_volume: Minimum allowed volume
        max_volume: Maximum allowed volume
        volume_step: Volume step size (e.g., 0.01 for mini lots)
        round_mode: Rounding mode - "down", "up", or "nearest"

    Returns:
        Normalized volume (rounded to step, clamped to range)

    Raises:
        ValueError: If volume is negative or parameters are invalid

    Example:
        ```python
        from hqt.foundation.utils import validate_volume

        # Standard validation
        vol = validate_volume(0.15, min_volume=0.01, volume_step=0.01)
        print(vol)  # 0.15

        # Round down to step
        vol = validate_volume(0.157, volume_step=0.01, round_mode="down")
        print(vol)  # 0.15

        # Round up to step
        vol = validate_volume(0.157, volume_step=0.01, round_mode="up")
        print(vol)  # 0.16

        # Round to nearest step
        vol = validate_volume(0.157, volume_step=0.01, round_mode="nearest")
        print(vol)  # 0.16

        # Clamp to max
        vol = validate_volume(150.0, max_volume=100.0)
        print(vol)  # 100.0
        ```
    """
    if volume < 0:
        raise ValueError(f"Volume cannot be negative: {volume}")

    if min_volume <= 0:
        raise ValueError(f"min_volume must be positive: {min_volume}")

    if max_volume <= 0:
        raise ValueError(f"max_volume must be positive: {max_volume}")

    if volume_step <= 0:
        raise ValueError(f"volume_step must be positive: {volume_step}")

    if min_volume > max_volume:
        raise ValueError(f"min_volume ({min_volume}) > max_volume ({max_volume})")

    # Use Decimal for precise rounding
    vol_decimal = Decimal(str(volume))
    step_decimal = Decimal(str(volume_step))

    # Round to step
    if round_mode == "down":
        steps = int(vol_decimal / step_decimal)
        rounded = float(steps * step_decimal)
    elif round_mode == "up":
        steps = int((vol_decimal + step_decimal - Decimal("0.00000001")) / step_decimal)
        rounded = float(steps * step_decimal)
    elif round_mode == "nearest":
        steps = int((vol_decimal / step_decimal).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        rounded = float(steps * step_decimal)
    else:
        raise ValueError(f"Invalid round_mode: {round_mode}. Must be 'down', 'up', or 'nearest'")

    # Clamp to range
    clamped = max(min_volume, min(rounded, max_volume))

    # Ensure minimum volume if rounded to zero
    if clamped == 0 and volume > 0:
        clamped = min_volume

    return clamped


def validate_price(
    price: float,
    min_price: float = 0.0,
    max_price: float | None = None,
    decimals: int = 5,
) -> float:
    """
    Validate and normalize a price.

    Args:
        price: Price to validate
        min_price: Minimum allowed price (default 0.0)
        max_price: Maximum allowed price (None = no limit)
        decimals: Number of decimal places to round to

    Returns:
        Normalized price (rounded to decimals, clamped to range)

    Raises:
        ValueError: If price is invalid or out of range

    Example:
        ```python
        from hqt.foundation.utils import validate_price

        # Standard validation
        price = validate_price(1.23456, decimals=5)
        print(price)  # 1.23456

        # Round to decimals
        price = validate_price(1.234567, decimals=5)
        print(price)  # 1.23457

        # With range limits
        price = validate_price(1.5, min_price=1.0, max_price=2.0)
        print(price)  # 1.5

        # Out of range
        try:
            price = validate_price(0.5, min_price=1.0)
        except ValueError as e:
            print(e)  # Price 0.5 below minimum 1.0
        ```
    """
    if price < 0:
        raise ValueError(f"Price cannot be negative: {price}")

    if decimals < 0:
        raise ValueError(f"decimals cannot be negative: {decimals}")

    # Round to decimals
    multiplier = 10 ** decimals
    rounded = round(price * multiplier) / multiplier

    # Check range
    if rounded < min_price:
        raise ValueError(f"Price {rounded} below minimum {min_price}")

    if max_price is not None and rounded > max_price:
        raise ValueError(f"Price {rounded} above maximum {max_price}")

    return rounded


def validate_positive(value: float, name: str = "value", allow_zero: bool = False) -> float:
    """
    Validate that a value is positive.

    Args:
        value: Value to validate
        name: Name of the value (for error messages)
        allow_zero: If True, allow zero (default False)

    Returns:
        The value if valid

    Raises:
        ValueError: If value is not positive

    Example:
        ```python
        from hqt.foundation.utils import validate_positive

        # Positive value
        val = validate_positive(10.5)  # OK

        # Negative value
        try:
            val = validate_positive(-5.0, name="stop_loss")
        except ValueError as e:
            print(e)  # stop_loss must be positive, got -5.0

        # Zero with allow_zero=False
        try:
            val = validate_positive(0.0)
        except ValueError as e:
            print(e)  # value must be positive, got 0.0

        # Zero with allow_zero=True
        val = validate_positive(0.0, allow_zero=True)  # OK
        ```
    """
    if allow_zero:
        if value < 0:
            raise ValueError(f"{name} must be non-negative, got {value}")
    else:
        if value <= 0:
            raise ValueError(f"{name} must be positive, got {value}")

    return value


def validate_range(
    value: float,
    min_value: float,
    max_value: float,
    name: str = "value",
    inclusive: bool = True,
) -> float:
    """
    Validate that a value is within a range.

    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        name: Name of the value (for error messages)
        inclusive: If True, include endpoints in range (default True)

    Returns:
        The value if valid

    Raises:
        ValueError: If value is out of range

    Example:
        ```python
        from hqt.foundation.utils import validate_range

        # Value in range (inclusive)
        val = validate_range(5.0, 0.0, 10.0)  # OK
        val = validate_range(0.0, 0.0, 10.0)  # OK (inclusive)
        val = validate_range(10.0, 0.0, 10.0)  # OK (inclusive)

        # Value out of range
        try:
            val = validate_range(15.0, 0.0, 10.0, name="risk_percent")
        except ValueError as e:
            print(e)  # risk_percent must be in range [0.0, 10.0], got 15.0

        # Exclusive range
        try:
            val = validate_range(10.0, 0.0, 10.0, inclusive=False)
        except ValueError as e:
            print(e)  # value must be in range (0.0, 10.0), got 10.0
        ```
    """
    if min_value > max_value:
        raise ValueError(f"min_value ({min_value}) > max_value ({max_value})")

    if inclusive:
        if value < min_value or value > max_value:
            raise ValueError(f"{name} must be in range [{min_value}, {max_value}], got {value}")
    else:
        if value <= min_value or value >= max_value:
            raise ValueError(f"{name} must be in range ({min_value}, {max_value}), got {value}")

    return value


def validate_integer(
    value: Any,
    name: str = "value",
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    """
    Validate and convert to integer.

    Args:
        value: Value to validate (can be int, float, str)
        name: Name of the value (for error messages)
        min_value: Minimum allowed value (None = no limit)
        max_value: Maximum allowed value (None = no limit)

    Returns:
        Integer value

    Raises:
        ValueError: If value cannot be converted to int or is out of range
        TypeError: If value type is not supported

    Example:
        ```python
        from hqt.foundation.utils import validate_integer

        # Valid integers
        val = validate_integer(42)  # 42
        val = validate_integer(42.0)  # 42
        val = validate_integer("42")  # 42

        # With range
        val = validate_integer(5, min_value=0, max_value=10)  # 5

        # Out of range
        try:
            val = validate_integer(15, min_value=0, max_value=10, name="position_count")
        except ValueError as e:
            print(e)  # position_count must be in range [0, 10], got 15

        # Invalid conversion
        try:
            val = validate_integer("abc")
        except ValueError as e:
            print(e)  # Cannot convert value to integer: abc
        ```
    """
    # Try to convert to int
    try:
        if isinstance(value, float):
            # Check if it's a whole number
            if value.is_integer():
                int_value = int(value)
            else:
                raise ValueError(f"{name} must be a whole number, got {value}")
        elif isinstance(value, str):
            int_value = int(value)
        elif isinstance(value, int):
            int_value = value
        else:
            raise TypeError(f"{name} must be int, float, or str, got {type(value).__name__}")
    except (ValueError, TypeError) as e:
        if "invalid literal" in str(e) or "could not convert" in str(e):
            raise ValueError(f"Cannot convert {name} to integer: {value}") from e
        raise

    # Check range
    if min_value is not None and int_value < min_value:
        if max_value is not None:
            raise ValueError(f"{name} must be in range [{min_value}, {max_value}], got {int_value}")
        else:
            raise ValueError(f"{name} must be >= {min_value}, got {int_value}")

    if max_value is not None and int_value > max_value:
        if min_value is not None:
            raise ValueError(f"{name} must be in range [{min_value}, {max_value}], got {int_value}")
        else:
            raise ValueError(f"{name} must be <= {max_value}, got {int_value}")

    return int_value


def sanitize_string(
    value: str,
    max_length: int | None = None,
    allowed_chars: str | None = None,
    strip: bool = True,
) -> str:
    """
    Sanitize a string value.

    Args:
        value: String to sanitize
        max_length: Maximum length (None = no limit)
        allowed_chars: Regex pattern of allowed characters (None = allow all)
        strip: If True, strip leading/trailing whitespace

    Returns:
        Sanitized string

    Raises:
        ValueError: If string is invalid

    Example:
        ```python
        from hqt.foundation.utils import sanitize_string

        # Basic sanitization
        s = sanitize_string("  hello  ")
        print(repr(s))  # 'hello'

        # Max length
        s = sanitize_string("hello world", max_length=5)
        print(s)  # "hello"

        # Allowed characters (alphanumeric only)
        s = sanitize_string("hello_123", allowed_chars=r"[a-zA-Z0-9]")
        print(s)  # "hello123"

        # Invalid characters
        try:
            s = sanitize_string("hello@world", allowed_chars=r"[a-zA-Z]")
        except ValueError as e:
            print(e)  # String contains invalid characters
        ```
    """
    if not isinstance(value, str):
        raise TypeError(f"Value must be string, got {type(value).__name__}")

    # Strip whitespace
    if strip:
        sanitized = value.strip()
    else:
        sanitized = value

    # Check allowed characters
    if allowed_chars is not None:
        # Remove characters not matching pattern
        sanitized = "".join(re.findall(allowed_chars, sanitized))

        # Check if any characters were removed
        if len(sanitized) != len(value.strip() if strip else value):
            # Some characters were removed
            pass

    # Truncate to max length
    if max_length is not None and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized
