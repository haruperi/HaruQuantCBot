"""
Financial calculation utilities for trading.

This module provides utilities for pip value calculation, lot conversions,
profit calculations, and other trading-related computations.
"""

from typing import Literal


# Standard contract sizes for different instrument types
CONTRACT_SIZE_FOREX = 100000  # 1 standard lot = 100,000 units
CONTRACT_SIZE_METALS_GOLD = 100  # 1 lot gold = 100 troy ounces
CONTRACT_SIZE_METALS_SILVER = 5000  # 1 lot silver = 5,000 troy ounces
CONTRACT_SIZE_INDICES = 1  # Index CFDs typically 1:1
CONTRACT_SIZE_CRYPTO = 1  # Crypto typically 1:1


def lot_to_units(
    lots: float,
    contract_size: int = CONTRACT_SIZE_FOREX,
) -> float:
    """
    Convert lot size to units.

    Args:
        lots: Lot size (e.g., 1.0 = 1 standard lot, 0.01 = 1 micro lot)
        contract_size: Contract size (units per lot, default 100,000 for Forex)

    Returns:
        Units (base currency amount)

    Example:
        ```python
        from hqt.foundation.utils import lot_to_units

        # Forex (1 lot = 100,000 units)
        units = lot_to_units(1.0)  # 100,000
        units = lot_to_units(0.1)  # 10,000 (mini lot)
        units = lot_to_units(0.01)  # 1,000 (micro lot)

        # Gold (1 lot = 100 oz)
        units = lot_to_units(1.0, contract_size=100)  # 100
        ```
    """
    return lots * contract_size


def units_to_lots(
    units: float,
    contract_size: int = CONTRACT_SIZE_FOREX,
) -> float:
    """
    Convert units to lot size.

    Args:
        units: Units (base currency amount)
        contract_size: Contract size (units per lot, default 100,000 for Forex)

    Returns:
        Lot size

    Raises:
        ValueError: If contract_size is zero

    Example:
        ```python
        from hqt.foundation.utils import units_to_lots

        # Forex (1 lot = 100,000 units)
        lots = units_to_lots(100000)  # 1.0
        lots = units_to_lots(10000)   # 0.1 (mini lot)
        lots = units_to_lots(1000)    # 0.01 (micro lot)

        # Gold (1 lot = 100 oz)
        lots = units_to_lots(100, contract_size=100)  # 1.0
        ```
    """
    if contract_size == 0:
        raise ValueError("contract_size cannot be zero")

    return units / contract_size


def pip_value(
    symbol: str,
    lots: float,
    account_currency: str = "USD",
    exchange_rate: float = 1.0,
    pip_location: int = 4,
) -> float:
    """
    Calculate pip value in account currency.

    Args:
        symbol: Trading symbol (e.g., "EURUSD", "GBPJPY")
        lots: Lot size
        account_currency: Account currency (e.g., "USD", "EUR")
        exchange_rate: Exchange rate to convert to account currency if needed
        pip_location: Pip decimal location (4 for most pairs, 2 for JPY pairs)

    Returns:
        Pip value in account currency

    Example:
        ```python
        from hqt.foundation.utils import pip_value

        # EURUSD with USD account (1 pip = $10 per lot)
        pv = pip_value("EURUSD", 1.0, account_currency="USD")
        print(pv)  # 10.0

        # EURUSD with EUR account (need conversion)
        pv = pip_value("EURUSD", 1.0, account_currency="EUR", exchange_rate=0.9)
        print(pv)  # 9.0

        # GBPJPY with USD account (2 decimal places for JPY)
        pv = pip_value("GBPJPY", 1.0, account_currency="USD", pip_location=2)
        print(pv)  # 10.0

        # Mini lot
        pv = pip_value("EURUSD", 0.1, account_currency="USD")
        print(pv)  # 1.0
        ```
    """
    # Get quote currency (last 3 characters of symbol)
    quote_currency = symbol[-3:].upper()

    # Calculate base pip value (in quote currency)
    # For 4-decimal pairs: 1 pip = 0.0001
    # For 2-decimal pairs (JPY): 1 pip = 0.01
    pip_size = 10 ** (-pip_location)

    # Calculate pip value in quote currency
    # Pip value = (pip size) * (lot size in units)
    units = lot_to_units(lots)
    pip_value_quote = pip_size * units

    # Convert to account currency if needed
    if quote_currency == account_currency:
        # No conversion needed
        return pip_value_quote
    else:
        # Convert using exchange rate
        # exchange_rate should be quote_currency/account_currency rate
        return pip_value_quote * exchange_rate


def points_to_price(points: float, pip_location: int = 4) -> float:
    """
    Convert points to price difference.

    Args:
        points: Points (1 point = 1 pip for 4-decimal pairs, 0.1 pip for 5-decimal)
        pip_location: Pip decimal location (4 for most pairs, 2 for JPY pairs)

    Returns:
        Price difference

    Example:
        ```python
        from hqt.foundation.utils import points_to_price

        # 4-decimal pair (1 pip = 0.0001)
        price_diff = points_to_price(100, pip_location=4)
        print(price_diff)  # 0.01 (100 pips)

        # 2-decimal pair (JPY: 1 pip = 0.01)
        price_diff = points_to_price(100, pip_location=2)
        print(price_diff)  # 1.0 (100 pips)

        # Negative points
        price_diff = points_to_price(-50, pip_location=4)
        print(price_diff)  # -0.005 (-50 pips)
        ```
    """
    return points * (10 ** (-pip_location))


def price_to_points(price_diff: float, pip_location: int = 4) -> float:
    """
    Convert price difference to points.

    Args:
        price_diff: Price difference
        pip_location: Pip decimal location (4 for most pairs, 2 for JPY pairs)

    Returns:
        Points

    Example:
        ```python
        from hqt.foundation.utils import price_to_points

        # 4-decimal pair
        points = price_to_points(0.01, pip_location=4)
        print(points)  # 100.0 (100 pips)

        # 2-decimal pair (JPY)
        points = price_to_points(1.0, pip_location=2)
        print(points)  # 100.0 (100 pips)

        # Fractional pips
        points = price_to_points(0.00015, pip_location=4)
        print(points)  # 1.5 (1.5 pips)
        ```
    """
    return price_diff / (10 ** (-pip_location))


def profit_in_account_currency(
    entry_price: float,
    exit_price: float,
    lots: float,
    direction: Literal["long", "short"],
    pip_value_per_lot: float = 10.0,
    pip_location: int = 4,
) -> float:
    """
    Calculate profit/loss in account currency.

    Args:
        entry_price: Entry price
        exit_price: Exit price
        lots: Lot size
        direction: Trade direction ("long" or "short")
        pip_value_per_lot: Pip value per lot in account currency (default $10/pip)
        pip_location: Pip decimal location (4 for most pairs, 2 for JPY pairs)

    Returns:
        Profit/loss in account currency (positive = profit, negative = loss)

    Raises:
        ValueError: If direction is invalid

    Example:
        ```python
        from hqt.foundation.utils import profit_in_account_currency

        # Long trade profit (buy at 1.1000, sell at 1.1100)
        profit = profit_in_account_currency(
            entry_price=1.1000,
            exit_price=1.1100,
            lots=1.0,
            direction="long",
            pip_value_per_lot=10.0,
        )
        print(profit)  # 1000.0 (100 pips * $10/pip)

        # Short trade profit (sell at 1.1100, buy at 1.1000)
        profit = profit_in_account_currency(
            entry_price=1.1100,
            exit_price=1.1000,
            lots=1.0,
            direction="short",
            pip_value_per_lot=10.0,
        )
        print(profit)  # 1000.0 (100 pips * $10/pip)

        # Long trade loss (buy at 1.1100, sell at 1.1000)
        profit = profit_in_account_currency(
            entry_price=1.1100,
            exit_price=1.1000,
            lots=1.0,
            direction="long",
            pip_value_per_lot=10.0,
        )
        print(profit)  # -1000.0 (-100 pips * $10/pip)
        ```
    """
    if direction not in ("long", "short"):
        raise ValueError(f"Invalid direction: {direction}. Must be 'long' or 'short'")

    # Calculate price difference
    if direction == "long":
        price_diff = exit_price - entry_price
    else:  # short
        price_diff = entry_price - exit_price

    # Convert to points
    points = price_to_points(price_diff, pip_location)

    # Calculate profit
    return points * lots * pip_value_per_lot


def position_size_from_risk(
    account_balance: float,
    risk_percent: float,
    stop_loss_pips: float,
    pip_value_per_lot: float = 10.0,
) -> float:
    """
    Calculate position size based on risk percentage.

    Args:
        account_balance: Account balance in account currency
        risk_percent: Risk percentage per trade (e.g., 1.0 for 1%)
        stop_loss_pips: Stop loss distance in pips
        pip_value_per_lot: Pip value per lot in account currency (default $10/pip)

    Returns:
        Lot size

    Raises:
        ValueError: If any parameter is invalid

    Example:
        ```python
        from hqt.foundation.utils import position_size_from_risk

        # Calculate lot size for 1% risk with 50 pip stop loss
        lots = position_size_from_risk(
            account_balance=10000,
            risk_percent=1.0,
            stop_loss_pips=50,
            pip_value_per_lot=10.0,
        )
        print(lots)  # 0.2 lots

        # Calculation:
        # Risk amount = $10,000 * 1% = $100
        # Stop loss value = 50 pips * $10/pip per lot = $500 per lot
        # Lot size = $100 / $500 = 0.2 lots
        ```
    """
    if account_balance <= 0:
        raise ValueError(f"account_balance must be positive, got {account_balance}")

    if risk_percent <= 0 or risk_percent > 100:
        raise ValueError(f"risk_percent must be in (0, 100], got {risk_percent}")

    if stop_loss_pips <= 0:
        raise ValueError(f"stop_loss_pips must be positive, got {stop_loss_pips}")

    if pip_value_per_lot <= 0:
        raise ValueError(f"pip_value_per_lot must be positive, got {pip_value_per_lot}")

    # Calculate risk amount in account currency
    risk_amount = account_balance * (risk_percent / 100.0)

    # Calculate stop loss value per lot
    stop_loss_value_per_lot = stop_loss_pips * pip_value_per_lot

    # Calculate lot size
    lots = risk_amount / stop_loss_value_per_lot

    return lots


def kelly_criterion(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
) -> float:
    """
    Calculate optimal position size using Kelly Criterion.

    Args:
        win_rate: Win rate as decimal (e.g., 0.6 for 60%)
        avg_win: Average win amount
        avg_loss: Average loss amount (positive value)

    Returns:
        Kelly percentage (0.0 - 1.0, where 1.0 = 100% of capital)

    Raises:
        ValueError: If parameters are invalid

    Note:
        Full Kelly can be aggressive. Consider using fractional Kelly (e.g., 0.25 or 0.5).

    Example:
        ```python
        from hqt.foundation.utils import kelly_criterion

        # Calculate Kelly percentage
        kelly = kelly_criterion(
            win_rate=0.6,  # 60% win rate
            avg_win=150.0,  # Average win $150
            avg_loss=100.0,  # Average loss $100
        )
        print(f"Kelly: {kelly:.2%}")  # Kelly: 40.00%

        # Use fractional Kelly (25% of full Kelly)
        fractional_kelly = kelly * 0.25
        print(f"Fractional Kelly: {fractional_kelly:.2%}")  # 10.00%

        # Negative Kelly (don't trade)
        kelly = kelly_criterion(win_rate=0.4, avg_win=100, avg_loss=150)
        print(kelly)  # Negative value - unfavorable odds
        ```
    """
    if not 0 <= win_rate <= 1:
        raise ValueError(f"win_rate must be in [0, 1], got {win_rate}")

    if avg_win <= 0:
        raise ValueError(f"avg_win must be positive, got {avg_win}")

    if avg_loss <= 0:
        raise ValueError(f"avg_loss must be positive, got {avg_loss}")

    # Kelly formula: K = W - [(1-W) / R]
    # where W = win rate, R = avg_win / avg_loss (win/loss ratio)
    win_loss_ratio = avg_win / avg_loss
    lose_rate = 1.0 - win_rate

    kelly = win_rate - (lose_rate / win_loss_ratio)

    return kelly


def sharpe_ratio(
    returns: list[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Calculate Sharpe ratio from returns.

    Args:
        returns: List of period returns (e.g., daily returns as decimals)
        risk_free_rate: Annual risk-free rate (default 0.0)
        periods_per_year: Number of periods per year (252 for daily, 12 for monthly)

    Returns:
        Sharpe ratio (annualized)

    Raises:
        ValueError: If returns is empty or standard deviation is zero

    Example:
        ```python
        from hqt.foundation.utils import sharpe_ratio

        # Daily returns
        daily_returns = [0.01, -0.005, 0.015, -0.01, 0.02]

        # Calculate Sharpe ratio (annualized)
        sharpe = sharpe_ratio(daily_returns, risk_free_rate=0.02, periods_per_year=252)
        print(f"Sharpe: {sharpe:.2f}")

        # Monthly returns
        monthly_returns = [0.03, -0.01, 0.05, 0.02]
        sharpe = sharpe_ratio(monthly_returns, periods_per_year=12)
        print(f"Sharpe: {sharpe:.2f}")
        ```
    """
    if not returns:
        raise ValueError("returns cannot be empty")

    # Calculate mean and standard deviation
    n = len(returns)
    mean_return = sum(returns) / n

    if n < 2:
        raise ValueError("Need at least 2 returns to calculate standard deviation")

    variance = sum((r - mean_return) ** 2 for r in returns) / (n - 1)
    std_dev = variance ** 0.5

    if std_dev == 0:
        raise ValueError("Standard deviation is zero (no volatility)")

    # Annualize mean and standard deviation
    annual_mean = mean_return * periods_per_year
    annual_std = std_dev * (periods_per_year ** 0.5)

    # Calculate Sharpe ratio
    sharpe = (annual_mean - risk_free_rate) / annual_std

    return sharpe


def max_drawdown(equity_curve: list[float]) -> tuple[float, int, int]:
    """
    Calculate maximum drawdown from equity curve.

    Args:
        equity_curve: List of equity values over time

    Returns:
        Tuple of (max_drawdown_percent, peak_index, trough_index)

    Raises:
        ValueError: If equity_curve is empty or contains non-positive values

    Example:
        ```python
        from hqt.foundation.utils import max_drawdown

        # Equity curve
        equity = [10000, 10500, 10200, 9800, 9500, 10000, 10800]

        # Calculate max drawdown
        dd_pct, peak_idx, trough_idx = max_drawdown(equity)
        print(f"Max Drawdown: {dd_pct:.2%}")  # -9.52%
        print(f"Peak at index {peak_idx}: ${equity[peak_idx]}")
        print(f"Trough at index {trough_idx}: ${equity[trough_idx]}")
        ```
    """
    if not equity_curve:
        raise ValueError("equity_curve cannot be empty")

    if any(v <= 0 for v in equity_curve):
        raise ValueError("equity_curve must contain only positive values")

    max_dd = 0.0
    peak_idx = 0
    trough_idx = 0
    current_peak = equity_curve[0]
    current_peak_idx = 0

    for i, equity in enumerate(equity_curve):
        # Update peak if new high
        if equity > current_peak:
            current_peak = equity
            current_peak_idx = i

        # Calculate drawdown from current peak
        dd = (equity - current_peak) / current_peak

        # Update max drawdown if deeper
        if dd < max_dd:
            max_dd = dd
            peak_idx = current_peak_idx
            trough_idx = i

    return max_dd, peak_idx, trough_idx
