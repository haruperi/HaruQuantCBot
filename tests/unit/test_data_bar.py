"""
Unit tests for Bar data model and Timeframe enum.

Tests the Bar Pydantic model and Timeframe enum including:
- Valid and invalid creation
- Validator triggers (OHLC consistency)
- Immutability (frozen)
- Properties and computed fields
- Timeframe operations
- Factory functions
"""

from datetime import datetime, timezone

import pytest

from hqt.data.models.bar import Bar, Timeframe, create_bar


class TestTimeframe:
    """Test suite for Timeframe enum."""

    def test_timeframe_values(self):
        """Test all timeframe values exist."""
        assert Timeframe.M1.value == "M1"
        assert Timeframe.M5.value == "M5"
        assert Timeframe.M15.value == "M15"
        assert Timeframe.M30.value == "M30"
        assert Timeframe.H1.value == "H1"
        assert Timeframe.H4.value == "H4"
        assert Timeframe.D1.value == "D1"
        assert Timeframe.W1.value == "W1"
        assert Timeframe.MN1.value == "MN1"

    def test_timeframe_minutes(self):
        """Test timeframe minute conversion."""
        assert Timeframe.M1.minutes == 1
        assert Timeframe.M5.minutes == 5
        assert Timeframe.M15.minutes == 15
        assert Timeframe.M30.minutes == 30
        assert Timeframe.H1.minutes == 60
        assert Timeframe.H4.minutes == 240
        assert Timeframe.D1.minutes == 1440
        assert Timeframe.W1.minutes == 10080
        assert Timeframe.MN1.minutes == 43200

    def test_timeframe_seconds(self):
        """Test timeframe second conversion."""
        assert Timeframe.M1.seconds == 60
        assert Timeframe.H1.seconds == 3600
        assert Timeframe.D1.seconds == 86400

    def test_timeframe_comparison(self):
        """Test timeframe comparison operators."""
        assert Timeframe.M1 < Timeframe.M5
        assert Timeframe.M5 < Timeframe.H1
        assert Timeframe.H1 < Timeframe.D1
        assert Timeframe.D1 > Timeframe.H1
        assert Timeframe.H1 <= Timeframe.H1
        assert Timeframe.H1 >= Timeframe.H1

    def test_timeframe_from_string(self):
        """Test creating timeframe from string."""
        tf = Timeframe("H1")
        assert tf == Timeframe.H1


class TestBar:
    """Test suite for Bar data model."""

    def test_bar_creation_valid(self):
        """Test creating a valid bar."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
            tick_volume=15234,
            real_volume=125000000.0,
            spread=0.00003,
        )

        assert bar.symbol == "EURUSD"
        assert bar.timeframe == Timeframe.H1
        assert bar.open == 1.10520
        assert bar.high == 1.10580
        assert bar.low == 1.10500
        assert bar.close == 1.10550

    def test_bar_default_volumes(self):
        """Test that volumes default to 0."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        assert bar.tick_volume == 0
        assert bar.real_volume == 0.0
        assert bar.spread == 0.0

    def test_bar_range_computed(self):
        """Test bar range calculation."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        assert bar.range == pytest.approx(0.00080, abs=1e-8)

    def test_bar_body_computed(self):
        """Test bar body size calculation."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        assert bar.body == pytest.approx(0.00030, abs=1e-8)

    def test_bar_wicks_computed(self):
        """Test bar wick calculations."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        # Upper wick: high - max(open, close)
        assert bar.upper_wick == pytest.approx(0.00030, abs=1e-8)
        # Lower wick: min(open, close) - low
        assert bar.lower_wick == pytest.approx(0.00020, abs=1e-8)

    def test_bar_is_bullish(self):
        """Test bullish bar detection."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        assert bar.is_bullish is True
        assert bar.is_bearish is False
        assert bar.is_doji is False

    def test_bar_is_bearish(self):
        """Test bearish bar detection."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10550,
            high=1.10580,
            low=1.10500,
            close=1.10520,
        )

        assert bar.is_bullish is False
        assert bar.is_bearish is True
        assert bar.is_doji is False

    def test_bar_is_doji(self):
        """Test doji bar detection."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10520,
        )

        assert bar.is_bullish is False
        assert bar.is_bearish is False
        assert bar.is_doji is True

    def test_bar_datetime_property(self):
        """Test datetime property conversion."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        dt = bar.datetime
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1

    def test_bar_invalid_high_less_than_open(self):
        """Test that high < open is rejected."""
        with pytest.raises(ValueError, match="high .* must be >= max"):
            Bar(
                symbol="EURUSD",
                timeframe=Timeframe.H1,
                timestamp=1704067200000000,
                open=1.10580,
                high=1.10550,  # Less than open
                low=1.10500,
                close=1.10520,
            )

    def test_bar_invalid_high_less_than_close(self):
        """Test that high < close is rejected."""
        with pytest.raises(ValueError, match="high .* must be >= max"):
            Bar(
                symbol="EURUSD",
                timeframe=Timeframe.H1,
                timestamp=1704067200000000,
                open=1.10520,
                high=1.10550,  # Less than close
                low=1.10500,
                close=1.10580,
            )

    def test_bar_invalid_low_greater_than_open(self):
        """Test that low > open is rejected."""
        with pytest.raises(ValueError, match="low .* must be <= min"):
            Bar(
                symbol="EURUSD",
                timeframe=Timeframe.H1,
                timestamp=1704067200000000,
                open=1.10500,
                high=1.10580,
                low=1.10520,  # Greater than open
                close=1.10550,
            )

    def test_bar_invalid_low_greater_than_close(self):
        """Test that low > close is rejected."""
        with pytest.raises(ValueError, match="low .* must be <= min"):
            Bar(
                symbol="EURUSD",
                timeframe=Timeframe.H1,
                timestamp=1704067200000000,
                open=1.10550,
                high=1.10580,
                low=1.10530,  # Greater than close
                close=1.10520,
            )

    def test_bar_invalid_zero_price(self):
        """Test that zero prices are rejected."""
        with pytest.raises(ValueError, match="greater than 0"):
            Bar(
                symbol="EURUSD",
                timeframe=Timeframe.H1,
                timestamp=1704067200000000,
                open=0.0,
                high=1.10580,
                low=1.10500,
                close=1.10550,
            )

    def test_bar_invalid_negative_volume(self):
        """Test that negative volumes are rejected."""
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            Bar(
                symbol="EURUSD",
                timeframe=Timeframe.H1,
                timestamp=1704067200000000,
                open=1.10520,
                high=1.10580,
                low=1.10500,
                close=1.10550,
                tick_volume=-100,
            )

    def test_bar_frozen_immutable(self):
        """Test that bar instances are immutable (frozen)."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        with pytest.raises(Exception):
            bar.close = 1.20000

    def test_bar_to_dict(self):
        """Test bar to_dict conversion."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        d = bar.to_dict()
        assert d["symbol"] == "EURUSD"
        assert d["timeframe"] == "H1"
        assert d["open"] == 1.10520
        assert d["high"] == 1.10580

    def test_bar_repr(self):
        """Test bar string representation."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        repr_str = repr(bar)
        assert "Bar" in repr_str
        assert "EURUSD" in repr_str
        assert "H1" in repr_str

    def test_create_bar_with_microseconds(self):
        """Test create_bar factory with microsecond timestamp."""
        bar = create_bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        assert bar.symbol == "EURUSD"
        assert bar.timestamp == 1704067200000000

    def test_create_bar_with_datetime(self):
        """Test create_bar factory with datetime object."""
        dt = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        bar = create_bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=dt,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        assert bar.symbol == "EURUSD"
        assert bar.timestamp == 1704067200000000

    def test_create_bar_with_timeframe_string(self):
        """Test create_bar factory with timeframe as string."""
        bar = create_bar(
            symbol="EURUSD",
            timeframe="H1",
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
        )

        assert bar.timeframe == Timeframe.H1

    def test_bar_valid_ohlc_all_equal(self):
        """Test that OHLC can all be equal (flat bar)."""
        bar = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10520,
            low=1.10520,
            close=1.10520,
        )

        assert bar.range == 0.0
        assert bar.body == 0.0
