"""
Unit tests for Tick data model.

Tests the Tick Pydantic model including:
- Valid and invalid creation
- Validator triggers
- Immutability (frozen)
- Properties and computed fields
- Factory functions
"""

from datetime import datetime, timezone

import pytest

from hqt.data.models.tick import Tick, create_tick


class TestTick:
    """Test suite for Tick data model."""

    def test_tick_creation_valid(self):
        """Test creating a valid tick."""
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
            bid_volume=1000000.0,
            ask_volume=1500000.0,
        )

        assert tick.symbol == "EURUSD"
        assert tick.timestamp == 1704067200000000
        assert tick.bid == 1.10520
        assert tick.ask == 1.10523
        assert tick.bid_volume == 1000000.0
        assert tick.ask_volume == 1500000.0

    def test_tick_spread_computed(self):
        """Test that spread is computed correctly."""
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
        )

        assert tick.spread == pytest.approx(0.00003, abs=1e-8)

    def test_tick_mid_price_computed(self):
        """Test that mid price is computed correctly."""
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
        )

        assert tick.mid_price == pytest.approx(1.105215, abs=1e-8)

    def test_tick_default_volumes(self):
        """Test that volumes default to 0.0."""
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
        )

        assert tick.bid_volume == 0.0
        assert tick.ask_volume == 0.0

    def test_tick_datetime_property(self):
        """Test datetime property conversion."""
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,  # 2024-01-01 00:00:00 UTC
            bid=1.10520,
            ask=1.10523,
        )

        dt = tick.datetime
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1

    def test_tick_invalid_bid_zero(self):
        """Test that bid=0 is rejected."""
        with pytest.raises(ValueError, match="greater than 0"):
            Tick(
                symbol="EURUSD",
                timestamp=1704067200000000,
                bid=0.0,
                ask=1.10523,
            )

    def test_tick_invalid_bid_negative(self):
        """Test that negative bid is rejected."""
        with pytest.raises(ValueError, match="greater than 0"):
            Tick(
                symbol="EURUSD",
                timestamp=1704067200000000,
                bid=-1.10520,
                ask=1.10523,
            )

    def test_tick_invalid_ask_zero(self):
        """Test that ask=0 is rejected."""
        with pytest.raises(ValueError, match="greater than 0"):
            Tick(
                symbol="EURUSD",
                timestamp=1704067200000000,
                bid=1.10520,
                ask=0.0,
            )

    def test_tick_invalid_ask_less_than_bid(self):
        """Test that ask < bid is rejected."""
        with pytest.raises(ValueError, match="ask .* must be >= bid"):
            Tick(
                symbol="EURUSD",
                timestamp=1704067200000000,
                bid=1.10523,
                ask=1.10520,
            )

    def test_tick_invalid_timestamp_zero(self):
        """Test that timestamp=0 is rejected."""
        with pytest.raises(ValueError, match="greater than 0"):
            Tick(
                symbol="EURUSD",
                timestamp=0,
                bid=1.10520,
                ask=1.10523,
            )

    def test_tick_invalid_negative_volume(self):
        """Test that negative volumes are rejected."""
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            Tick(
                symbol="EURUSD",
                timestamp=1704067200000000,
                bid=1.10520,
                ask=1.10523,
                bid_volume=-100.0,
            )

    def test_tick_frozen_immutable(self):
        """Test that tick instances are immutable (frozen)."""
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
        )

        with pytest.raises(Exception):  # Pydantic raises ValidationError or similar
            tick.bid = 1.20000

    def test_tick_to_dict(self):
        """Test tick to_dict conversion."""
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
            bid_volume=1000000.0,
        )

        d = tick.to_dict()
        assert d["symbol"] == "EURUSD"
        assert d["timestamp"] == 1704067200000000
        assert d["bid"] == 1.10520
        assert d["ask"] == 1.10523
        assert "spread" in d

    def test_tick_repr(self):
        """Test tick string representation."""
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
        )

        repr_str = repr(tick)
        assert "Tick" in repr_str
        assert "EURUSD" in repr_str
        assert "1.10520" in repr_str

    def test_create_tick_with_microseconds(self):
        """Test create_tick factory with microsecond timestamp."""
        tick = create_tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
        )

        assert tick.symbol == "EURUSD"
        assert tick.timestamp == 1704067200000000

    def test_create_tick_with_datetime(self):
        """Test create_tick factory with datetime object."""
        dt = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        tick = create_tick(
            symbol="EURUSD",
            timestamp=dt,
            bid=1.10520,
            ask=1.10523,
        )

        assert tick.symbol == "EURUSD"
        assert tick.timestamp == 1704067200000000

    def test_tick_ask_equal_to_bid_valid(self):
        """Test that ask == bid is allowed (zero spread)."""
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10520,
        )

        assert tick.spread == 0.0

    def test_tick_empty_symbol_rejected(self):
        """Test that empty symbol string is rejected."""
        with pytest.raises(ValueError):
            Tick(
                symbol="",
                timestamp=1704067200000000,
                bid=1.10520,
                ask=1.10523,
            )

    def test_tick_whitespace_symbol_stripped(self):
        """Test that whitespace in symbol is stripped."""
        tick = Tick(
            symbol="  EURUSD  ",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
        )

        assert tick.symbol == "EURUSD"
