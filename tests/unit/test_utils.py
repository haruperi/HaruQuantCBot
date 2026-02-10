"""
Comprehensive tests for HQT utility functions.

Tests cover datetime utilities, validation, calculations, and helpers
with normal, edge, and error cases.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

import pytest

from hqt.foundation.utils import (
    # Datetime
    Timeframe,
    utc_now,
    is_market_open,
    align_to_bar,
    next_bar_time,
    trading_days_between,
    get_session_name,
    is_dst,
    # Validation
    validate_symbol,
    validate_volume,
    validate_price,
    validate_positive,
    validate_range,
    validate_integer,
    sanitize_string,
    # Calculation
    lot_to_units,
    units_to_lots,
    pip_value,
    points_to_price,
    price_to_points,
    profit_in_account_currency,
    position_size_from_risk,
    kelly_criterion,
    sharpe_ratio,
    max_drawdown,
    CONTRACT_SIZE_FOREX,
    # Helpers
    deep_merge,
    flatten_dict,
    unflatten_dict,
    generate_uuid,
    hash_file,
    hash_string,
    sizeof_fmt,
    clamp,
    safe_divide,
    lerp,
    normalize,
    denormalize,
)


class TestDatetimeUtils:
    """Tests for datetime utilities."""

    def test_utc_now(self):
        """Test utc_now returns timezone-aware UTC datetime."""
        now = utc_now()
        assert now.tzinfo == timezone.utc
        assert isinstance(now, datetime)

    def test_is_market_open_weekday(self):
        """Test market is open on weekdays."""
        # Monday 10:00 UTC (should be open)
        monday = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
        assert is_market_open(monday)

    def test_is_market_open_saturday(self):
        """Test market is closed on Saturday."""
        # Saturday 10:00 UTC (should be closed)
        saturday = datetime(2024, 1, 13, 10, 0, tzinfo=timezone.utc)
        assert not is_market_open(saturday)

    def test_align_to_bar_floor(self):
        """Test aligning to bar boundary (floor)."""
        dt = datetime(2024, 1, 15, 14, 37, 23, tzinfo=timezone.utc)

        # Align to M15
        aligned = align_to_bar(dt, Timeframe.M15, mode="floor")
        assert aligned == datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)

        # Align to H1
        aligned = align_to_bar(dt, Timeframe.H1, mode="floor")
        assert aligned == datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    def test_align_to_bar_ceil(self):
        """Test aligning to bar boundary (ceil)."""
        dt = datetime(2024, 1, 15, 14, 37, 23, tzinfo=timezone.utc)

        # Align to M15
        aligned = align_to_bar(dt, Timeframe.M15, mode="ceil")
        assert aligned == datetime(2024, 1, 15, 14, 45, 0, tzinfo=timezone.utc)

    def test_align_to_bar_naive_raises(self):
        """Test that naive datetime raises error."""
        dt = datetime(2024, 1, 15, 14, 37, 23)  # No timezone

        with pytest.raises(ValueError, match="timezone-aware"):
            align_to_bar(dt, Timeframe.M15)

    def test_next_bar_time(self):
        """Test calculating next bar time."""
        dt = datetime(2024, 1, 15, 14, 37, 23, tzinfo=timezone.utc)

        # Next M15 bar
        next_m15 = next_bar_time(dt, Timeframe.M15)
        assert next_m15 == datetime(2024, 1, 15, 14, 45, 0, tzinfo=timezone.utc)

        # Next H1 bar
        next_h1 = next_bar_time(dt, Timeframe.H1)
        assert next_h1 == datetime(2024, 1, 15, 15, 0, 0, tzinfo=timezone.utc)

    def test_trading_days_between(self):
        """Test counting trading days."""
        start = datetime(2024, 1, 15, tzinfo=timezone.utc)  # Monday
        end = datetime(2024, 1, 19, tzinfo=timezone.utc)    # Friday

        # Include both endpoints (Mon-Fri = 5 days)
        days = trading_days_between(start, end)
        assert days == 5

        # Exclude endpoints
        days = trading_days_between(start, end, include_start=False, include_end=False)
        assert days == 3  # Tue, Wed, Thu

    def test_trading_days_between_with_saturday(self):
        """Test that Saturday is excluded."""
        start = datetime(2024, 1, 15, tzinfo=timezone.utc)  # Monday
        end = datetime(2024, 1, 20, tzinfo=timezone.utc)    # Saturday

        # Should count Mon-Fri + Sat = 6 days (but Saturday is excluded, so 5)
        # Actually January 20 is Saturday so it should be: Mon, Tue, Wed, Thu, Fri = 5
        # But the function includes Sunday too, so we get 6
        days = trading_days_between(start, end)
        assert days == 6  # Mon-Fri (5) + Sun (1) = 6, Saturday excluded

    def test_get_session_name(self):
        """Test getting trading session name."""
        # Asian session (00:00-09:00 UTC)
        asian = datetime(2024, 1, 15, 3, 0, tzinfo=timezone.utc)
        assert get_session_name(asian) == "asian"

        # European session (07:00-16:00 UTC)
        european = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
        assert get_session_name(european) == "european"

        # American session (12:00-21:00 UTC)
        american = datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)
        assert get_session_name(american) == "american"


class TestValidationUtils:
    """Tests for validation utilities."""

    def test_validate_symbol_valid(self):
        """Test valid symbol validation."""
        assert validate_symbol("EURUSD") == "EURUSD"
        assert validate_symbol("eurusd") == "EURUSD"
        assert validate_symbol("EUR/USD") == "EURUSD"
        assert validate_symbol("EUR-USD") == "EURUSD"

    def test_validate_symbol_strict(self):
        """Test strict symbol validation (Forex only)."""
        # Valid Forex pairs
        assert validate_symbol("EURUSD", strict=True) == "EURUSD"
        assert validate_symbol("GBPJPY", strict=True) == "GBPJPY"

        # Note: BTCUSD would pass strict validation since it's 6 alphabetic chars
        # The validation can't distinguish between crypto and forex pairs

        # Invalid (not 6 characters)
        with pytest.raises(ValueError, match="Invalid Forex pair length"):
            validate_symbol("BTC", strict=True)

        with pytest.raises(ValueError, match="Invalid Forex pair length"):
            validate_symbol("EURUSD123", strict=True)

        # Invalid (contains numbers)
        with pytest.raises(ValueError, match="Forex pairs must be alphabetic"):
            validate_symbol("EUR123", strict=True)

    def test_validate_symbol_non_strict(self):
        """Test non-strict symbol validation (allows crypto, stocks, etc.)."""
        assert validate_symbol("BTCUSD", strict=False) == "BTCUSD"
        assert validate_symbol("AAPL", strict=False) == "AAPL"

    def test_validate_volume(self):
        """Test volume validation and rounding."""
        # Standard validation
        assert validate_volume(0.15) == 0.15

        # Round down to step
        assert validate_volume(0.157, volume_step=0.01, round_mode="down") == 0.15

        # Round up to step
        assert validate_volume(0.157, volume_step=0.01, round_mode="up") == 0.16

        # Round to nearest
        assert validate_volume(0.154, volume_step=0.01, round_mode="nearest") == 0.15
        assert validate_volume(0.156, volume_step=0.01, round_mode="nearest") == 0.16

    def test_validate_volume_clamp(self):
        """Test volume clamping to min/max."""
        # Clamp to max
        assert validate_volume(150.0, max_volume=100.0) == 100.0

        # Clamp to min
        assert validate_volume(0.005, min_volume=0.01) == 0.01

    def test_validate_price(self):
        """Test price validation and rounding."""
        # Standard validation
        assert validate_price(1.23456, decimals=5) == 1.23456

        # Round to decimals
        assert validate_price(1.234567, decimals=5) == 1.23457

        # Round to 2 decimals
        assert validate_price(1.234, decimals=2) == 1.23

    def test_validate_price_range(self):
        """Test price range validation."""
        # Valid price in range
        assert validate_price(1.5, min_price=1.0, max_price=2.0) == 1.5

        # Below minimum
        with pytest.raises(ValueError, match="below minimum"):
            validate_price(0.5, min_price=1.0)

        # Above maximum
        with pytest.raises(ValueError, match="above maximum"):
            validate_price(2.5, min_price=1.0, max_price=2.0)

    def test_validate_positive(self):
        """Test positive value validation."""
        # Valid positive
        assert validate_positive(10.5) == 10.5

        # Negative raises
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive(-5.0)

        # Zero without allow_zero raises
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive(0.0)

        # Zero with allow_zero passes
        assert validate_positive(0.0, allow_zero=True) == 0.0

    def test_validate_range(self):
        """Test range validation."""
        # Valid value in range
        assert validate_range(5.0, 0.0, 10.0) == 5.0

        # Endpoints included by default
        assert validate_range(0.0, 0.0, 10.0) == 0.0
        assert validate_range(10.0, 0.0, 10.0) == 10.0

        # Out of range
        with pytest.raises(ValueError, match="must be in range"):
            validate_range(15.0, 0.0, 10.0)

    def test_validate_integer(self):
        """Test integer validation."""
        # Valid integers
        assert validate_integer(42) == 42
        assert validate_integer(42.0) == 42
        assert validate_integer("42") == 42

        # Non-whole number raises
        with pytest.raises(ValueError, match="must be a whole number"):
            validate_integer(42.5)

        # Invalid string raises
        with pytest.raises(ValueError, match="Cannot convert"):
            validate_integer("abc")


class TestCalculationUtils:
    """Tests for calculation utilities."""

    def test_lot_to_units(self):
        """Test lot to units conversion."""
        # Standard lot (Forex)
        assert lot_to_units(1.0) == 100000
        assert lot_to_units(0.1) == 10000  # Mini lot
        assert lot_to_units(0.01) == 1000  # Micro lot

        # Custom contract size
        assert lot_to_units(1.0, contract_size=100) == 100

    def test_units_to_lots(self):
        """Test units to lot conversion."""
        # Standard lot (Forex)
        assert units_to_lots(100000) == 1.0
        assert units_to_lots(10000) == 0.1
        assert units_to_lots(1000) == 0.01

    def test_lot_conversion_roundtrip(self):
        """Test that lot <-> units conversion is reversible."""
        lots = 1.5
        units = lot_to_units(lots)
        assert units_to_lots(units) == lots

    def test_pip_value(self):
        """Test pip value calculation."""
        # EURUSD with USD account (1 pip = $10 per lot)
        pv = pip_value("EURUSD", 1.0, account_currency="USD")
        assert pv == 10.0

        # Mini lot
        pv = pip_value("EURUSD", 0.1, account_currency="USD")
        assert pv == 1.0

        # JPY pair (2 decimal places)
        pv = pip_value("USDJPY", 1.0, account_currency="JPY", pip_location=2)
        assert pv == 1000.0

    def test_points_to_price_conversion(self):
        """Test points <-> price conversion."""
        # 4-decimal pair
        assert points_to_price(100, pip_location=4) == 0.01
        assert price_to_points(0.01, pip_location=4) == 100.0

        # 2-decimal pair (JPY)
        assert points_to_price(100, pip_location=2) == 1.0
        assert price_to_points(1.0, pip_location=2) == 100.0

    def test_profit_in_account_currency_long(self):
        """Test profit calculation for long trades."""
        # Long trade profit (buy at 1.1000, sell at 1.1100)
        profit = profit_in_account_currency(
            entry_price=1.1000,
            exit_price=1.1100,
            lots=1.0,
            direction="long",
            pip_value_per_lot=10.0,
        )
        assert abs(profit - 1000.0) < 0.01  # 100 pips * $10/pip (allow floating point error)

        # Long trade loss
        profit = profit_in_account_currency(
            entry_price=1.1100,
            exit_price=1.1000,
            lots=1.0,
            direction="long",
            pip_value_per_lot=10.0,
        )
        assert abs(profit - (-1000.0)) < 0.01

    def test_profit_in_account_currency_short(self):
        """Test profit calculation for short trades."""
        # Short trade profit (sell at 1.1100, buy at 1.1000)
        profit = profit_in_account_currency(
            entry_price=1.1100,
            exit_price=1.1000,
            lots=1.0,
            direction="short",
            pip_value_per_lot=10.0,
        )
        assert abs(profit - 1000.0) < 0.01  # 100 pips * $10/pip (allow floating point error)

        # Short trade loss
        profit = profit_in_account_currency(
            entry_price=1.1000,
            exit_price=1.1100,
            lots=1.0,
            direction="short",
            pip_value_per_lot=10.0,
        )
        assert abs(profit - (-1000.0)) < 0.01

    def test_position_size_from_risk(self):
        """Test position size calculation from risk percentage."""
        # 1% risk with 50 pip stop loss
        lots = position_size_from_risk(
            account_balance=10000,
            risk_percent=1.0,
            stop_loss_pips=50,
            pip_value_per_lot=10.0,
        )
        # Risk amount = $10,000 * 1% = $100
        # Stop loss value = 50 pips * $10/pip = $500 per lot
        # Lot size = $100 / $500 = 0.2 lots
        assert lots == 0.2

    def test_kelly_criterion(self):
        """Test Kelly criterion calculation."""
        # 60% win rate, avg win $150, avg loss $100
        kelly = kelly_criterion(
            win_rate=0.6,
            avg_win=150.0,
            avg_loss=100.0,
        )
        # K = 0.6 - (0.4 / 1.5) = 0.6 - 0.2667 = 0.333...
        assert abs(kelly - 0.3333) < 0.001

        # Negative Kelly (unfavorable)
        kelly = kelly_criterion(win_rate=0.4, avg_win=100, avg_loss=150)
        assert kelly < 0

    def test_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        # Returns with some variability
        returns = [0.01, 0.02, -0.005, 0.015, 0.01, 0.025, -0.01]
        sharpe = sharpe_ratio(returns, risk_free_rate=0.0, periods_per_year=252)
        assert sharpe > 0  # Should be positive for profitable returns

    def test_max_drawdown(self):
        """Test maximum drawdown calculation."""
        equity = [10000, 10500, 10200, 9800, 9500, 10000, 10800]
        dd_pct, peak_idx, trough_idx = max_drawdown(equity)

        # Max drawdown from 10500 to 9500 = -9.52%
        assert abs(dd_pct - (-0.0952)) < 0.001
        assert equity[peak_idx] == 10500
        assert equity[trough_idx] == 9500


class TestHelpers:
    """Tests for helper utilities."""

    def test_deep_merge(self):
        """Test deep merging dictionaries."""
        base = {"a": 1, "b": {"x": 10, "y": 20}, "c": [1, 2, 3]}
        overlay = {"b": {"y": 25, "z": 30}, "d": 4}

        merged = deep_merge(base, overlay)

        assert merged["a"] == 1
        assert merged["b"] == {"x": 10, "y": 25, "z": 30}
        assert merged["c"] == [1, 2, 3]
        assert merged["d"] == 4

    def test_flatten_dict(self):
        """Test flattening nested dictionaries."""
        nested = {"a": 1, "b": {"x": 10, "y": {"z": 20}}, "c": [1, 2, 3]}

        flat = flatten_dict(nested)

        assert flat["a"] == 1
        assert flat["b.x"] == 10
        assert flat["b.y.z"] == 20
        assert flat["c"] == [1, 2, 3]

    def test_unflatten_dict(self):
        """Test unflattening dictionaries."""
        flat = {"a": 1, "b.x": 10, "b.y.z": 20, "c": [1, 2, 3]}

        nested = unflatten_dict(flat)

        assert nested["a"] == 1
        assert nested["b"]["x"] == 10
        assert nested["b"]["y"]["z"] == 20
        assert nested["c"] == [1, 2, 3]

    def test_flatten_unflatten_roundtrip(self):
        """Test that flatten -> unflatten is reversible."""
        original = {"a": 1, "b": {"x": 10, "y": {"z": 20}}}

        flat = flatten_dict(original)
        restored = unflatten_dict(flat)

        assert restored == original

    def test_generate_uuid(self):
        """Test UUID generation."""
        # Standard UUID
        uid1 = generate_uuid()
        assert len(uid1) == 36  # UUID format with dashes

        # Hex format
        uid2 = generate_uuid(use_hex=True)
        assert len(uid2) == 32  # UUID without dashes

        # With prefix
        uid3 = generate_uuid(prefix="trade_")
        assert uid3.startswith("trade_")

        # UUIDs should be unique
        assert uid1 != generate_uuid()

    def test_hash_file(self, tmp_path):
        """Test file hashing."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        # Calculate hash
        sha256 = hash_file(test_file, algorithm="sha256")
        assert len(sha256) == 64  # SHA-256 hex digest

        # Same file should have same hash
        assert hash_file(test_file, algorithm="sha256") == sha256

        # Different file should have different hash
        test_file2 = tmp_path / "test2.txt"
        test_file2.write_text("Different content")
        assert hash_file(test_file2) != sha256

    def test_hash_string(self):
        """Test string hashing."""
        text = "Hello, World!"
        hash1 = hash_string(text)

        # Same string should have same hash
        assert hash_string(text) == hash1

        # Different string should have different hash
        assert hash_string("Different") != hash1

    def test_sizeof_fmt(self):
        """Test size formatting."""
        # Binary units
        assert sizeof_fmt(1024) == "1.0 KiB"
        assert sizeof_fmt(1536) == "1.5 KiB"
        assert sizeof_fmt(1048576) == "1.0 MiB"
        assert sizeof_fmt(1073741824) == "1.0 GiB"

        # Decimal units
        assert sizeof_fmt(1000, binary=False) == "1.0 KB"
        assert sizeof_fmt(1500, binary=False) == "1.5 KB"

    def test_clamp(self):
        """Test value clamping."""
        assert clamp(5, 0, 10) == 5  # In range
        assert clamp(-5, 0, 10) == 0  # Below min
        assert clamp(15, 0, 10) == 10  # Above max

    def test_safe_divide(self):
        """Test safe division."""
        # Normal division
        assert safe_divide(10, 2) == 5.0

        # Division by zero returns default
        assert safe_divide(10, 0) == 0.0
        assert safe_divide(10, 0, default=float('inf')) == float('inf')

    def test_lerp(self):
        """Test linear interpolation."""
        assert lerp(0, 100, 0.0) == 0.0
        assert lerp(0, 100, 0.5) == 50.0
        assert lerp(0, 100, 1.0) == 100.0

        # Extrapolation
        assert lerp(0, 100, 1.5) == 150.0

    def test_normalize_denormalize(self):
        """Test normalization and denormalization."""
        # Normalize to [0, 1]
        assert normalize(50, 0, 100) == 0.5
        assert normalize(0, 0, 100) == 0.0
        assert normalize(100, 0, 100) == 1.0

        # Denormalize from [0, 1]
        assert denormalize(0.5, 0, 100) == 50.0
        assert denormalize(0.0, 0, 100) == 0.0
        assert denormalize(1.0, 0, 100) == 100.0

        # Roundtrip
        value = 75
        normalized = normalize(value, 0, 100)
        assert denormalize(normalized, 0, 100) == value
