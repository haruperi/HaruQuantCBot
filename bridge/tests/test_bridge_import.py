"""
Test basic import of hqt_core module

This test verifies that the nanobind bridge builds correctly
and the module can be imported in Python.
"""

import pytest


def test_import_module():
    """Test that hqt_core module can be imported"""
    import hqt_core

    assert hqt_core is not None


def test_module_version():
    """Test that module has version attribute"""
    import hqt_core

    assert hasattr(hqt_core, "__version__")
    assert isinstance(hqt_core.__version__, str)
    print(f"hqt_core version: {hqt_core.__version__}")


def test_module_constants():
    """Test module constants"""
    import hqt_core

    assert hasattr(hqt_core, "VERSION")
    assert hasattr(hqt_core, "BUILD_DATE")
    assert hasattr(hqt_core, "BUILD_TIME")


def test_enums_available():
    """Test that enums are exported"""
    import hqt_core

    # Check Timeframe enum
    assert hasattr(hqt_core, "Timeframe")
    assert hasattr(hqt_core.Timeframe, "M1")
    assert hasattr(hqt_core.Timeframe, "M5")
    assert hasattr(hqt_core.Timeframe, "H1")
    assert hasattr(hqt_core.Timeframe, "D1")

    # Check PositionType enum
    assert hasattr(hqt_core, "PositionType")
    assert hasattr(hqt_core.PositionType, "BUY")
    assert hasattr(hqt_core.PositionType, "SELL")

    # Check OrderType enum
    assert hasattr(hqt_core, "OrderType")
    assert hasattr(hqt_core.OrderType, "BUY")
    assert hasattr(hqt_core.OrderType, "SELL")
    assert hasattr(hqt_core.OrderType, "BUY_LIMIT")
    assert hasattr(hqt_core.OrderType, "SELL_STOP")


def test_types_available():
    """Test that data types are exported"""
    import hqt_core

    # Market data types
    assert hasattr(hqt_core, "Tick")
    assert hasattr(hqt_core, "Bar")
    assert hasattr(hqt_core, "SymbolInfo")

    # Account and trading types
    assert hasattr(hqt_core, "AccountInfo")
    assert hasattr(hqt_core, "PositionInfo")
    assert hasattr(hqt_core, "OrderInfo")
    assert hasattr(hqt_core, "DealInfo")


def test_engine_available():
    """Test that Engine class is exported"""
    import hqt_core

    assert hasattr(hqt_core, "Engine")


def test_engine_creation():
    """Test creating an Engine instance"""
    import hqt_core

    # Create engine with default parameters
    engine = hqt_core.Engine()
    assert engine is not None
    assert repr(engine).startswith("<Engine")

    # Create engine with custom parameters
    engine2 = hqt_core.Engine(initial_balance=50000.0, currency="EUR", leverage=50)
    assert engine2 is not None


def test_helper_functions():
    """Test helper functions are exported"""
    import hqt_core

    assert hasattr(hqt_core, "to_price")
    assert hasattr(hqt_core, "from_price")
    assert hasattr(hqt_core, "validate_volume")
    assert hasattr(hqt_core, "validate_price")
    assert hasattr(hqt_core, "round_to_tick")
    assert hasattr(hqt_core, "round_to_volume_step")


def test_price_conversion():
    """Test price conversion helpers"""
    import hqt_core

    # Test fixed-point to double
    fixed_point = 1100000  # 1.10000 in fixed-point
    price = hqt_core.to_price(fixed_point)
    assert abs(price - 1.10000) < 1e-6

    # Test double to fixed-point
    price = 1.10000
    fixed_point = hqt_core.from_price(price)
    assert fixed_point == 1100000


def test_exceptions_available():
    """Test that exceptions are exported"""
    import hqt_core

    assert hasattr(hqt_core, "EngineError")
    assert hasattr(hqt_core, "DataFeedError")
    assert hasattr(hqt_core, "MmapError")

    # Verify they're actual exception types
    assert issubclass(hqt_core.EngineError, Exception)
    assert issubclass(hqt_core.DataFeedError, Exception)
    assert issubclass(hqt_core.MmapError, Exception)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
