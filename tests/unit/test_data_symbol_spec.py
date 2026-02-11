"""
Unit tests for SymbolSpecification model.

Tests the SymbolSpecification Pydantic model including:
- Valid and invalid creation
- Enums (SwapType, TradeMode)
- Helper methods (normalize, calculate)
- Immutability (frozen)
"""

import pytest

from hqt.data.models.symbol_spec import (
    SwapType,
    SymbolSpecification,
    TradeMode,
)


class TestSwapType:
    """Test suite for SwapType enum."""

    def test_swap_type_values(self):
        """Test all swap type values exist."""
        assert SwapType.POINTS.value == "POINTS"
        assert SwapType.BASE_CURRENCY.value == "BASE_CURRENCY"
        assert SwapType.INTEREST.value == "INTEREST"
        assert SwapType.MARGIN_CURRENCY.value == "MARGIN_CURRENCY"


class TestTradeMode:
    """Test suite for TradeMode enum."""

    def test_trade_mode_values(self):
        """Test all trade mode values exist."""
        assert TradeMode.DISABLED.value == "DISABLED"
        assert TradeMode.LONG_ONLY.value == "LONG_ONLY"
        assert TradeMode.SHORT_ONLY.value == "SHORT_ONLY"
        assert TradeMode.CLOSE_ONLY.value == "CLOSE_ONLY"
        assert TradeMode.FULL.value == "FULL"


class TestSymbolSpecification:
    """Test suite for SymbolSpecification model."""

    def test_symbol_spec_creation_valid(self):
        """Test creating a valid symbol specification."""
        spec = SymbolSpecification(
            name="EURUSD",
            description="Euro vs US Dollar",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            swap_long=-0.5,
            swap_short=0.2,
            swap_type=SwapType.POINTS,
            trade_mode=TradeMode.FULL,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )

        assert spec.name == "EURUSD"
        assert spec.digits == 5
        assert spec.contract_size == 100000.0
        assert spec.margin_initial == 0.01

    def test_symbol_spec_defaults(self):
        """Test default values."""
        spec = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )

        assert spec.description == ""
        assert spec.swap_long == 0.0
        assert spec.swap_short == 0.0
        assert spec.swap_type == SwapType.POINTS
        assert spec.trade_mode == TradeMode.FULL

    def test_symbol_spec_normalize_price(self):
        """Test price normalization to symbol digits."""
        spec = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )

        normalized = spec.normalize_price(1.105234567)
        assert normalized == pytest.approx(1.10523)

    def test_symbol_spec_normalize_volume(self):
        """Test volume normalization to valid step."""
        spec = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )

        # Test rounding to step
        assert spec.normalize_volume(0.567) == pytest.approx(0.57)
        assert spec.normalize_volume(1.234) == pytest.approx(1.23)

        # Test clamping to min
        assert spec.normalize_volume(0.005) == pytest.approx(0.01)

        # Test clamping to max
        assert spec.normalize_volume(150.0) == pytest.approx(100.0)

    def test_symbol_spec_calculate_margin(self):
        """Test margin calculation."""
        spec = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,  # 1%
            margin_maintenance=0.005,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )

        # 1 lot EURUSD at 1.10 with 1% margin
        # = 100000 * 1.10 * 0.01 = 1100
        margin = spec.calculate_margin(volume=1.0, price=1.10)
        assert margin == pytest.approx(1100.0)

    def test_symbol_spec_calculate_pip_value(self):
        """Test pip value calculation."""
        spec = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )

        # 1 standard lot EURUSD = $10 per pip
        # pip = 0.0001 (4th decimal for 5-digit quote)
        # pip_value = 1.0 * 100000 * 0.0001 * 1.0 = 10.0
        pip_value = spec.calculate_pip_value(volume=1.0)
        assert pip_value == pytest.approx(10.0)

    def test_symbol_spec_is_tradeable(self):
        """Test is_tradeable method."""
        spec_full = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            trade_mode=TradeMode.FULL,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )
        assert spec_full.is_tradeable() is True

        spec_disabled = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            trade_mode=TradeMode.DISABLED,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )
        assert spec_disabled.is_tradeable() is False

        spec_close_only = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            trade_mode=TradeMode.CLOSE_ONLY,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )
        assert spec_close_only.is_tradeable() is False

    def test_symbol_spec_can_open_long(self):
        """Test can_open_long method."""
        spec_full = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            trade_mode=TradeMode.FULL,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )
        assert spec_full.can_open_long() is True

        spec_long_only = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            trade_mode=TradeMode.LONG_ONLY,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )
        assert spec_long_only.can_open_long() is True

        spec_short_only = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            trade_mode=TradeMode.SHORT_ONLY,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )
        assert spec_short_only.can_open_long() is False

    def test_symbol_spec_can_open_short(self):
        """Test can_open_short method."""
        spec_full = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            trade_mode=TradeMode.FULL,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )
        assert spec_full.can_open_short() is True

        spec_short_only = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            trade_mode=TradeMode.SHORT_ONLY,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )
        assert spec_short_only.can_open_short() is True

        spec_long_only = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            trade_mode=TradeMode.LONG_ONLY,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )
        assert spec_long_only.can_open_short() is False

    def test_symbol_spec_invalid_margin_too_high(self):
        """Test that margin > 1.0 (100%) is rejected."""
        with pytest.raises(ValueError, match="less than or equal to 1"):
            SymbolSpecification(
                name="EURUSD",
                digits=5,
                point=0.00001,
                tick_size=0.00001,
                tick_value=1.0,
                contract_size=100000.0,
                margin_initial=1.5,  # 150%
                margin_maintenance=0.005,
                volume_min=0.01,
                volume_max=100.0,
                volume_step=0.01,
                currency_base="EUR",
                currency_profit="USD",
                currency_margin="USD",
            )

    def test_symbol_spec_invalid_currency_length(self):
        """Test that currency codes must be 3 characters."""
        with pytest.raises(ValueError):
            SymbolSpecification(
                name="EURUSD",
                digits=5,
                point=0.00001,
                tick_size=0.00001,
                tick_value=1.0,
                contract_size=100000.0,
                margin_initial=0.01,
                margin_maintenance=0.005,
                volume_min=0.01,
                volume_max=100.0,
                volume_step=0.01,
                currency_base="EU",  # Too short
                currency_profit="USD",
                currency_margin="USD",
            )

    def test_symbol_spec_frozen_immutable(self):
        """Test that symbol spec instances are immutable (frozen)."""
        spec = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )

        with pytest.raises(Exception):
            spec.contract_size = 50000.0

    def test_symbol_spec_to_dict(self):
        """Test symbol spec to_dict conversion."""
        spec = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )

        d = spec.to_dict()
        assert d["name"] == "EURUSD"
        assert d["digits"] == 5
        assert d["contract_size"] == 100000.0
        assert d["swap_type"] == "POINTS"
        assert d["trade_mode"] == "FULL"

    def test_symbol_spec_repr(self):
        """Test symbol spec string representation."""
        spec = SymbolSpecification(
            name="EURUSD",
            digits=5,
            point=0.00001,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            margin_initial=0.01,
            margin_maintenance=0.005,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            currency_base="EUR",
            currency_profit="USD",
            currency_margin="USD",
        )

        repr_str = repr(spec)
        assert "SymbolSpecification" in repr_str
        assert "EURUSD" in repr_str
