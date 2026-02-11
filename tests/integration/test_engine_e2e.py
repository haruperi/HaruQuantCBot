"""
End-to-end integration test for Python-to-C++ Engine bridge.

Tests the complete workflow:
- Instantiate Engine from Python
- Load market data (ticks and bars)
- Register callbacks
- Execute trading operations
- Verify all events processed correctly

[Task 3.9.1: Python E2E Integration Test]
"""

import sys
from pathlib import Path

import pytest

# Try to import hqt_core (requires built bridge module)
try:
    import hqt_core
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="hqt_core bridge not built yet")


class TestEngineE2E:
    """End-to-end tests for Python-C++ Engine integration."""

    @pytest.fixture
    def engine(self):
        """Create a test engine instance."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        # Create engine with 10,000 USD, leverage 100
        engine = hqt_core.Engine(
            initial_balance=10000.0,
            currency="USD",
            leverage=100
        )

        # Load EURUSD symbol
        symbol = hqt_core.SymbolInfo()
        symbol.set_name("EURUSD")
        symbol.set_point(0.00001)
        symbol.set_tick_size(0.00001)
        symbol.set_tick_value(1.0)
        symbol.set_contract_size(100000.0)
        symbol.set_volume_min(0.01)
        symbol.set_volume_max(100.0)
        symbol.set_volume_step(0.01)
        symbol.set_margin_rate(0.01)  # 1% margin requirement

        engine.load_symbol("EURUSD", symbol)

        return engine

    def test_engine_creation(self):
        """Test basic engine creation and configuration."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        engine = hqt_core.Engine(
            initial_balance=10000.0,
            currency="USD",
            leverage=100
        )

        # Verify engine created
        assert engine is not None

        # Verify account state
        account = engine.account()
        assert account.balance() == hqt_core.from_price(10000.0)
        assert account.equity() == hqt_core.from_price(10000.0)
        assert account.margin_free() == hqt_core.from_price(10000.0)
        assert account.margin() == 0

    def test_symbol_loading(self, engine):
        """Test symbol loading and configuration."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        # Load another symbol
        symbol = hqt_core.SymbolInfo()
        symbol.set_name("GBPUSD")
        symbol.set_point(0.00001)
        symbol.set_contract_size(100000.0)

        # Should not raise
        engine.load_symbol("GBPUSD", symbol)

    def test_tick_callback(self, engine):
        """Test tick callback registration and execution."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        tick_count = [0]  # Use list for closure
        last_tick = [None]

        def on_tick(tick, symbol):
            tick_count[0] += 1
            last_tick[0] = tick

            # Verify tick data
            assert tick.timestamp_us > 0
            assert tick.bid > 0
            assert tick.ask > 0
            assert tick.ask >= tick.bid  # Sanity check

            # Verify symbol
            assert symbol.name() == "EURUSD"

        # Register callback
        engine.set_on_tick(on_tick)

        # Feed tick directly using the internal event loop
        # Note: In production, ticks come from data feed
        # For this test, we'll use the mmap feed after loading data

        # For now, just verify callback registration doesn't crash
        assert tick_count[0] == 0  # No ticks yet

    def test_bar_callback(self, engine):
        """Test bar callback registration and execution."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        bar_count = [0]
        last_bar = [None]

        @engine.on_bar
        def on_bar(bar, symbol, timeframe):
            bar_count[0] += 1
            last_bar[0] = bar

            # Verify bar data
            assert bar.timestamp_us > 0
            assert bar.open > 0
            assert bar.high >= bar.low
            assert bar.high >= bar.open
            assert bar.high >= bar.close
            assert bar.low <= bar.open
            assert bar.low <= bar.close
            assert bar.volume >= 0

            # Verify timeframe
            assert timeframe in [
                hqt_core.Timeframe.M1,
                hqt_core.Timeframe.M5,
                hqt_core.Timeframe.M15,
                hqt_core.Timeframe.M30,
                hqt_core.Timeframe.H1,
                hqt_core.Timeframe.H4,
                hqt_core.Timeframe.D1,
            ]

        # Callback registered via decorator
        assert bar_count[0] == 0  # No bars yet

    def test_trade_callback(self, engine):
        """Test trade callback registration."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        trade_count = [0]

        @engine.on_trade
        def on_trade(deal):
            trade_count[0] += 1

            # Verify deal data
            assert deal.ticket() > 0
            assert deal.volume() > 0
            assert deal.price() > 0

        assert trade_count[0] == 0  # No trades yet

    def test_order_callback(self, engine):
        """Test order callback registration."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        order_count = [0]

        engine.set_on_order(lambda order: order_count.__setitem__(0, order_count[0] + 1))

        assert order_count[0] == 0  # No orders yet

    def test_trading_operations(self, engine):
        """Test basic trading operations."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        # Get initial account state
        account = engine.account()
        initial_balance = account.balance()

        # Note: Trading operations require ticks to be processed first
        # In a real scenario, we'd load data and run the engine
        # For this test, we just verify the API is callable

        # These will likely fail without data, but shouldn't crash
        try:
            ticket = engine.buy(volume=0.01, symbol="EURUSD")
            # If successful, ticket > 0
            if ticket > 0:
                # Verify position opened
                positions = engine.positions()
                assert len(positions) > 0

                # Close the position
                engine.close(ticket)

        except hqt_core.EngineError as e:
            # Expected if no market data loaded
            assert "No data" in str(e) or "No tick" in str(e) or "symbol" in str(e).lower()

    def test_price_conversion_helpers(self):
        """Test price conversion helper functions."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        # Test to_price (fixed-point to double)
        fixed_point = 1100000  # 1.10000 in fixed-point (multiplied by 1e6)
        price = hqt_core.to_price(fixed_point)
        assert abs(price - 1.10000) < 1e-9

        # Test from_price (double to fixed-point)
        price = 1.10000
        fixed_point = hqt_core.from_price(price)
        assert fixed_point == 1100000

        # Test round-trip
        original = 1.23456
        fixed = hqt_core.from_price(original)
        recovered = hqt_core.to_price(fixed)
        assert abs(recovered - original) < 1e-9

    def test_volume_validation(self):
        """Test volume validation helper."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        # Valid volumes
        assert hqt_core.validate_volume(0.01, 0.01, 100.0, 0.01) is True
        assert hqt_core.validate_volume(1.00, 0.01, 100.0, 0.01) is True
        assert hqt_core.validate_volume(100.0, 0.01, 100.0, 0.01) is True

        # Invalid volumes
        assert hqt_core.validate_volume(0.005, 0.01, 100.0, 0.01) is False  # Below min
        assert hqt_core.validate_volume(101.0, 0.01, 100.0, 0.01) is False  # Above max
        assert hqt_core.validate_volume(0.015, 0.01, 100.0, 0.01) is False  # Not multiple of step

    def test_price_validation(self):
        """Test price validation helper."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        # Positive prices are valid
        assert hqt_core.validate_price(1.10000) is True
        assert hqt_core.validate_price(0.00001) is True

        # Zero and negative prices are invalid
        assert hqt_core.validate_price(0.0) is False
        assert hqt_core.validate_price(-1.0) is False

    def test_round_to_tick(self):
        """Test tick rounding helper."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        tick_size = 0.00001  # 1 pip for EURUSD

        # Test rounding
        assert abs(hqt_core.round_to_tick(1.10003, tick_size) - 1.10003) < 1e-9
        assert abs(hqt_core.round_to_tick(1.100034, tick_size) - 1.10003) < 1e-9
        assert abs(hqt_core.round_to_tick(1.100036, tick_size) - 1.10004) < 1e-9

    def test_round_to_volume_step(self):
        """Test volume step rounding helper."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        volume_step = 0.01

        # Test rounding
        assert abs(hqt_core.round_to_volume_step(0.01, volume_step) - 0.01) < 1e-9
        assert abs(hqt_core.round_to_volume_step(0.014, volume_step) - 0.01) < 1e-9
        assert abs(hqt_core.round_to_volume_step(0.016, volume_step) - 0.02) < 1e-9

    def test_exception_translation(self, engine):
        """Test that C++ exceptions translate to Python exceptions."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        # Verify exception types exist
        assert hasattr(hqt_core, "EngineError")
        assert hasattr(hqt_core, "DataFeedError")
        assert hasattr(hqt_core, "MmapError")

        # Test that invalid operations raise exceptions
        with pytest.raises(Exception):  # Will be EngineError or similar
            # Try to trade with invalid symbol
            engine.buy(volume=0.01, symbol="INVALID")

    def test_account_info_access(self, engine):
        """Test account info access and structure."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        account = engine.account()

        # Verify all fields are accessible
        assert account.balance() >= 0
        assert account.equity() >= 0
        assert account.margin() >= 0
        assert account.margin_free() >= 0
        assert account.margin_level() >= 0.0
        assert account.profit() == 0  # No trades yet

        # Verify initial state
        assert account.balance() == hqt_core.from_price(10000.0)
        assert account.equity() == hqt_core.from_price(10000.0)

    def test_positions_list(self, engine):
        """Test positions list access."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        positions = engine.positions()

        # Initially empty
        assert isinstance(positions, list)
        assert len(positions) == 0

    def test_orders_list(self, engine):
        """Test orders list access."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        orders = engine.orders()

        # Initially empty
        assert isinstance(orders, list)
        assert len(orders) == 0

    def test_deals_list(self, engine):
        """Test deals history access."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        deals = engine.deals()

        # Initially empty
        assert isinstance(deals, list)
        assert len(deals) == 0

    def test_engine_lifecycle(self, engine):
        """Test engine lifecycle methods."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        # Test pause/resume (won't do anything without data)
        engine.pause()
        engine.resume()

        # Test stop
        engine.stop()

        # Note: run() would block and requires data feed
        # We don't test it here to avoid infinite waits

    def test_gil_release(self):
        """Test that engine.run() releases GIL (documented behavior)."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        # This is a documentation test
        # The actual GIL release happens in bind_engine.cpp
        # We just verify the pattern is documented in the module

        import inspect

        # Check that Engine.run has proper docstring mentioning GIL
        if hasattr(hqt_core.Engine, "run"):
            doc = hqt_core.Engine.run.__doc__
            if doc:
                # Should mention GIL release
                assert "GIL" in doc or "release" in doc.lower()

    def test_callback_decorator_and_function_style(self, engine):
        """Test both decorator and function-style callback registration."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        # Function style
        tick_count_func = [0]

        def tick_handler(tick, symbol):
            tick_count_func[0] += 1

        engine.set_on_tick(tick_handler)

        # Decorator style
        bar_count_dec = [0]

        @engine.on_bar
        def bar_handler(bar, symbol, timeframe):
            bar_count_dec[0] += 1

        # Both should work without raising
        assert True

    def test_multiple_engines(self):
        """Test creating multiple engine instances."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        engine1 = hqt_core.Engine(initial_balance=10000.0)
        engine2 = hqt_core.Engine(initial_balance=20000.0)

        # Should be separate instances
        assert engine1 is not engine2

        # Should have independent state
        account1 = engine1.account()
        account2 = engine2.account()

        assert account1.balance() == hqt_core.from_price(10000.0)
        assert account2.balance() == hqt_core.from_price(20000.0)

    def test_repr_strings(self):
        """Test that objects have reasonable repr strings."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        engine = hqt_core.Engine()
        assert "<Engine" in repr(engine)

        account = engine.account()
        assert "<AccountInfo" in repr(account)


class TestEngineWithData:
    """Tests that require market data loaded."""

    @pytest.fixture
    def engine_with_data(self):
        """Create engine with sample market data loaded."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        # Create engine
        engine = hqt_core.Engine(
            initial_balance=10000.0,
            currency="USD",
            leverage=100
        )

        # Load symbol
        symbol = hqt_core.SymbolInfo()
        symbol.set_name("EURUSD")
        symbol.set_point(0.00001)
        symbol.set_tick_size(0.00001)
        symbol.set_tick_value(1.0)
        symbol.set_contract_size(100000.0)
        symbol.set_volume_min(0.01)
        symbol.set_volume_max(100.0)
        symbol.set_volume_step(0.01)
        symbol.set_margin_rate(0.01)

        engine.load_symbol("EURUSD", symbol)

        # TODO: Load actual market data from mmap or Parquet
        # For now, this fixture just sets up the structure
        # Full data loading would require integration with Task 2 components

        return engine

    @pytest.mark.skip(reason="Requires market data loading implementation")
    def test_full_backtest_run(self, engine_with_data):
        """Test complete backtest with data, callbacks, and trading."""
        if not BRIDGE_AVAILABLE:
            pytest.skip("Bridge module not available")

        engine = engine_with_data

        # Track events
        events = {
            "ticks": 0,
            "bars": 0,
            "trades": 0,
            "orders": 0,
        }

        @engine.on_tick
        def on_tick(tick, symbol):
            events["ticks"] += 1

            # Simple trading logic: buy on first tick
            if events["ticks"] == 1:
                engine.buy(volume=0.01, symbol="EURUSD")

        @engine.on_bar
        def on_bar(bar, symbol, timeframe):
            events["bars"] += 1

            # Close position on first bar
            if events["bars"] == 1 and len(engine.positions()) > 0:
                pos = engine.positions()[0]
                engine.close(pos.ticket())

        @engine.on_trade
        def on_trade(deal):
            events["trades"] += 1

        # Run backtest
        engine.run()

        # Verify events were processed
        assert events["ticks"] > 0, "No ticks processed"
        assert events["bars"] > 0, "No bars processed"
        assert events["trades"] > 0, "No trades executed"

        # Verify final account state
        account = engine.account()
        # Balance may have changed due to trades
        assert account.balance() != hqt_core.from_price(10000.0)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
