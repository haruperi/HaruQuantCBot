"""
Symbol Specification model for HQT Trading System.

This module defines the SymbolSpecification data structure containing all
trading symbol parameters, contract specifications, and trading rules.

[REQ: DAT-FR-003] SymbolSpecification with all trading parameters.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SwapType(str, Enum):
    """
    Swap calculation method for overnight positions.

    Attributes:
        POINTS: Swap in points
        BASE_CURRENCY: Swap in base currency
        INTEREST: Swap as annual interest percentage
        MARGIN_CURRENCY: Swap in margin currency
    """

    POINTS = "POINTS"
    BASE_CURRENCY = "BASE_CURRENCY"
    INTEREST = "INTEREST"
    MARGIN_CURRENCY = "MARGIN_CURRENCY"


class TradeMode(str, Enum):
    """
    Allowed trade operations for a symbol.

    Attributes:
        DISABLED: Trading disabled
        LONG_ONLY: Only long positions allowed
        SHORT_ONLY: Only short positions allowed
        CLOSE_ONLY: Only closing existing positions allowed
        FULL: All trading operations allowed
    """

    DISABLED = "DISABLED"
    LONG_ONLY = "LONG_ONLY"
    SHORT_ONLY = "SHORT_ONLY"
    CLOSE_ONLY = "CLOSE_ONLY"
    FULL = "FULL"


class SymbolSpecification(BaseModel):
    """
    Complete specification for a trading symbol.

    Contains all parameters needed for trading calculations including:
    - Price precision and tick specifications
    - Contract and lot specifications
    - Margin requirements
    - Swap rates for overnight positions
    - Trading mode restrictions
    - Currency specifications

    This information is typically obtained from the broker and used for:
    - Price normalization and validation
    - Position sizing calculations
    - Margin requirement calculations
    - Profit/loss calculations
    - Risk management

    Attributes:
        name: Symbol name (e.g., "EURUSD", "XAUUSD", "US30")
        description: Human-readable description
        digits: Number of decimal places for price (e.g., 5 for EURUSD)
        point: Minimum price change (e.g., 0.00001 for 5-digit EURUSD)
        tick_size: Minimum price step (usually equal to point)
        tick_value: Value of one tick in account currency
        contract_size: Size of one lot in base currency (e.g., 100000 for EURUSD)
        margin_initial: Initial margin requirement percentage (e.g., 0.01 = 1%)
        margin_maintenance: Maintenance margin percentage
        swap_long: Swap rate for long positions
        swap_short: Swap rate for short positions
        swap_type: Method for calculating swap
        trade_mode: Allowed trading operations
        volume_min: Minimum trade volume (lots)
        volume_max: Maximum trade volume (lots)
        volume_step: Volume increment step (e.g., 0.01 for micro lots)
        currency_base: Base currency (first in pair, e.g., "EUR" in EURUSD)
        currency_profit: Profit currency (second in pair, e.g., "USD" in EURUSD)
        currency_margin: Currency used for margin calculation

    Example:
        ```python
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
        ```

    Validation:
        - All numeric values must be positive (except swap rates which can be negative)
        - volume_min <= volume_max
        - point and tick_size must be positive
    """

    model_config = ConfigDict(
        frozen=True,  # Make instances immutable
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    # Symbol identification
    name: str = Field(..., min_length=1, description="Symbol name (e.g., 'EURUSD')")
    description: str = Field(default="", description="Human-readable description")

    # Price precision
    digits: int = Field(..., ge=0, le=8, description="Decimal places for price")
    point: float = Field(..., gt=0, description="Minimum price change")
    tick_size: float = Field(..., gt=0, description="Minimum price step")
    tick_value: float = Field(..., gt=0, description="Value of one tick")

    # Contract specification
    contract_size: float = Field(..., gt=0, description="Size of one lot")

    # Margin requirements
    margin_initial: float = Field(..., gt=0, le=1.0, description="Initial margin percentage")
    margin_maintenance: float = Field(..., gt=0, le=1.0, description="Maintenance margin percentage")

    # Swap rates
    swap_long: float = Field(default=0.0, description="Swap rate for long positions")
    swap_short: float = Field(default=0.0, description="Swap rate for short positions")
    swap_type: SwapType = Field(default=SwapType.POINTS, description="Swap calculation method")

    # Trading restrictions
    trade_mode: TradeMode = Field(default=TradeMode.FULL, description="Allowed trade operations")

    # Volume limits
    volume_min: float = Field(..., gt=0, description="Minimum trade volume (lots)")
    volume_max: float = Field(..., gt=0, description="Maximum trade volume (lots)")
    volume_step: float = Field(..., gt=0, description="Volume increment step")

    # Currencies
    currency_base: str = Field(..., min_length=3, max_length=3, description="Base currency code")
    currency_profit: str = Field(..., min_length=3, max_length=3, description="Profit currency code")
    currency_margin: str = Field(..., min_length=3, max_length=3, description="Margin currency code")

    def normalize_price(self, price: float) -> float:
        """
        Normalize a price to the symbol's precision.

        Args:
            price: Raw price value

        Returns:
            Price rounded to the symbol's digit precision

        Example:
            ```python
            spec = SymbolSpecification(name="EURUSD", digits=5, ...)
            normalized = spec.normalize_price(1.105234567)
            # Returns: 1.10523
            ```
        """
        return round(price, self.digits)

    def normalize_volume(self, volume: float) -> float:
        """
        Normalize a volume to valid lot size.

        Rounds the volume to the nearest valid step and clamps to min/max.

        Args:
            volume: Desired volume in lots

        Returns:
            Normalized volume within allowed range

        Example:
            ```python
            spec = SymbolSpecification(
                name="EURUSD",
                volume_min=0.01,
                volume_max=100.0,
                volume_step=0.01,
                ...
            )
            normalized = spec.normalize_volume(0.567)
            # Returns: 0.57
            ```
        """
        # Round to nearest step
        steps = round(volume / self.volume_step)
        normalized = steps * self.volume_step

        # Clamp to min/max
        normalized = max(self.volume_min, min(self.volume_max, normalized))

        return normalized

    def calculate_margin(self, volume: float, price: float) -> float:
        """
        Calculate required margin for a position.

        Args:
            volume: Trade volume in lots
            price: Entry price

        Returns:
            Required margin in margin currency

        Example:
            ```python
            spec = SymbolSpecification(
                name="EURUSD",
                contract_size=100000.0,
                margin_initial=0.01,  # 1%
                ...
            )
            margin = spec.calculate_margin(volume=1.0, price=1.10)
            # Returns: 1100.0 (100000 * 1.10 * 0.01)
            ```
        """
        notional_value = volume * self.contract_size * price
        return notional_value * self.margin_initial

    def calculate_pip_value(self, volume: float, conversion_rate: float = 1.0) -> float:
        """
        Calculate the value of one pip for a given volume.

        Args:
            volume: Trade volume in lots
            conversion_rate: Conversion rate to account currency (default: 1.0)

        Returns:
            Value of one pip in account currency

        Example:
            ```python
            spec = SymbolSpecification(
                name="EURUSD",
                contract_size=100000.0,
                digits=5,
                point=0.00001,
                ...
            )
            pip_value = spec.calculate_pip_value(volume=1.0)
            # For standard lot EURUSD: $10 per pip
            ```
        """
        pip = 10 ** (-self.digits + 1)  # One pip (0.0001 for 5-digit quote)
        pip_value = volume * self.contract_size * pip * conversion_rate
        return pip_value

    def is_tradeable(self) -> bool:
        """
        Check if trading is currently allowed for this symbol.

        Returns:
            True if trading is allowed (not DISABLED or CLOSE_ONLY)
        """
        return self.trade_mode not in (TradeMode.DISABLED, TradeMode.CLOSE_ONLY)

    def can_open_long(self) -> bool:
        """Check if long positions can be opened."""
        return self.trade_mode in (TradeMode.FULL, TradeMode.LONG_ONLY)

    def can_open_short(self) -> bool:
        """Check if short positions can be opened."""
        return self.trade_mode in (TradeMode.FULL, TradeMode.SHORT_ONLY)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert specification to dictionary representation.

        Returns:
            Dictionary with all specification fields.
        """
        return {
            "name": self.name,
            "description": self.description,
            "digits": self.digits,
            "point": self.point,
            "tick_size": self.tick_size,
            "tick_value": self.tick_value,
            "contract_size": self.contract_size,
            "margin_initial": self.margin_initial,
            "margin_maintenance": self.margin_maintenance,
            "swap_long": self.swap_long,
            "swap_short": self.swap_short,
            "swap_type": self.swap_type.value,
            "trade_mode": self.trade_mode.value,
            "volume_min": self.volume_min,
            "volume_max": self.volume_max,
            "volume_step": self.volume_step,
            "currency_base": self.currency_base,
            "currency_profit": self.currency_profit,
            "currency_margin": self.currency_margin,
        }

    def __repr__(self) -> str:
        """Return string representation of the specification."""
        return (
            f"SymbolSpecification(name={self.name!r}, digits={self.digits}, "
            f"contract_size={self.contract_size}, margin={self.margin_initial:.2%})"
        )

    @classmethod
    def from_mt5(cls, mt5_symbol: Any) -> "SymbolSpecification":
        """
        Create a SymbolSpecification from MetaTrader 5 symbol info.

        MT5 symbol_info structure (from MetaTrader5 package):
        - name: str
        - description: str
        - digits: int
        - point: float
        - tick_size: float
        - tick_value: float
        - trade_contract_size: float
        - margin_initial: float (initial margin requirement)
        - margin_maintenance: float (maintenance margin)
        - swap_long: float
        - swap_short: float
        - swap_rollover3days: int (day of triple swap)
        - trade_mode: int (trade execution mode)
        - volume_min: float
        - volume_max: float
        - volume_step: float
        - currency_base: str
        - currency_profit: str
        - currency_margin: str

        Args:
            mt5_symbol: MT5 symbol_info object (from MetaTrader5.symbol_info())

        Returns:
            SymbolSpecification instance

        Example:
            ```python
            import MetaTrader5 as mt5

            mt5.initialize()
            symbol_info = mt5.symbol_info("EURUSD")

            spec = SymbolSpecification.from_mt5(symbol_info)
            print(spec.name, spec.digits, spec.contract_size)

            mt5.shutdown()
            ```

        Note:
            - MT5 margin values might be in different format (absolute vs percentage)
              depending on broker configuration. This assumes percentage format.
            - SwapType is inferred as POINTS by default (most common)
            - TradeMode is inferred from MT5 trade_mode flags
        """
        # Get basic symbol info
        name = mt5_symbol.name
        description = mt5_symbol.description if hasattr(mt5_symbol, "description") else ""
        digits = mt5_symbol.digits
        point = float(mt5_symbol.point)
        tick_size = float(mt5_symbol.trade_tick_size if hasattr(mt5_symbol, "trade_tick_size") else point)
        tick_value = float(mt5_symbol.trade_tick_value if hasattr(mt5_symbol, "trade_tick_value") else 1.0)
        contract_size = float(mt5_symbol.trade_contract_size)

        # Get margin requirements
        # MT5 might provide margin as absolute or percentage - we assume percentage
        # If margin values are very large (>10), convert to percentage
        margin_initial = float(getattr(mt5_symbol, "margin_initial", 0.01))
        if margin_initial > 10:  # Likely absolute value, convert to approximate percentage
            margin_initial = 0.01  # Default to 1%

        margin_maintenance = float(getattr(mt5_symbol, "margin_maintenance", margin_initial))
        if margin_maintenance > 10:
            margin_maintenance = margin_initial / 2  # Maintenance usually half of initial

        # Get swap rates
        swap_long = float(mt5_symbol.swap_long if hasattr(mt5_symbol, "swap_long") else 0.0)
        swap_short = float(mt5_symbol.swap_short if hasattr(mt5_symbol, "swap_short") else 0.0)

        # Infer swap type (default to POINTS, most common for forex)
        swap_type = SwapType.POINTS

        # Get trade mode from MT5 trade_mode flags
        # MT5 trade_mode: 0=Disabled, 1=LongOnly, 2=ShortOnly, 3=CloseOnly, 4=Full
        trade_mode_value = getattr(mt5_symbol, "trade_mode", 4)
        if trade_mode_value == 0:
            trade_mode = TradeMode.DISABLED
        elif trade_mode_value == 1:
            trade_mode = TradeMode.LONG_ONLY
        elif trade_mode_value == 2:
            trade_mode = TradeMode.SHORT_ONLY
        elif trade_mode_value == 3:
            trade_mode = TradeMode.CLOSE_ONLY
        else:
            trade_mode = TradeMode.FULL

        # Get volume limits
        volume_min = float(mt5_symbol.volume_min)
        volume_max = float(mt5_symbol.volume_max)
        volume_step = float(mt5_symbol.volume_step)

        # Get currencies
        currency_base = mt5_symbol.currency_base if hasattr(mt5_symbol, "currency_base") else "USD"
        currency_profit = mt5_symbol.currency_profit if hasattr(mt5_symbol, "currency_profit") else "USD"
        currency_margin = mt5_symbol.currency_margin if hasattr(mt5_symbol, "currency_margin") else "USD"

        return cls(
            name=name,
            description=description,
            digits=digits,
            point=point,
            tick_size=tick_size,
            tick_value=tick_value,
            contract_size=contract_size,
            margin_initial=margin_initial,
            margin_maintenance=margin_maintenance,
            swap_long=swap_long,
            swap_short=swap_short,
            swap_type=swap_type,
            trade_mode=trade_mode,
            volume_min=volume_min,
            volume_max=volume_max,
            volume_step=volume_step,
            currency_base=currency_base,
            currency_profit=currency_profit,
            currency_margin=currency_margin,
        )
