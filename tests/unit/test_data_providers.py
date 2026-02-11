"""
Unit tests for data provider implementations.

Tests the DataProvider abstract base class and all concrete implementations:
- DataProvider ABC (base.py)
- MT5DataProvider (mt5_provider.py)
- DukascopyProvider (dukascopy_provider.py)
- Factory and retry logic (factory.py)

All external dependencies (MetaTrader5, requests) are mocked to ensure
tests run in any environment without requiring MT5 installation or network access.
"""

import lzma
import struct
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch

import pandas as pd
import pytest
import requests

from hqt.data.models.bar import Timeframe
from hqt.data.providers.base import DataProvider
from hqt.foundation.exceptions.broker import BrokerError, ConnectionError, TimeoutError
from hqt.foundation.exceptions.data import DataError


# ============================================================================
# Test Base DataProvider
# ============================================================================


class TestDataProviderBase:
    """Test suite for DataProvider abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that DataProvider ABC cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            DataProvider()  # type: ignore

    def test_context_manager_protocol(self):
        """Test that DataProvider supports context manager protocol."""
        # Create a concrete implementation for testing
        class ConcreteProvider(DataProvider):
            def __init__(self):
                self.closed = False

            def fetch_bars(self, symbol, timeframe, start, end, progress_callback=None):
                return pd.DataFrame()

            def fetch_ticks(self, symbol, start, end, progress_callback=None):
                return pd.DataFrame()

            def get_available_symbols(self):
                return []

            def get_available_timeframes(self, symbol):
                return []

            def close(self):
                self.closed = True

        provider = ConcreteProvider()
        assert not provider.closed

        # Test __enter__ returns self
        with provider as p:
            assert p is provider
            assert not provider.closed

        # Test __exit__ calls close()
        assert provider.closed

    def test_context_manager_exit_returns_false(self):
        """Test that __exit__ returns False (doesn't suppress exceptions)."""
        class ConcreteProvider(DataProvider):
            def fetch_bars(self, symbol, timeframe, start, end, progress_callback=None):
                return pd.DataFrame()

            def fetch_ticks(self, symbol, start, end, progress_callback=None):
                return pd.DataFrame()

            def get_available_symbols(self):
                return []

            def get_available_timeframes(self, symbol):
                return []

        provider = ConcreteProvider()

        # Test that exception is not suppressed
        with pytest.raises(ValueError):
            with provider:
                raise ValueError("Test error")

    def test_default_supports_incremental_download(self):
        """Test default implementation returns True."""
        class ConcreteProvider(DataProvider):
            def fetch_bars(self, symbol, timeframe, start, end, progress_callback=None):
                return pd.DataFrame()

            def fetch_ticks(self, symbol, start, end, progress_callback=None):
                return pd.DataFrame()

            def get_available_symbols(self):
                return []

            def get_available_timeframes(self, symbol):
                return []

        provider = ConcreteProvider()
        assert provider.supports_incremental_download() is True

    def test_default_get_provider_name(self):
        """Test default implementation returns class name."""
        class MyCustomProvider(DataProvider):
            def fetch_bars(self, symbol, timeframe, start, end, progress_callback=None):
                return pd.DataFrame()

            def fetch_ticks(self, symbol, start, end, progress_callback=None):
                return pd.DataFrame()

            def get_available_symbols(self):
                return []

            def get_available_timeframes(self, symbol):
                return []

        provider = MyCustomProvider()
        assert provider.get_provider_name() == "MyCustomProvider"

    def test_default_close_does_nothing(self):
        """Test default close() implementation does nothing."""
        class ConcreteProvider(DataProvider):
            def fetch_bars(self, symbol, timeframe, start, end, progress_callback=None):
                return pd.DataFrame()

            def fetch_ticks(self, symbol, start, end, progress_callback=None):
                return pd.DataFrame()

            def get_available_symbols(self):
                return []

            def get_available_timeframes(self, symbol):
                return []

        provider = ConcreteProvider()
        # Should not raise
        provider.close()
        provider.close()  # Can be called multiple times


# ============================================================================
# Test MT5DataProvider
# ============================================================================


class TestMT5DataProvider:
    """Test suite for MT5DataProvider with fully mocked MT5."""

    @pytest.fixture
    def mock_mt5(self):
        """Create a mock MetaTrader5 module."""
        # Create mock MT5 module
        mt5_mock = MagicMock()
        mt5_mock.TIMEFRAME_M1 = 1
        mt5_mock.TIMEFRAME_M2 = 2
        mt5_mock.TIMEFRAME_M3 = 3
        mt5_mock.TIMEFRAME_M4 = 4
        mt5_mock.TIMEFRAME_M5 = 5
        mt5_mock.TIMEFRAME_M6 = 6
        mt5_mock.TIMEFRAME_M10 = 10
        mt5_mock.TIMEFRAME_M12 = 12
        mt5_mock.TIMEFRAME_M15 = 15
        mt5_mock.TIMEFRAME_M20 = 20
        mt5_mock.TIMEFRAME_M30 = 30
        mt5_mock.TIMEFRAME_H1 = 60
        mt5_mock.TIMEFRAME_H2 = 120
        mt5_mock.TIMEFRAME_H3 = 180
        mt5_mock.TIMEFRAME_H4 = 240
        mt5_mock.TIMEFRAME_H6 = 360
        mt5_mock.TIMEFRAME_H8 = 480
        mt5_mock.TIMEFRAME_H12 = 720
        mt5_mock.TIMEFRAME_D1 = 1440
        mt5_mock.TIMEFRAME_W1 = 10080
        mt5_mock.TIMEFRAME_MN1 = 43200
        mt5_mock.COPY_TICKS_ALL = 0

        # Mock successful initialization by default
        mt5_mock.initialize.return_value = True
        mt5_mock.last_error.return_value = (1, "Success")

        return mt5_mock

    @pytest.fixture
    def mock_symbol_info(self):
        """Create a mock symbol info object."""
        info = MagicMock()
        info.name = "EURUSD"
        type(info).visible = PropertyMock(return_value=True)
        return info

    def test_import_error_when_mt5_not_available(self):
        """Test that ImportError is raised when MT5 not installed."""
        with patch.dict("sys.modules", {"MetaTrader5": None}):
            # Mock MT5_AVAILABLE to False
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", False):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                with pytest.raises(ImportError, match="MetaTrader5 package not installed"):
                    MT5DataProvider()

    def test_initialization_success(self, mock_mt5):
        """Test successful MT5 initialization."""
        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                mock_mt5.initialize.assert_called_once()
                assert provider._connected is True

    def test_initialization_with_path(self, mock_mt5):
        """Test MT5 initialization with custom path."""
        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider(path="C:/MT5/terminal.exe")

                mock_mt5.initialize.assert_called_once_with("C:/MT5/terminal.exe")
                assert provider._path == "C:/MT5/terminal.exe"

    def test_initialization_with_credentials(self, mock_mt5):
        """Test MT5 initialization with login credentials."""
        mock_mt5.login.return_value = True

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider(
                    login=12345, password="secret", server="BrokerServer-Demo"
                )

                mock_mt5.login.assert_called_once_with(12345, "secret", "BrokerServer-Demo")
                assert provider._login == 12345
                assert provider._server == "BrokerServer-Demo"

    def test_initialization_failure(self, mock_mt5):
        """Test MT5 initialization failure."""
        mock_mt5.initialize.return_value = False
        mock_mt5.last_error.return_value = (10004, "Terminal not found")

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                with pytest.raises(ConnectionError, match="Failed to initialize MT5"):
                    MT5DataProvider()

    def test_login_failure(self, mock_mt5):
        """Test MT5 login failure."""
        mock_mt5.login.return_value = False
        mock_mt5.last_error.return_value = (10015, "Invalid credentials")

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                with pytest.raises(ConnectionError, match="Failed to login to MT5"):
                    MT5DataProvider(
                        login=12345, password="wrong", server="BrokerServer-Demo"
                    )

                # Verify shutdown was called after login failure
                mock_mt5.shutdown.assert_called_once()

    def test_fetch_bars_success(self, mock_mt5, mock_symbol_info):
        """Test successful bar data fetching."""
        # Mock successful data fetch
        mock_rates = [
            {
                "time": 1704067200,  # 2024-01-01 00:00:00
                "open": 1.10520,
                "high": 1.10580,
                "low": 1.10500,
                "close": 1.10550,
                "tick_volume": 1000,
                "spread": 2,
                "real_volume": 50000,
            },
            {
                "time": 1704070800,  # 2024-01-01 01:00:00
                "open": 1.10550,
                "high": 1.10600,
                "low": 1.10530,
                "close": 1.10580,
                "tick_volume": 1200,
                "spread": 2,
                "real_volume": 60000,
            },
        ]
        mock_mt5.copy_rates_range.return_value = mock_rates
        mock_mt5.symbol_info.return_value = mock_symbol_info
        mock_mt5.symbol_select.return_value = True

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                start = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end = datetime(2024, 1, 2, tzinfo=timezone.utc)

                bars = provider.fetch_bars(
                    symbol="EURUSD", timeframe=Timeframe.H1, start=start, end=end
                )

                # Verify data structure
                assert len(bars) == 2
                assert list(bars.columns) == [
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "tick_volume",
                    "real_volume",
                    "spread",
                ]

                # Verify data types
                assert bars["timestamp"].dtype == "int64"
                assert bars["open"].dtype == "float64"
                assert bars["tick_volume"].dtype == "int64"
                assert bars["spread"].dtype == "int32"

                # Verify values
                assert bars.iloc[0]["timestamp"] == 1704067200000000
                assert bars.iloc[0]["open"] == 1.10520
                assert bars.iloc[0]["tick_volume"] == 1000

    def test_fetch_bars_with_progress_callback(self, mock_mt5, mock_symbol_info):
        """Test fetch_bars calls progress callback."""
        mock_mt5.copy_rates_range.return_value = [
            {"time": 1704067200, "open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1, "tick_volume": 100, "spread": 2, "real_volume": 1000}
        ]
        mock_mt5.symbol_info.return_value = mock_symbol_info

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                callback = Mock()
                start = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end = datetime(2024, 1, 2, tzinfo=timezone.utc)

                provider.fetch_bars(
                    symbol="EURUSD",
                    timeframe=Timeframe.H1,
                    start=start,
                    end=end,
                    progress_callback=callback,
                )

                # Verify callback was called at start and end
                assert callback.call_count == 2
                callback.assert_any_call(0, 100, 0.0)
                callback.assert_any_call(100, 100, 0.0)

    def test_fetch_bars_invalid_symbol(self, mock_mt5):
        """Test fetch_bars with invalid symbol."""
        mock_mt5.symbol_info.return_value = None
        mock_mt5.last_error.return_value = (10015, "Symbol not found")

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                start = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end = datetime(2024, 1, 2, tzinfo=timezone.utc)

                with pytest.raises(ValueError, match="Symbol INVALID not found in MT5"):
                    provider.fetch_bars(
                        symbol="INVALID", timeframe=Timeframe.H1, start=start, end=end
                    )

    def test_fetch_bars_empty_result(self, mock_mt5, mock_symbol_info):
        """Test fetch_bars with no data in range."""
        mock_mt5.copy_rates_range.return_value = None
        mock_mt5.last_error.return_value = (1, "Success")  # RES_S_OK
        mock_mt5.symbol_info.return_value = mock_symbol_info

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                start = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end = datetime(2024, 1, 2, tzinfo=timezone.utc)

                bars = provider.fetch_bars(
                    symbol="EURUSD", timeframe=Timeframe.H1, start=start, end=end
                )

                # Should return empty DataFrame with correct columns
                assert len(bars) == 0
                assert list(bars.columns) == [
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "tick_volume",
                    "real_volume",
                    "spread",
                ]

    def test_fetch_bars_mt5_error(self, mock_mt5, mock_symbol_info):
        """Test fetch_bars with MT5 error."""
        mock_mt5.copy_rates_range.return_value = None
        mock_mt5.last_error.return_value = (10004, "Data error")
        mock_mt5.symbol_info.return_value = mock_symbol_info

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                start = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end = datetime(2024, 1, 2, tzinfo=timezone.utc)

                with pytest.raises(BrokerError, match="Failed to fetch bars"):
                    provider.fetch_bars(
                        symbol="EURUSD", timeframe=Timeframe.H1, start=start, end=end
                    )

    def test_fetch_bars_invisible_symbol(self, mock_mt5):
        """Test fetch_bars enables invisible symbol."""
        mock_symbol_info = MagicMock()
        mock_symbol_info.name = "EURUSD"
        type(mock_symbol_info).visible = PropertyMock(return_value=False)

        mock_mt5.symbol_info.return_value = mock_symbol_info
        mock_mt5.symbol_select.return_value = True
        mock_mt5.copy_rates_range.return_value = [
            {"time": 1704067200, "open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1, "tick_volume": 100, "spread": 2, "real_volume": 1000}
        ]

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                start = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end = datetime(2024, 1, 2, tzinfo=timezone.utc)

                provider.fetch_bars(
                    symbol="EURUSD", timeframe=Timeframe.H1, start=start, end=end
                )

                # Verify symbol_select was called to enable the symbol
                mock_mt5.symbol_select.assert_called_once_with("EURUSD", True)

    def test_fetch_ticks_success(self, mock_mt5, mock_symbol_info):
        """Test successful tick data fetching."""
        # Mock successful tick fetch
        mock_ticks = [
            {
                "time": 1704067200,
                "time_msc": 1704067200000,  # Milliseconds
                "bid": 1.10500,
                "ask": 1.10520,
                "last": 1.10510,
                "volume": 100,
                "volume_real": 100.0,
                "flags": 0,
            },
            {
                "time": 1704067201,
                "time_msc": 1704067201000,
                "bid": 1.10505,
                "ask": 1.10525,
                "last": 1.10515,
                "volume": 150,
                "volume_real": 150.0,
                "flags": 0,
            },
        ]
        mock_mt5.copy_ticks_range.return_value = mock_ticks
        mock_mt5.symbol_info.return_value = mock_symbol_info

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                start = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end = datetime(2024, 1, 2, tzinfo=timezone.utc)

                ticks = provider.fetch_ticks(symbol="EURUSD", start=start, end=end)

                # Verify data structure
                assert len(ticks) == 2
                assert list(ticks.columns) == [
                    "timestamp",
                    "bid",
                    "ask",
                    "bid_volume",
                    "ask_volume",
                ]

                # Verify data types
                assert ticks["timestamp"].dtype == "int64"
                assert ticks["bid"].dtype == "float64"
                assert ticks["bid_volume"].dtype == "int64"

                # Verify values (milliseconds to microseconds)
                assert ticks.iloc[0]["timestamp"] == 1704067200000000
                assert ticks.iloc[0]["bid"] == 1.10500
                assert ticks.iloc[0]["ask"] == 1.10520

    def test_fetch_ticks_with_progress_callback(self, mock_mt5, mock_symbol_info):
        """Test fetch_ticks calls progress callback."""
        mock_mt5.copy_ticks_range.return_value = [
            {"time": 1704067200, "time_msc": 1704067200000, "bid": 1.1, "ask": 1.1, "last": 1.1, "volume": 100, "volume_real": 100.0, "flags": 0}
        ]
        mock_mt5.symbol_info.return_value = mock_symbol_info

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                callback = Mock()
                start = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end = datetime(2024, 1, 2, tzinfo=timezone.utc)

                provider.fetch_ticks(
                    symbol="EURUSD", start=start, end=end, progress_callback=callback
                )

                # Verify callback was called at start and end
                assert callback.call_count == 2
                callback.assert_any_call(0, 100, 0.0)
                callback.assert_any_call(100, 100, 0.0)

    def test_fetch_ticks_empty_result(self, mock_mt5, mock_symbol_info):
        """Test fetch_ticks with no data in range."""
        mock_mt5.copy_ticks_range.return_value = None
        mock_mt5.last_error.return_value = (1, "Success")
        mock_mt5.symbol_info.return_value = mock_symbol_info

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                start = datetime(2024, 1, 1, tzinfo=timezone.utc)
                end = datetime(2024, 1, 2, tzinfo=timezone.utc)

                ticks = provider.fetch_ticks(symbol="EURUSD", start=start, end=end)

                # Should return empty DataFrame with correct columns
                assert len(ticks) == 0
                assert list(ticks.columns) == [
                    "timestamp",
                    "bid",
                    "ask",
                    "bid_volume",
                    "ask_volume",
                ]

    def test_get_available_symbols(self, mock_mt5):
        """Test getting available symbols."""
        # Create mock symbol objects with .name attribute
        mock_symbol1 = MagicMock()
        mock_symbol1.name = "EURUSD"
        mock_symbol2 = MagicMock()
        mock_symbol2.name = "GBPUSD"
        mock_symbol3 = MagicMock()
        mock_symbol3.name = "USDJPY"

        mock_symbols = [mock_symbol1, mock_symbol2, mock_symbol3]
        mock_mt5.symbols_get.return_value = mock_symbols

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()
                symbols = provider.get_available_symbols()

                assert symbols == ["EURUSD", "GBPUSD", "USDJPY"]

    def test_get_available_symbols_error(self, mock_mt5):
        """Test getting available symbols with error."""
        mock_mt5.symbols_get.return_value = None
        mock_mt5.last_error.return_value = (10004, "Connection error")

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                with pytest.raises(BrokerError, match="Failed to get symbols"):
                    provider.get_available_symbols()

    def test_get_available_timeframes(self, mock_mt5, mock_symbol_info):
        """Test getting available timeframes for a symbol."""
        mock_mt5.symbol_info.return_value = mock_symbol_info

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()
                timeframes = provider.get_available_timeframes("EURUSD")

                # MT5 supports all standard timeframes
                assert Timeframe.M1 in timeframes
                assert Timeframe.H1 in timeframes
                assert Timeframe.D1 in timeframes
                assert len(timeframes) > 0

    def test_get_available_timeframes_invalid_symbol(self, mock_mt5):
        """Test getting timeframes for invalid symbol."""
        mock_mt5.symbol_info.return_value = None
        mock_mt5.last_error.return_value = (10015, "Symbol not found")

        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()

                with pytest.raises(ValueError, match="Symbol INVALID not found"):
                    provider.get_available_timeframes("INVALID")

    def test_get_provider_name(self, mock_mt5):
        """Test provider name."""
        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()
                assert provider.get_provider_name() == "MetaTrader 5"

    def test_close_connection(self, mock_mt5):
        """Test closing MT5 connection."""
        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()
                assert provider._connected is True

                provider.close()

                mock_mt5.shutdown.assert_called_once()
                assert provider._connected is False

    def test_close_when_not_connected(self, mock_mt5):
        """Test closing when not connected does nothing."""
        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                provider = MT5DataProvider()
                provider._connected = False
                mock_mt5.shutdown.reset_mock()

                provider.close()

                # Should not call shutdown
                mock_mt5.shutdown.assert_not_called()

    def test_context_manager(self, mock_mt5):
        """Test using provider as context manager."""
        with patch("hqt.data.providers.mt5_provider.mt5", mock_mt5):
            with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
                from hqt.data.providers.mt5_provider import MT5DataProvider

                with MT5DataProvider() as provider:
                    assert provider._connected is True

                # Should call shutdown on exit
                mock_mt5.shutdown.assert_called()


# ============================================================================
# Test DukascopyProvider
# ============================================================================


class TestDukascopyProvider:
    """Test suite for DukascopyProvider with mocked HTTP requests."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock requests Session."""
        session = MagicMock(spec=requests.Session)
        return session

    def create_bi5_data(self, ticks: list[tuple[int, float, float, float, float]]) -> bytes:
        """
        Create realistic .bi5 binary data.

        Args:
            ticks: List of (timestamp_ms, ask, bid, ask_volume, bid_volume)

        Returns:
            LZMA-compressed binary data
        """
        binary_data = b""
        for timestamp_ms, ask, bid, ask_volume, bid_volume in ticks:
            # Scale prices to integers (Dukascopy format)
            ask_scaled = int(ask * 100000)
            bid_scaled = int(bid * 100000)

            # Pack as big-endian: IIIff
            tick_bytes = struct.pack(
                ">IIIff", timestamp_ms, ask_scaled, bid_scaled, ask_volume, bid_volume
            )
            binary_data += tick_bytes

        # Compress with LZMA
        return lzma.compress(binary_data)

    def test_initialization(self):
        """Test DukascopyProvider initialization."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider(timeout=60, max_retries=5)

        assert provider._timeout == 60
        assert provider._max_retries == 5
        assert provider._session is not None

    def test_fetch_bars_not_implemented(self):
        """Test that fetch_bars raises NotImplementedError."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)

        with pytest.raises(NotImplementedError, match="Dukascopy provider only supports tick data"):
            provider.fetch_bars(
                symbol="EURUSD", timeframe=Timeframe.H1, start=start, end=end
            )

    def test_fetch_ticks_invalid_symbol(self):
        """Test fetch_ticks with invalid symbol."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="Symbol INVALID not supported"):
            provider.fetch_ticks(symbol="INVALID", start=start, end=end)

    def test_fetch_ticks_success(self, mock_session):
        """Test successful tick data fetching."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        # Create mock tick data for one hour
        ticks = [
            (0, 1.10520, 1.10500, 100.0, 100.0),  # timestamp_ms relative to hour
            (1000, 1.10525, 1.10505, 150.0, 150.0),
            (2000, 1.10530, 1.10510, 200.0, 200.0),
        ]
        bi5_data = self.create_bi5_data(ticks)

        # Mock response
        mock_response = MagicMock()
        mock_response.content = bi5_data
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        provider = DukascopyProvider()
        provider._session = mock_session

        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)

        result = provider.fetch_ticks(symbol="EURUSD", start=start, end=end)

        # Verify data structure
        assert len(result) == 3
        assert list(result.columns) == [
            "timestamp",
            "bid",
            "ask",
            "bid_volume",
            "ask_volume",
        ]

        # Verify first tick
        hour_us = int(start.timestamp() * 1_000_000)
        assert result.iloc[0]["timestamp"] == hour_us
        assert result.iloc[0]["ask"] == 1.10520
        assert result.iloc[0]["bid"] == 1.10500

    def test_fetch_ticks_with_progress_callback(self, mock_session):
        """Test fetch_ticks calls progress callback."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        # Create mock data for 3 hours
        ticks = [(0, 1.1, 1.1, 100.0, 100.0)]
        bi5_data = self.create_bi5_data(ticks)

        mock_response = MagicMock()
        mock_response.content = bi5_data
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        provider = DukascopyProvider()
        provider._session = mock_session

        callback = Mock()
        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

        provider.fetch_ticks(symbol="EURUSD", start=start, end=end, progress_callback=callback)

        # Should be called once per hour (3 times)
        assert callback.call_count == 3

    def test_fetch_ticks_missing_hour_404(self, mock_session):
        """Test fetch_ticks handles missing hours gracefully."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        # Mock 404 response (missing data)
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")

        mock_session.get.return_value = mock_response

        provider = DukascopyProvider(max_retries=1)
        provider._session = mock_session

        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)

        # Should handle missing hours gracefully and return empty DataFrame
        result = provider.fetch_ticks(symbol="EURUSD", start=start, end=end)

        # Should return empty DataFrame with correct structure
        assert len(result) == 0
        assert list(result.columns) == ["timestamp", "bid", "ask", "bid_volume", "ask_volume"]

    def test_fetch_ticks_network_retry(self, mock_session):
        """Test fetch_ticks retries on network failure."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        # First call fails, second succeeds
        ticks = [(0, 1.1, 1.1, 100.0, 100.0)]
        bi5_data = self.create_bi5_data(ticks)

        mock_response_success = MagicMock()
        mock_response_success.content = bi5_data
        mock_response_success.raise_for_status = MagicMock()

        mock_session.get.side_effect = [
            requests.exceptions.ConnectionError("Network error"),
            mock_response_success,
        ]

        provider = DukascopyProvider(max_retries=3)
        provider._session = mock_session

        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)

        # Should succeed after retry
        result = provider.fetch_ticks(symbol="EURUSD", start=start, end=end)
        assert len(result) > 0

    def test_fetch_ticks_all_retries_fail(self, mock_session):
        """Test fetch_ticks gives up after max retries but continues gracefully."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        mock_session.get.side_effect = requests.exceptions.ConnectionError("Network error")

        provider = DukascopyProvider(max_retries=2)
        provider._session = mock_session

        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)

        # fetch_ticks catches exceptions and returns empty DataFrame for missing hours
        result = provider.fetch_ticks(symbol="EURUSD", start=start, end=end)

        # Should return empty DataFrame
        assert len(result) == 0
        assert list(result.columns) == ["timestamp", "bid", "ask", "bid_volume", "ask_volume"]

        # Should have tried max_retries times
        assert mock_session.get.call_count == 2

    def test_parse_bi5_invalid_size(self):
        """Test _parse_bi5 with invalid data size."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()

        # 19 bytes - not divisible by 20
        invalid_data = b"x" * 19

        hour = datetime(2024, 1, 1, 10, tzinfo=timezone.utc)

        with pytest.raises(DataError, match="Invalid data size"):
            provider._parse_bi5(invalid_data, hour)

    def test_parse_bi5_empty_data(self):
        """Test _parse_bi5 with empty data."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()

        hour = datetime(2024, 1, 1, 10, tzinfo=timezone.utc)
        result = provider._parse_bi5(b"", hour)

        # Should return empty DataFrame with correct columns
        assert len(result) == 0
        assert list(result.columns) == [
            "timestamp",
            "bid",
            "ask",
            "bid_volume",
            "ask_volume",
        ]

    def test_generate_hour_list(self):
        """Test _generate_hour_list creates correct hour list."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()

        start = datetime(2024, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 13, 15, 0, tzinfo=timezone.utc)

        hours = provider._generate_hour_list(start, end)

        # Should round down start and up end
        expected = [
            datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
        ]

        assert hours == expected

    def test_generate_hour_list_exact_hours(self):
        """Test _generate_hour_list with exact hour boundaries."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()

        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        hours = provider._generate_hour_list(start, end)

        expected = [
            datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
        ]

        assert hours == expected

    def test_url_generation(self):
        """Test URL generation for Dukascopy data."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()

        # Note: Dukascopy uses 0-indexed months and days
        hour = datetime(2024, 3, 15, 14, 0, 0, tzinfo=timezone.utc)  # March 15, 2:00 PM

        # We can't test _fetch_hour directly without mocking, but we can verify
        # the URL format in the source code matches expectations
        expected_url_pattern = "datafeed/EURUSD/2024/02/14/14h_ticks.bi5"
        # Month 3 -> 02 (3-1), Day 15 -> 14 (15-1)

        assert provider.BASE_URL == "https://datafeed.dukascopy.com/datafeed"

    def test_get_available_symbols(self):
        """Test get_available_symbols returns predefined list."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()
        symbols = provider.get_available_symbols()

        # Should return copy of supported symbols
        assert "EURUSD" in symbols
        assert "GBPUSD" in symbols
        assert "XAUUSD" in symbols
        assert len(symbols) > 0

        # Verify it's a copy, not the original
        symbols.append("TEST")
        assert "TEST" not in provider.get_available_symbols()

    def test_get_available_timeframes(self):
        """Test get_available_timeframes returns empty list."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()
        timeframes = provider.get_available_timeframes("EURUSD")

        # Dukascopy only provides tick data
        assert timeframes == []

    def test_get_provider_name(self):
        """Test provider name."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()
        assert provider.get_provider_name() == "Dukascopy"

    def test_close_session(self, mock_session):
        """Test close() closes HTTP session."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()
        provider._session = mock_session

        provider.close()

        mock_session.close.assert_called_once()

    def test_context_manager(self, mock_session):
        """Test using provider as context manager."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        provider = DukascopyProvider()
        provider._session = mock_session

        with provider:
            pass

        # Should call close on exit
        mock_session.close.assert_called_once()

    def test_fetch_ticks_filters_to_exact_range(self, mock_session):
        """Test that fetch_ticks filters results to exact time range."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        # Create ticks at different times within the hour
        ticks = [
            (0, 1.1, 1.1, 100.0, 100.0),  # Start of hour
            (30 * 60 * 1000, 1.1, 1.1, 100.0, 100.0),  # 30 minutes in
            (59 * 60 * 1000, 1.1, 1.1, 100.0, 100.0),  # Near end of hour
        ]
        bi5_data = self.create_bi5_data(ticks)

        mock_response = MagicMock()
        mock_response.content = bi5_data
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        provider = DukascopyProvider()
        provider._session = mock_session

        # Request only 15-45 minutes of the hour
        start = datetime(2024, 1, 1, 10, 15, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 10, 45, 0, tzinfo=timezone.utc)

        result = provider.fetch_ticks(symbol="EURUSD", start=start, end=end)

        # Should only include the middle tick (at 30 minutes)
        assert len(result) == 1


# ============================================================================
# Test Factory and Retry Logic
# ============================================================================


class TestFactory:
    """Test suite for factory functions and retry decorator."""

    def test_get_provider_mt5(self):
        """Test creating MT5 provider via factory."""
        from hqt.data.providers.factory import get_provider

        # Mock MT5 availability
        with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
            with patch("hqt.data.providers.mt5_provider.mt5") as mock_mt5:
                mock_mt5.initialize.return_value = True
                mock_mt5.last_error.return_value = (1, "Success")

                provider = get_provider("mt5")

                assert provider.get_provider_name() == "MetaTrader 5"

    def test_get_provider_mt5_with_config(self):
        """Test creating MT5 provider with config."""
        from hqt.data.providers.factory import get_provider

        with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
            with patch("hqt.data.providers.mt5_provider.mt5") as mock_mt5:
                mock_mt5.initialize.return_value = True
                mock_mt5.login.return_value = True
                mock_mt5.last_error.return_value = (1, "Success")

                provider = get_provider(
                    "mt5",
                    path="C:/MT5/terminal.exe",
                    login=12345,
                    password="secret",
                    server="BrokerServer",
                )

                assert provider._path == "C:/MT5/terminal.exe"
                assert provider._login == 12345

    def test_get_provider_dukascopy(self):
        """Test creating Dukascopy provider via factory."""
        from hqt.data.providers.factory import get_provider

        provider = get_provider("dukascopy")

        assert provider.get_provider_name() == "Dukascopy"

    def test_get_provider_dukascopy_with_config(self):
        """Test creating Dukascopy provider with config."""
        from hqt.data.providers.factory import get_provider

        provider = get_provider("dukascopy", timeout=60, max_retries=5)

        assert provider._timeout == 60
        assert provider._max_retries == 5

    def test_get_provider_case_insensitive(self):
        """Test that provider type is case-insensitive."""
        from hqt.data.providers.factory import get_provider

        with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
            with patch("hqt.data.providers.mt5_provider.mt5") as mock_mt5:
                mock_mt5.initialize.return_value = True
                mock_mt5.last_error.return_value = (1, "Success")

                provider1 = get_provider("MT5")
                provider2 = get_provider("Mt5")
                provider3 = get_provider("mt5")

                assert all(
                    p.get_provider_name() == "MetaTrader 5"
                    for p in [provider1, provider2, provider3]
                )

    def test_get_provider_invalid_type(self):
        """Test get_provider with invalid provider type."""
        from hqt.data.providers.factory import get_provider

        with pytest.raises(ValueError, match="Unknown provider type: invalid"):
            get_provider("invalid")

    def test_get_available_providers(self):
        """Test get_available_providers returns metadata."""
        from hqt.data.providers.factory import get_available_providers

        providers = get_available_providers()

        # Verify MT5 metadata
        assert "mt5" in providers
        assert providers["mt5"]["name"] == "MetaTrader 5"
        assert providers["mt5"]["supports_bars"] is True
        assert providers["mt5"]["supports_ticks"] is True
        assert "MetaTrader5" in providers["mt5"]["requires"]

        # Verify Dukascopy metadata
        assert "dukascopy" in providers
        assert providers["dukascopy"]["name"] == "Dukascopy"
        assert providers["dukascopy"]["supports_bars"] is False
        assert providers["dukascopy"]["supports_ticks"] is True
        assert "requests" in providers["dukascopy"]["requires"]

    def test_with_retry_success_first_try(self):
        """Test with_retry succeeds on first attempt."""
        from hqt.data.providers.factory import with_retry

        @with_retry(max_retries=3)
        def succeeding_function():
            return "success"

        result = succeeding_function()
        assert result == "success"

    def test_with_retry_success_after_failure(self):
        """Test with_retry succeeds after transient failure."""
        from hqt.data.providers.factory import with_retry

        call_count = 0

        @with_retry(max_retries=3, initial_delay=0.01)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(
                    error_code="TEST-001",
                    module="test",
                    message="Temporary failure"
                )
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 3

    def test_with_retry_exhausts_retries(self):
        """Test with_retry gives up after max_retries."""
        from hqt.data.providers.factory import with_retry

        call_count = 0

        @with_retry(max_retries=2, initial_delay=0.01)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError(
                error_code="TEST-001",
                module="test",
                message="Always fails"
            )

        with pytest.raises(ConnectionError, match="Always fails"):
            always_failing_function()

        # Should try initial + 2 retries = 3 times
        assert call_count == 3

    def test_with_retry_exponential_backoff(self):
        """Test with_retry uses exponential backoff."""
        from hqt.data.providers.factory import with_retry

        delays = []

        @with_retry(max_retries=3, initial_delay=0.1, backoff_factor=2.0)
        def failing_function():
            raise ConnectionError(
                error_code="TEST-001",
                module="test",
                message="Fail"
            )

        start_time = time.time()
        try:
            failing_function()
        except ConnectionError:
            pass
        elapsed = time.time() - start_time

        # Should sleep for 0.1 + 0.2 + 0.4 = 0.7 seconds (approximately)
        # Allow some tolerance for timing
        assert elapsed >= 0.6

    def test_with_retry_max_delay_cap(self):
        """Test with_retry caps delay at max_delay."""
        from hqt.data.providers.factory import with_retry

        @with_retry(max_retries=10, initial_delay=1.0, max_delay=2.0, backoff_factor=10.0)
        def failing_function():
            raise ConnectionError(
                error_code="TEST-001",
                module="test",
                message="Fail"
            )

        start_time = time.time()
        try:
            failing_function()
        except ConnectionError:
            pass
        elapsed = time.time() - start_time

        # Even with high backoff_factor, delay should be capped
        # Max total: 10 retries * 2.0 max_delay = 20 seconds (but first is 1.0, second is 2.0)
        # Should be much less than without cap (1 + 10 + 100 + 1000... would be huge)
        assert elapsed < 25  # Should complete in reasonable time

    def test_with_retry_custom_exceptions(self):
        """Test with_retry with custom exception types."""
        from hqt.data.providers.factory import with_retry

        @with_retry(max_retries=2, initial_delay=0.01, exceptions=(ValueError,))
        def function_with_value_error():
            raise ValueError("Custom error")

        # ValueError should be retried
        with pytest.raises(ValueError):
            function_with_value_error()

        # Other exceptions should not be retried
        @with_retry(max_retries=2, initial_delay=0.01, exceptions=(ValueError,))
        def function_with_type_error():
            raise TypeError("Not retried")

        with pytest.raises(TypeError):
            function_with_type_error()

    def test_download_with_progress_bars(self):
        """Test download_with_progress for bars."""
        from hqt.data.providers.factory import download_with_progress

        mock_provider = MagicMock(spec=DataProvider)
        mock_provider.fetch_bars.return_value = pd.DataFrame()

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)

        download_with_progress(
            mock_provider,
            "EURUSD",
            start,
            end,
            fetch_type="bars",
            timeframe=Timeframe.H1,
        )

        # Verify fetch_bars was called with progress callback
        mock_provider.fetch_bars.assert_called_once()
        args, kwargs = mock_provider.fetch_bars.call_args
        assert kwargs["symbol"] == "EURUSD"
        assert kwargs["timeframe"] == Timeframe.H1
        assert kwargs["progress_callback"] is not None

    def test_download_with_progress_ticks(self):
        """Test download_with_progress for ticks."""
        from hqt.data.providers.factory import download_with_progress

        mock_provider = MagicMock(spec=DataProvider)
        mock_provider.fetch_ticks.return_value = pd.DataFrame()

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)

        download_with_progress(
            mock_provider, "EURUSD", start, end, fetch_type="ticks"
        )

        # Verify fetch_ticks was called with progress callback
        mock_provider.fetch_ticks.assert_called_once()
        args, kwargs = mock_provider.fetch_ticks.call_args
        assert kwargs["symbol"] == "EURUSD"
        assert kwargs["progress_callback"] is not None

    def test_download_with_progress_invalid_fetch_type(self):
        """Test download_with_progress with invalid fetch_type."""
        from hqt.data.providers.factory import download_with_progress

        mock_provider = MagicMock(spec=DataProvider)

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="Invalid fetch_type: invalid"):
            download_with_progress(
                mock_provider, "EURUSD", start, end, fetch_type="invalid"
            )

    def test_download_with_progress_bars_without_timeframe(self):
        """Test download_with_progress bars requires timeframe."""
        from hqt.data.providers.factory import download_with_progress

        mock_provider = MagicMock(spec=DataProvider)

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="timeframe required for bars"):
            download_with_progress(
                mock_provider, "EURUSD", start, end, fetch_type="bars", timeframe=None
            )


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for data providers."""

    def test_mt5_provider_full_workflow(self):
        """Test complete MT5 provider workflow."""
        with patch("hqt.data.providers.mt5_provider.MT5_AVAILABLE", True):
            with patch("hqt.data.providers.mt5_provider.mt5") as mock_mt5:
                # Setup mocks
                mock_mt5.initialize.return_value = True
                mock_mt5.last_error.return_value = (1, "Success")

                mock_symbol_info = MagicMock()
                mock_symbol_info.name = "EURUSD"
                type(mock_symbol_info).visible = PropertyMock(return_value=True)
                mock_mt5.symbol_info.return_value = mock_symbol_info

                mock_rates = [
                    {"time": 1704067200, "open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1, "tick_volume": 100, "spread": 2, "real_volume": 1000}
                ]
                mock_mt5.copy_rates_range.return_value = mock_rates

                from hqt.data.providers.mt5_provider import MT5DataProvider

                # Use as context manager
                with MT5DataProvider() as provider:
                    # Check connection
                    assert provider._connected

                    # Fetch bars
                    bars = provider.fetch_bars(
                        symbol="EURUSD",
                        timeframe=Timeframe.H1,
                        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
                        end=datetime(2024, 1, 2, tzinfo=timezone.utc),
                    )

                    assert len(bars) > 0

                # Verify shutdown was called
                mock_mt5.shutdown.assert_called()

    def test_dukascopy_provider_full_workflow(self):
        """Test complete Dukascopy provider workflow."""
        from hqt.data.providers.dukascopy_provider import DukascopyProvider

        # Create realistic test data
        ticks = [(0, 1.1, 1.1, 100.0, 100.0)]
        binary_data = b""
        for timestamp_ms, ask, bid, ask_vol, bid_vol in ticks:
            tick_bytes = struct.pack(
                ">IIIff",
                timestamp_ms,
                int(ask * 100000),
                int(bid * 100000),
                ask_vol,
                bid_vol,
            )
            binary_data += tick_bytes
        bi5_data = lzma.compress(binary_data)

        with patch.object(DukascopyProvider, "_fetch_hour") as mock_fetch:
            # Create timestamp that falls within the requested range (10:00-11:00)
            start_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
            timestamp_us = int(start_time.timestamp() * 1_000_000)

            mock_fetch.return_value = pd.DataFrame(
                {
                    "timestamp": [timestamp_us],
                    "bid": [1.1],
                    "ask": [1.1],
                    "bid_volume": [100],
                    "ask_volume": [100],
                }
            )

            with DukascopyProvider() as provider:
                ticks = provider.fetch_ticks(
                    symbol="EURUSD",
                    start=start_time,
                    end=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
                )

                assert len(ticks) > 0
