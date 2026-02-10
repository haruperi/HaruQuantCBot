"""
Comprehensive tests for the HQT exception hierarchy.

Tests cover instantiation, inheritance, serialization, and string
representation for all exception classes.
"""

from datetime import datetime, timezone

import pytest

from hqt.foundation.exceptions import (
    BridgeError,
    BrokerError,
    ConfigError,
    ConnectionError,
    DataError,
    DuplicateError,
    EngineError,
    GapError,
    HQTBaseError,
    MarginError,
    OrderError,
    PriceSanityError,
    ReconnectError,
    SchemaError,
    SecretError,
    StopOutError,
    TimeoutError,
    TradingError,
    ValidationError,
)


class TestHQTBaseError:
    """Tests for the base exception class."""

    def test_instantiation(self):
        """Test basic exception instantiation."""
        error = HQTBaseError(
            error_code="TEST-001",
            module="test.module",
            message="Test error message",
        )

        assert error.error_code == "TEST-001"
        assert error.module == "test.module"
        assert error.message == "Test error message"
        assert isinstance(error.timestamp, datetime)
        assert error.timestamp.tzinfo == timezone.utc
        assert error.context == {}

    def test_instantiation_with_context(self):
        """Test exception instantiation with additional context."""
        error = HQTBaseError(
            error_code="TEST-002",
            module="test.module",
            message="Test error",
            custom_field="custom_value",
            numeric_field=42,
        )

        assert error.context["custom_field"] == "custom_value"
        assert error.context["numeric_field"] == 42

    def test_to_dict(self):
        """Test exception serialization to dictionary."""
        error = HQTBaseError(
            error_code="TEST-003",
            module="test.module",
            message="Test error",
            extra_data="test",
        )

        error_dict = error.to_dict()

        assert error_dict["error_code"] == "TEST-003"
        assert error_dict["module"] == "test.module"
        assert error_dict["message"] == "Test error"
        assert "timestamp" in error_dict
        assert error_dict["extra_data"] == "test"
        assert isinstance(error_dict["timestamp"], str)  # ISO format

    def test_str_representation(self):
        """Test string representation of exception."""
        error = HQTBaseError(
            error_code="TEST-004",
            module="test.module",
            message="Test error message",
        )

        assert str(error) == "[test.module] TEST-004: Test error message"

    def test_repr_representation(self):
        """Test detailed representation of exception."""
        error = HQTBaseError(
            error_code="TEST-005",
            module="test.module",
            message="Test error",
        )

        repr_str = repr(error)
        assert "HQTBaseError" in repr_str
        assert "TEST-005" in repr_str
        assert "test.module" in repr_str

    def test_repr_with_context(self):
        """Test repr includes context fields."""
        error = HQTBaseError(
            error_code="TEST-006",
            module="test.module",
            message="Test error",
            field1="value1",
            field2=123,
        )

        repr_str = repr(error)
        assert "field1='value1'" in repr_str
        assert "field2=123" in repr_str

    def test_inheritance(self):
        """Test that HQTBaseError is an Exception."""
        error = HQTBaseError(
            error_code="TEST-007",
            module="test",
            message="Test",
        )

        assert isinstance(error, Exception)
        assert isinstance(error, HQTBaseError)


class TestDataExceptions:
    """Tests for data-related exceptions."""

    def test_data_error_inheritance(self):
        """Test DataError inherits from HQTBaseError."""
        error = DataError(
            error_code="DAT-001",
            module="data",
            message="Data error",
        )

        assert isinstance(error, HQTBaseError)
        assert isinstance(error, DataError)

    def test_validation_error(self):
        """Test ValidationError with field context."""
        error = ValidationError(
            error_code="DAT-002",
            module="data.validation",
            message="Invalid value",
            field="price",
            value=-100.0,
            constraint="price > 0",
        )

        assert isinstance(error, DataError)
        assert error.context["field"] == "price"
        assert error.context["value"] == -100.0
        assert error.context["constraint"] == "price > 0"

    def test_price_sanity_error(self):
        """Test PriceSanityError with price context."""
        error = PriceSanityError(
            error_code="DAT-003",
            module="data.validation",
            message="Bid > Ask",
            symbol="EURUSD",
            price=1.1000,
            bid=1.1000,
            ask=1.0900,
        )

        assert isinstance(error, DataError)
        assert error.context["symbol"] == "EURUSD"
        assert error.context["price"] == 1.1000

    def test_gap_error(self):
        """Test GapError with gap context."""
        error = GapError(
            error_code="DAT-004",
            module="data.pipeline",
            message="Missing data",
            symbol="EURUSD",
            gap_size=3600,
        )

        assert isinstance(error, DataError)
        assert error.context["symbol"] == "EURUSD"
        assert error.context["gap_size"] == 3600

    def test_duplicate_error(self):
        """Test DuplicateError with duplicate context."""
        error = DuplicateError(
            error_code="DAT-005",
            module="data.storage",
            message="Duplicate detected",
            key="2024-01-01T10:00:00Z",
            duplicate_count=3,
        )

        assert isinstance(error, DataError)
        assert error.context["key"] == "2024-01-01T10:00:00Z"
        assert error.context["duplicate_count"] == 3


class TestTradingExceptions:
    """Tests for trading-related exceptions."""

    def test_trading_error_inheritance(self):
        """Test TradingError inherits from HQTBaseError."""
        error = TradingError(
            error_code="TRD-001",
            module="trading",
            message="Trading error",
        )

        assert isinstance(error, HQTBaseError)
        assert isinstance(error, TradingError)

    def test_order_error(self):
        """Test OrderError with order context."""
        error = OrderError(
            error_code="TRD-002",
            module="trading.orders",
            message="Invalid order",
            order_id="ORD-12345",
            symbol="EURUSD",
            volume=1.0,
        )

        assert isinstance(error, TradingError)
        assert error.context["order_id"] == "ORD-12345"
        assert error.context["symbol"] == "EURUSD"

    def test_margin_error(self):
        """Test MarginError with margin context."""
        error = MarginError(
            error_code="TRD-003",
            module="trading.margin",
            message="Insufficient margin",
            required_margin=1000.0,
            available_margin=500.0,
        )

        assert isinstance(error, TradingError)
        assert error.context["required_margin"] == 1000.0
        assert error.context["available_margin"] == 500.0

    def test_stop_out_error(self):
        """Test StopOutError with stop-out context."""
        error = StopOutError(
            error_code="TRD-004",
            module="trading.margin",
            message="Stop-out triggered",
            margin_level=15.0,
            stop_out_level=20.0,
        )

        assert isinstance(error, TradingError)
        assert error.context["margin_level"] == 15.0
        assert error.context["stop_out_level"] == 20.0


class TestBrokerExceptions:
    """Tests for broker-related exceptions."""

    def test_broker_error_inheritance(self):
        """Test BrokerError inherits from HQTBaseError."""
        error = BrokerError(
            error_code="BRK-001",
            module="broker",
            message="Broker error",
        )

        assert isinstance(error, HQTBaseError)
        assert isinstance(error, BrokerError)

    def test_connection_error(self):
        """Test ConnectionError with connection context."""
        error = ConnectionError(
            error_code="BRK-002",
            module="broker.gateway",
            message="Connection failed",
            broker="MT5",
            endpoint="localhost:5555",
        )

        assert isinstance(error, BrokerError)
        assert error.context["broker"] == "MT5"
        assert error.context["endpoint"] == "localhost:5555"

    def test_timeout_error(self):
        """Test TimeoutError with timeout context."""
        error = TimeoutError(
            error_code="BRK-003",
            module="broker.gateway",
            message="Operation timed out",
            operation="place_order",
            timeout_seconds=30.0,
        )

        assert isinstance(error, BrokerError)
        assert error.context["operation"] == "place_order"
        assert error.context["timeout_seconds"] == 30.0

    def test_reconnect_error(self):
        """Test ReconnectError with reconnection context."""
        error = ReconnectError(
            error_code="BRK-004",
            module="broker.gateway",
            message="Reconnection failed",
            broker="MT5",
            attempts=5,
        )

        assert isinstance(error, BrokerError)
        assert error.context["broker"] == "MT5"
        assert error.context["attempts"] == 5


class TestEngineExceptions:
    """Tests for engine-related exceptions."""

    def test_engine_error(self):
        """Test EngineError with engine context."""
        error = EngineError(
            error_code="ENG-001",
            module="engine.core",
            message="Engine failed",
            engine_state="running",
        )

        assert isinstance(error, HQTBaseError)
        assert error.context["engine_state"] == "running"

    def test_bridge_error(self):
        """Test BridgeError with bridge context."""
        error = BridgeError(
            error_code="BRG-001",
            module="bridge.types",
            message="Conversion failed",
            bridge_operation="convert_bar",
        )

        assert isinstance(error, HQTBaseError)
        assert error.context["bridge_operation"] == "convert_bar"


class TestConfigExceptions:
    """Tests for configuration-related exceptions."""

    def test_config_error_inheritance(self):
        """Test ConfigError inherits from HQTBaseError."""
        error = ConfigError(
            error_code="CFG-001",
            module="config",
            message="Config error",
            config_file="config/base.toml",
        )

        assert isinstance(error, HQTBaseError)
        assert isinstance(error, ConfigError)
        assert error.context["config_file"] == "config/base.toml"

    def test_schema_error(self):
        """Test SchemaError with schema context."""
        error = SchemaError(
            error_code="CFG-002",
            module="config.schema",
            message="Schema validation failed",
            config_file="config/base.toml",
            schema_field="engine.buffer_size",
            expected_type="int",
        )

        assert isinstance(error, ConfigError)
        assert error.context["schema_field"] == "engine.buffer_size"
        assert error.context["expected_type"] == "int"

    def test_secret_error(self):
        """Test SecretError with secret context."""
        error = SecretError(
            error_code="CFG-003",
            module="config.secrets",
            message="Secret retrieval failed",
            config_file=None,
            secret_key="api.key",
            operation="get",
        )

        assert isinstance(error, ConfigError)
        assert error.context["secret_key"] == "api.key"
        assert error.context["operation"] == "get"


class TestExceptionHierarchy:
    """Tests for the overall exception hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all exceptions inherit from HQTBaseError."""
        exceptions = [
            DataError,
            ValidationError,
            PriceSanityError,
            GapError,
            DuplicateError,
            TradingError,
            OrderError,
            MarginError,
            StopOutError,
            BrokerError,
            ConnectionError,
            TimeoutError,
            ReconnectError,
            EngineError,
            BridgeError,
            ConfigError,
            SchemaError,
            SecretError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, HQTBaseError)

    def test_exception_catching(self):
        """Test that exceptions can be caught by their parent classes."""
        # Raise ValidationError, catch as DataError
        with pytest.raises(DataError):
            raise ValidationError(
                error_code="DAT-999",
                module="test",
                message="Test",
            )

        # Raise SchemaError, catch as ConfigError
        with pytest.raises(ConfigError):
            raise SchemaError(
                error_code="CFG-999",
                module="test",
                message="Test",
            )

        # Raise any exception, catch as HQTBaseError
        with pytest.raises(HQTBaseError):
            raise OrderError(
                error_code="TRD-999",
                module="test",
                message="Test",
            )
