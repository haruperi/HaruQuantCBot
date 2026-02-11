"""
Dukascopy tick data provider for HQT Trading System.

This module implements the DataProvider interface for Dukascopy's free
historical tick data feeds. Downloads compressed .bi5 files via HTTPS,
decompresses them, and parses the binary format.

[REQ: DAT-FR-017] Dukascopy data provider
[REQ: DAT-FR-019] Incremental downloads
[REQ: DAT-FR-020] Progress callbacks
[SDD: §5.4] Data Providers
"""

import lzma
import struct
import time
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import quote

import pandas as pd
import requests

from hqt.data.models.bar import Timeframe
from hqt.data.providers.base import DataProvider
from hqt.foundation.exceptions.broker import ConnectionError
from hqt.foundation.exceptions.data import DataError


class DukascopyProvider(DataProvider):
    """
    Dukascopy historical tick data provider.

    Downloads tick data from Dukascopy's free public data feeds. Data is
    provided in compressed .bi5 files (LZMA compression) with a proprietary
    binary format. Files are organized by hour.

    Features:
        - Free historical tick data for major forex pairs
        - High-quality institutional data
        - Supports incremental downloads
        - Progress callbacks for UI integration
        - Automatic retry on transient failures

    Data Format:
        - Organized by: symbol/year/month/day/hour.bi5
        - Each file contains ticks for one hour
        - Binary format: 20 bytes per tick
        - LZMA compressed

    Limitations:
        - Tick data only (no bar data)
        - Some hours may be missing (weekends, holidays)
        - Limited to forex pairs and some CFDs

    Example:
        ```python
        from hqt.data.providers import DukascopyProvider
        from datetime import datetime, timedelta

        # Use as context manager
        with DukascopyProvider() as provider:
            # Check available symbols
            symbols = provider.get_available_symbols()
            print(f"Available: {len(symbols)} symbols")

            # Fetch tick data
            end = datetime.now()
            start = end - timedelta(days=7)

            def progress(current, total, eta):
                pct = 100 * current / total
                print(f"\\rProgress: {pct:.1f}% (ETA: {eta:.0f}s)", end="")

            ticks = provider.fetch_ticks(
                symbol="EURUSD",
                start=start,
                end=end,
                progress_callback=progress,
            )
            print(f"\\nFetched {len(ticks)} ticks")
        ```

    Note:
        Dukascopy uses specific symbol naming conventions (e.g., "EURUSD"
        not "EUR/USD"). Check get_available_symbols() for valid names.
    """

    # Dukascopy base URL
    BASE_URL = "https://datafeed.dukascopy.com/datafeed"

    # Major forex pairs available from Dukascopy
    # This is a subset - Dukascopy has many more symbols
    SUPPORTED_SYMBOLS = [
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD",
        "EURGBP", "EURJPY", "EURCHF", "GBPJPY", "GBPCHF", "AUDJPY", "AUDNZD",
        "EURAUD", "EURNZD", "GBPAUD", "GBPNZD", "NZDJPY", "CHFJPY", "CADCHF",
        "CADJPY", "AUDCAD", "NZDCAD", "AUDCHF", "NZDCHF", "EURCAD", "GBPCAD",
        "XAUUSD", "XAGUSD",  # Gold, Silver
    ]

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Initialize Dukascopy data provider.

        Args:
            timeout: HTTP request timeout in seconds
            max_retries: Maximum retry attempts for failed requests

        Note:
            No authentication required - Dukascopy data is publicly available.
        """
        self._timeout = timeout
        self._max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "HQT Trading System/1.0"
        })

    def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        progress_callback: Callable[[int, int, float], None] | None = None,
    ) -> pd.DataFrame:
        """
        Fetch historical bar data.

        Note:
            Dukascopy provides tick data only. This method is not implemented.
            To get bar data, fetch ticks and resample them.

        Raises:
            NotImplementedError: Dukascopy only provides tick data

        Example:
            ```python
            # Fetch ticks and resample to bars
            ticks = provider.fetch_ticks("EURUSD", start, end)
            bars = ticks.set_index('timestamp').resample('1H').agg({
                'bid': 'ohlc',
                'ask': 'ohlc',
            })
            ```
        """
        raise NotImplementedError(
            "Dukascopy provider only supports tick data. "
            "Fetch ticks and resample to bars using pandas."
        )

    def fetch_ticks(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        progress_callback: Callable[[int, int, float], None] | None = None,
    ) -> pd.DataFrame:
        """
        Fetch historical tick data from Dukascopy.

        Downloads and parses .bi5 files for each hour in the requested range.
        Missing hours (weekends, holidays) are skipped silently.

        Args:
            symbol: Dukascopy symbol name (e.g., "EURUSD")
            start: Start datetime (UTC)
            end: End datetime (UTC)
            progress_callback: Optional callback(current, total, eta_seconds)

        Returns:
            DataFrame with standardized tick columns

        Raises:
            ValueError: Invalid symbol
            ConnectionError: Network error
            DataError: Failed to parse data

        Note:
            Downloads one file per hour. Progress is updated after each hour.
            Large date ranges may take significant time.
        """
        if symbol not in self.SUPPORTED_SYMBOLS:
            raise ValueError(
                f"Symbol {symbol} not supported by Dukascopy. "
                f"Supported: {', '.join(self.SUPPORTED_SYMBOLS[:10])}..."
            )

        # Ensure UTC
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # Generate list of hours to download
        hours = self._generate_hour_list(start, end)
        total_hours = len(hours)

        if total_hours == 0:
            return pd.DataFrame(
                columns=["timestamp", "bid", "ask", "bid_volume", "ask_volume"]
            )

        # Download and parse each hour
        all_ticks = []
        start_time = time.time()

        for i, hour_dt in enumerate(hours):
            # Download and parse this hour
            try:
                ticks = self._fetch_hour(symbol, hour_dt)
                if len(ticks) > 0:
                    all_ticks.append(ticks)
            except Exception as e:
                # Log warning but continue (missing data is common)
                pass

            # Update progress
            if progress_callback:
                current = i + 1
                elapsed = time.time() - start_time
                if current > 0:
                    eta = (elapsed / current) * (total_hours - current)
                else:
                    eta = 0.0
                progress_callback(current, total_hours, eta)

        # Combine all hours
        if len(all_ticks) == 0:
            return pd.DataFrame(
                columns=["timestamp", "bid", "ask", "bid_volume", "ask_volume"]
            )

        df = pd.concat(all_ticks, ignore_index=True)

        # Sort by timestamp
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Filter to exact range
        start_us = int(start.timestamp() * 1_000_000)
        end_us = int(end.timestamp() * 1_000_000)
        df = df[(df["timestamp"] >= start_us) & (df["timestamp"] < end_us)]

        return df

    def _generate_hour_list(self, start: datetime, end: datetime) -> list[datetime]:
        """
        Generate list of hours to download.

        Args:
            start: Start datetime (UTC)
            end: End datetime (UTC)

        Returns:
            List of datetime objects at hour boundaries
        """
        # Round start down to hour
        start_hour = start.replace(minute=0, second=0, microsecond=0)

        # Round end up to hour
        if end.minute > 0 or end.second > 0 or end.microsecond > 0:
            end_hour = end.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            end_hour = end

        # Generate hourly timestamps
        hours = []
        current = start_hour
        while current < end_hour:
            hours.append(current)
            current += timedelta(hours=1)

        return hours

    def _fetch_hour(self, symbol: str, hour: datetime) -> pd.DataFrame:
        """
        Fetch and parse one hour of tick data.

        Args:
            symbol: Dukascopy symbol name
            hour: Hour datetime (UTC)

        Returns:
            DataFrame with ticks for this hour

        Raises:
            ConnectionError: Download failed
            DataError: Parse failed
        """
        # Build URL
        # Format: datafeed/{symbol}/{year}/{month-1}/{day-1}/{hour}h_ticks.bi5
        # Note: months and days are 0-indexed in Dukascopy URLs
        url = (
            f"{self.BASE_URL}/{quote(symbol)}/"
            f"{hour.year:04d}/{hour.month-1:02d}/{hour.day-1:02d}/"
            f"{hour.hour:02d}h_ticks.bi5"
        )

        # Download with retries
        for attempt in range(self._max_retries):
            try:
                response = self._session.get(url, timeout=self._timeout)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt == self._max_retries - 1:
                    raise ConnectionError(
                        error_code="BRK-020",
                        module="data.providers.dukascopy",
                        message=f"Failed to download {url}: {e}",
                        broker="Dukascopy",
                        endpoint=url,
                        symbol=symbol,
                        hour=hour.isoformat(),
                    )
                time.sleep(0.5 * (2 ** attempt))  # Exponential backoff
        else:
            # Should not reach here
            raise ConnectionError(
                error_code="BRK-020",
                module="data.providers.dukascopy",
                message=f"Failed to download {url} after {self._max_retries} attempts",
                broker="Dukascopy",
                endpoint=url,
                symbol=symbol,
                hour=hour.isoformat(),
            )

        # Decompress LZMA
        try:
            decompressed = lzma.decompress(response.content)
        except lzma.LZMAError as e:
            raise DataError(
                error_code="DAT-020",
                module="data.providers.dukascopy",
                message=f"Failed to decompress data: {e}",
                url=url,
                symbol=symbol,
                hour=hour.isoformat(),
            )

        # Parse binary format
        try:
            ticks = self._parse_bi5(decompressed, hour)
        except Exception as e:
            raise DataError(
                error_code="DAT-021",
                module="data.providers.dukascopy",
                message=f"Failed to parse binary data: {e}",
                url=url,
                symbol=symbol,
                hour=hour.isoformat(),
            )

        return ticks

    def _parse_bi5(self, data: bytes, hour: datetime) -> pd.DataFrame:
        """
        Parse Dukascopy .bi5 binary format.

        Format (big-endian):
            - timestamp_ms: int32 (milliseconds from hour start)
            - ask_price: int32 (scaled by point size)
            - bid_price: int32 (scaled by point size)
            - ask_volume: float32
            - bid_volume: float32

        Total: 20 bytes per tick

        Args:
            data: Decompressed binary data
            hour: Hour datetime for timestamp calculation

        Returns:
            DataFrame with parsed ticks

        Raises:
            DataError: Invalid data format
        """
        TICK_SIZE = 20
        num_ticks = len(data) // TICK_SIZE

        if len(data) % TICK_SIZE != 0:
            raise DataError(
                error_code="DAT-022",
                module="data.providers.dukascopy",
                message=f"Invalid data size: {len(data)} (not divisible by {TICK_SIZE})",
                data_size=len(data),
                expected_multiple=TICK_SIZE,
            )

        if num_ticks == 0:
            return pd.DataFrame(
                columns=["timestamp", "bid", "ask", "bid_volume", "ask_volume"]
            )

        # Parse all ticks
        timestamps = []
        bids = []
        asks = []
        bid_volumes = []
        ask_volumes = []

        hour_us = int(hour.timestamp() * 1_000_000)

        for i in range(num_ticks):
            offset = i * TICK_SIZE

            # Unpack tick (big-endian format)
            tick_data = struct.unpack(">IIIff", data[offset : offset + TICK_SIZE])

            timestamp_ms = tick_data[0]  # Milliseconds from hour start
            ask_price_scaled = tick_data[1]
            bid_price_scaled = tick_data[2]
            ask_volume = tick_data[3]
            bid_volume = tick_data[4]

            # Calculate absolute timestamp (microseconds)
            timestamp_us = hour_us + (timestamp_ms * 1000)

            # Convert price from scaled integer to float
            # Dukascopy uses point_value = 100000 for forex pairs
            ask_price = ask_price_scaled / 100000.0
            bid_price = bid_price_scaled / 100000.0

            timestamps.append(timestamp_us)
            bids.append(bid_price)
            asks.append(ask_price)
            bid_volumes.append(int(bid_volume * 1_000_000))  # Convert to units
            ask_volumes.append(int(ask_volume * 1_000_000))

        # Create DataFrame
        df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "bid": bids,
                "ask": asks,
                "bid_volume": bid_volumes,
                "ask_volume": ask_volumes,
            }
        )

        return df

    def get_available_symbols(self) -> list[str]:
        """
        Get list of symbols available from Dukascopy.

        Returns:
            List of supported symbol names

        Note:
            This returns a predefined list. Dukascopy may have additional
            symbols not listed here.
        """
        return self.SUPPORTED_SYMBOLS.copy()

    def get_available_timeframes(self, symbol: str) -> list[Timeframe]:
        """
        Get list of timeframes available for a symbol.

        Args:
            symbol: Dukascopy symbol name

        Returns:
            Empty list (Dukascopy provides tick data only)

        Note:
            Dukascopy only provides tick data. Fetch ticks and resample
            to any desired timeframe.
        """
        return []

    def get_provider_name(self) -> str:
        """Get provider display name."""
        return "Dukascopy"

    def close(self) -> None:
        """Close HTTP session and release resources."""
        self._session.close()
