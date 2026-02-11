"""
Data provider factory and retry logic for HQT Trading System.

This module provides utilities for creating data providers and handling
transient failures with exponential backoff retry logic.

[SDD: §5.4] Data Providers
"""

import functools
import time
from typing import Any, Callable, TypeVar

from hqt.data.providers.base import DataProvider
from hqt.foundation.exceptions.broker import ConnectionError, TimeoutError

# Type variable for generic retry decorator
F = TypeVar("F", bound=Callable[..., Any])


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (ConnectionError, TimeoutError, Exception),
) -> Callable[[F], F]:
    """
    Decorator that retries a function on failure with exponential backoff.

    Retries the decorated function if it raises one of the specified exceptions.
    Delay between retries increases exponentially up to max_delay.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 0.5)
        max_delay: Maximum delay in seconds (default: 30.0)
        backoff_factor: Exponential backoff multiplier (default: 2.0)
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function with retry logic

    Example:
        ```python
        @with_retry(max_retries=5, initial_delay=1.0)
        def fetch_data():
            response = requests.get("https://api.example.com/data")
            response.raise_for_status()
            return response.json()

        # Will retry up to 5 times with exponential backoff
        data = fetch_data()
        ```

    Note:
        The function will sleep between retries. Total time spent in retries
        can be calculated as: sum(initial_delay * backoff_factor^i for i in range(max_retries))
        Example with defaults: 0.5 + 1.0 + 2.0 = 3.5 seconds
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # Don't sleep after last attempt
                    if attempt < max_retries:
                        # Sleep with exponential backoff
                        time.sleep(min(delay, max_delay))
                        delay *= backoff_factor

            # All retries exhausted, raise last exception
            raise last_exception  # type: ignore

        return wrapper  # type: ignore

    return decorator


def get_provider(provider_type: str, **config: Any) -> DataProvider:
    """
    Factory function to create data providers by name.

    Args:
        provider_type: Provider type name ("mt5", "dukascopy")
        **config: Provider-specific configuration parameters

    Returns:
        Configured DataProvider instance

    Raises:
        ValueError: Unknown provider type
        ImportError: Provider dependencies not installed

    Example:
        ```python
        # Create MT5 provider
        mt5 = get_provider("mt5")

        # Create MT5 provider with custom config
        mt5 = get_provider(
            "mt5",
            path="C:/Program Files/MT5/terminal64.exe",
            login=12345,
            password="secret",
            server="BrokerServer-Demo",
        )

        # Create Dukascopy provider
        duka = get_provider("dukascopy", timeout=60, max_retries=5)
        ```

    Available Providers:
        - "mt5": MetaTrader 5 provider
            Config: path, login, password, server
        - "dukascopy": Dukascopy tick data provider
            Config: timeout, max_retries
    """
    provider_type_lower = provider_type.lower()

    if provider_type_lower == "mt5":
        from hqt.data.providers.mt5_provider import MT5DataProvider

        return MT5DataProvider(**config)

    elif provider_type_lower == "dukascopy":
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        return DukascopyProvider(**config)

    else:
        raise ValueError(
            f"Unknown provider type: {provider_type}. "
            f"Available: mt5, dukascopy"
        )


def get_available_providers() -> dict[str, dict[str, Any]]:
    """
    Get information about available data providers.

    Returns:
        Dictionary mapping provider names to metadata

    Example:
        ```python
        providers = get_available_providers()
        for name, info in providers.items():
            print(f"{name}: {info['description']}")
            print(f"  Supports bars: {info['supports_bars']}")
            print(f"  Supports ticks: {info['supports_ticks']}")
        ```
    """
    return {
        "mt5": {
            "name": "MetaTrader 5",
            "description": "Official MT5 terminal data provider",
            "supports_bars": True,
            "supports_ticks": True,
            "supports_incremental": True,
            "requires": ["MetaTrader5"],
            "config_params": ["path", "login", "password", "server"],
        },
        "dukascopy": {
            "name": "Dukascopy",
            "description": "Free historical tick data from Dukascopy",
            "supports_bars": False,
            "supports_ticks": True,
            "supports_incremental": True,
            "requires": ["requests"],
            "config_params": ["timeout", "max_retries"],
        },
    }


# Convenience functions for common patterns


def download_with_progress(
    provider: DataProvider,
    symbol: str,
    start,
    end,
    fetch_type: str = "bars",
    timeframe=None,
) -> Any:
    """
    Download data with automatic progress display.

    Args:
        provider: Data provider instance
        symbol: Trading symbol
        start: Start datetime
        end: End datetime
        fetch_type: "bars" or "ticks"
        timeframe: Timeframe (required for bars)

    Returns:
        Downloaded DataFrame

    Example:
        ```python
        provider = get_provider("mt5")
        bars = download_with_progress(
            provider,
            "EURUSD",
            datetime(2024, 1, 1),
            datetime(2024, 12, 31),
            fetch_type="bars",
            timeframe=Timeframe.D1,
        )
        ```
    """

    def progress_callback(current: int, total: int, eta: float) -> None:
        """Display progress bar."""
        if total > 0:
            pct = 100 * current / total
            bar_width = 40
            filled = int(bar_width * current / total)
            bar = "█" * filled + "░" * (bar_width - filled)
            print(f"\r[{bar}] {pct:.1f}% (ETA: {eta:.0f}s)", end="", flush=True)
            if current == total:
                print()  # New line when complete

    if fetch_type == "bars":
        if timeframe is None:
            raise ValueError("timeframe required for bars")
        return provider.fetch_bars(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            progress_callback=progress_callback,
        )
    elif fetch_type == "ticks":
        return provider.fetch_ticks(
            symbol=symbol,
            start=start,
            end=end,
            progress_callback=progress_callback,
        )
    else:
        raise ValueError(f"Invalid fetch_type: {fetch_type}")
