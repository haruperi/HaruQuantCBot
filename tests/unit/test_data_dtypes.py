"""
Unit tests for NumPy dtype definitions and conversion functions.

Tests the dtype module including:
- Fixed-point conversion (price_to_fixed, fixed_to_price)
- Tick ↔ NumPy array conversion
- Bar ↔ NumPy array conversion
- Batch conversions
- Round-trip integrity
"""

import numpy as np
import pytest

from hqt.data.models.bar import Bar, Timeframe
from hqt.data.models.dtypes import (
    BAR_DTYPE,
    TICK_DTYPE,
    array_to_bar,
    array_to_bars,
    array_to_tick,
    array_to_ticks,
    bar_to_array,
    bars_to_array,
    fixed_to_price,
    price_to_fixed,
    tick_to_array,
    ticks_to_array,
)
from hqt.data.models.tick import Tick


class TestFixedPointConversion:
    """Test suite for fixed-point arithmetic conversion."""

    def test_price_to_fixed_5_digits(self):
        """Test float to fixed-point conversion (5 digits)."""
        assert price_to_fixed(1.10523, 5) == 110523
        assert price_to_fixed(1.10000, 5) == 110000
        assert price_to_fixed(0.00001, 5) == 1

    def test_price_to_fixed_2_digits(self):
        """Test float to fixed-point conversion (2 digits)."""
        assert price_to_fixed(2350.50, 2) == 235050
        assert price_to_fixed(2350.00, 2) == 235000

    def test_price_to_fixed_rounding(self):
        """Test rounding in conversion."""
        # 1.105235 should round to 1.10524 (110524)
        assert price_to_fixed(1.105235, 5) == 110524
        assert price_to_fixed(1.105234, 5) == 110523

    def test_fixed_to_price_5_digits(self):
        """Test fixed-point to float conversion (5 digits)."""
        assert fixed_to_price(110523, 5) == pytest.approx(1.10523)
        assert fixed_to_price(110000, 5) == pytest.approx(1.10000)
        assert fixed_to_price(1, 5) == pytest.approx(0.00001)

    def test_fixed_to_price_2_digits(self):
        """Test fixed-point to float conversion (2 digits)."""
        assert fixed_to_price(235050, 2) == pytest.approx(2350.50)
        assert fixed_to_price(235000, 2) == pytest.approx(2350.00)

    def test_price_fixed_round_trip(self):
        """Test round-trip conversion integrity."""
        original = 1.10523
        fixed = price_to_fixed(original, 5)
        recovered = fixed_to_price(fixed, 5)
        assert recovered == pytest.approx(original, abs=1e-8)


class TestTickDtype:
    """Test suite for Tick NumPy dtype."""

    def test_tick_dtype_structure(self):
        """Test that TICK_DTYPE has correct fields."""
        assert "timestamp" in TICK_DTYPE.names
        assert "symbol_id" in TICK_DTYPE.names
        assert "bid" in TICK_DTYPE.names
        assert "ask" in TICK_DTYPE.names
        assert "bid_volume" in TICK_DTYPE.names
        assert "ask_volume" in TICK_DTYPE.names
        assert "spread_points" in TICK_DTYPE.names

    def test_tick_dtype_types(self):
        """Test that TICK_DTYPE has correct field types."""
        assert TICK_DTYPE.fields["timestamp"][0] == np.dtype(np.int64)
        assert TICK_DTYPE.fields["symbol_id"][0] == np.dtype(np.uint32)
        assert TICK_DTYPE.fields["bid"][0] == np.dtype(np.int64)
        assert TICK_DTYPE.fields["spread_points"][0] == np.dtype(np.int32)


class TestBarDtype:
    """Test suite for Bar NumPy dtype."""

    def test_bar_dtype_structure(self):
        """Test that BAR_DTYPE has correct fields."""
        assert "timestamp" in BAR_DTYPE.names
        assert "symbol_id" in BAR_DTYPE.names
        assert "open" in BAR_DTYPE.names
        assert "high" in BAR_DTYPE.names
        assert "low" in BAR_DTYPE.names
        assert "close" in BAR_DTYPE.names
        assert "tick_volume" in BAR_DTYPE.names
        assert "real_volume" in BAR_DTYPE.names
        assert "spread_points" in BAR_DTYPE.names
        assert "timeframe" in BAR_DTYPE.names

    def test_bar_dtype_types(self):
        """Test that BAR_DTYPE has correct field types."""
        assert BAR_DTYPE.fields["timestamp"][0] == np.dtype(np.int64)
        assert BAR_DTYPE.fields["open"][0] == np.dtype(np.int64)
        assert BAR_DTYPE.fields["timeframe"][0] == np.dtype(np.uint16)


class TestTickConversion:
    """Test suite for Tick ↔ NumPy array conversion."""

    def test_tick_to_array(self):
        """Test converting Tick model to NumPy array."""
        tick = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
            bid_volume=1000000.0,
            ask_volume=1500000.0,
        )

        arr = tick_to_array(tick, digits=5)

        assert arr["timestamp"] == 1704067200000000
        assert arr["bid"] == 110520
        assert arr["ask"] == 110523
        assert arr["bid_volume"] == 1000000
        assert arr["ask_volume"] == 1500000

    def test_array_to_tick(self):
        """Test converting NumPy array to Tick model."""
        arr = np.zeros(1, dtype=TICK_DTYPE)
        arr["timestamp"] = 1704067200000000
        arr["bid"] = 110520
        arr["ask"] = 110523
        arr["bid_volume"] = 1000000
        arr["ask_volume"] = 1500000

        tick = array_to_tick(arr[0], symbol="EURUSD", digits=5)

        assert tick.symbol == "EURUSD"
        assert tick.timestamp == 1704067200000000
        assert tick.bid == pytest.approx(1.10520)
        assert tick.ask == pytest.approx(1.10523)
        assert tick.bid_volume == 1000000.0

    def test_tick_round_trip(self):
        """Test Tick → array → Tick round-trip integrity."""
        original = Tick(
            symbol="EURUSD",
            timestamp=1704067200000000,
            bid=1.10520,
            ask=1.10523,
            bid_volume=1000000.0,
            ask_volume=1500000.0,
        )

        arr = tick_to_array(original, digits=5)
        recovered = array_to_tick(arr, symbol="EURUSD", digits=5)

        assert recovered.symbol == original.symbol
        assert recovered.timestamp == original.timestamp
        assert recovered.bid == pytest.approx(original.bid, abs=1e-5)
        assert recovered.ask == pytest.approx(original.ask, abs=1e-5)

    def test_ticks_to_array(self):
        """Test converting multiple Tick models to NumPy array."""
        ticks = [
            Tick(
                symbol="EURUSD",
                timestamp=1704067200000000 + i * 1000,
                bid=1.10520 + i * 0.00001,
                ask=1.10523 + i * 0.00001,
            )
            for i in range(10)
        ]

        arr = ticks_to_array(ticks, digits=5)

        assert arr.shape == (10,)
        assert arr[0]["timestamp"] == 1704067200000000
        assert arr[9]["timestamp"] == 1704067200000000 + 9000

    def test_array_to_ticks(self):
        """Test converting NumPy array to multiple Tick models."""
        arr = np.zeros(10, dtype=TICK_DTYPE)
        for i in range(10):
            arr[i]["timestamp"] = 1704067200000000 + i * 1000
            arr[i]["bid"] = 110520 + i
            arr[i]["ask"] = 110523 + i

        ticks = array_to_ticks(arr, symbol="EURUSD", digits=5)

        assert len(ticks) == 10
        assert ticks[0].timestamp == 1704067200000000
        assert ticks[9].timestamp == 1704067200000000 + 9000


class TestBarConversion:
    """Test suite for Bar ↔ NumPy array conversion."""

    def test_bar_to_array(self):
        """Test converting Bar model to NumPy array."""
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
        )

        arr = bar_to_array(bar, digits=5)

        assert arr["timestamp"] == 1704067200000000
        assert arr["open"] == 110520
        assert arr["high"] == 110580
        assert arr["low"] == 110500
        assert arr["close"] == 110550
        assert arr["tick_volume"] == 15234
        assert arr["timeframe"] == 60  # H1 = 60 minutes

    def test_array_to_bar(self):
        """Test converting NumPy array to Bar model."""
        arr = np.zeros(1, dtype=BAR_DTYPE)
        arr["timestamp"] = 1704067200000000
        arr["open"] = 110520
        arr["high"] = 110580
        arr["low"] = 110500
        arr["close"] = 110550
        arr["tick_volume"] = 15234
        arr["real_volume"] = 125000000
        arr["timeframe"] = 60  # H1

        bar = array_to_bar(arr[0], symbol="EURUSD", digits=5)

        assert bar.symbol == "EURUSD"
        assert bar.timeframe == Timeframe.H1
        assert bar.timestamp == 1704067200000000
        assert bar.open == pytest.approx(1.10520)
        assert bar.high == pytest.approx(1.10580)
        assert bar.low == pytest.approx(1.10500)
        assert bar.close == pytest.approx(1.10550)

    def test_bar_round_trip(self):
        """Test Bar → array → Bar round-trip integrity."""
        original = Bar(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp=1704067200000000,
            open=1.10520,
            high=1.10580,
            low=1.10500,
            close=1.10550,
            tick_volume=15234,
        )

        arr = bar_to_array(original, digits=5)
        recovered = array_to_bar(arr, symbol="EURUSD", digits=5)

        assert recovered.symbol == original.symbol
        assert recovered.timeframe == original.timeframe
        assert recovered.timestamp == original.timestamp
        assert recovered.open == pytest.approx(original.open, abs=1e-5)
        assert recovered.close == pytest.approx(original.close, abs=1e-5)

    def test_bars_to_array(self):
        """Test converting multiple Bar models to NumPy array."""
        bars = [
            Bar(
                symbol="EURUSD",
                timeframe=Timeframe.H1,
                timestamp=1704067200000000 + i * 3600000000,
                open=1.10520 + i * 0.00001,
                high=1.10580 + i * 0.00001,
                low=1.10500 + i * 0.00001,
                close=1.10550 + i * 0.00001,
            )
            for i in range(10)
        ]

        arr = bars_to_array(bars, digits=5)

        assert arr.shape == (10,)
        assert arr[0]["timestamp"] == 1704067200000000
        assert arr[9]["timestamp"] == 1704067200000000 + 9 * 3600000000

    def test_array_to_bars(self):
        """Test converting NumPy array to multiple Bar models."""
        arr = np.zeros(10, dtype=BAR_DTYPE)
        for i in range(10):
            arr[i]["timestamp"] = 1704067200000000 + i * 3600000000
            arr[i]["open"] = 110520 + i
            arr[i]["high"] = 110580 + i
            arr[i]["low"] = 110500 + i
            arr[i]["close"] = 110550 + i
            arr[i]["timeframe"] = 60

        bars = array_to_bars(arr, symbol="EURUSD", digits=5)

        assert len(bars) == 10
        assert bars[0].timestamp == 1704067200000000
        assert bars[9].timestamp == 1704067200000000 + 9 * 3600000000

    def test_bar_timeframe_conversion(self):
        """Test timeframe enum conversion through array."""
        for tf in [Timeframe.M1, Timeframe.M5, Timeframe.H1, Timeframe.D1]:
            bar = Bar(
                symbol="EURUSD",
                timeframe=tf,
                timestamp=1704067200000000,
                open=1.10520,
                high=1.10580,
                low=1.10500,
                close=1.10550,
            )

            arr = bar_to_array(bar, digits=5)
            recovered = array_to_bar(arr, symbol="EURUSD", digits=5)

            assert recovered.timeframe == tf
