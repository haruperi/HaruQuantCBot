"""
Comprehensive tests for the HQT configuration system.

Tests cover Pydantic models, schema validation, secrets management,
config loading, merging, and hot reload.
"""

import os
import tempfile
from pathlib import Path

import pytest

from hqt.foundation.config import (
    AppConfig,
    BrokerConfig,
    ConfigManager,
    DataConfig,
    EngineConfig,
    RiskConfig,
    SecretsManager,
)
from hqt.foundation.exceptions import ConfigError, SchemaError, SecretError


class TestConfigModels:
    """Tests for Pydantic configuration models."""

    def test_engine_config_defaults(self):
        """Test EngineConfig with default values."""
        config = EngineConfig()

        assert config.tick_buffer_size == 100000
        assert config.event_queue_size == 10000
        assert config.worker_threads == 4
        assert config.enable_wal is True

    def test_engine_config_validation(self):
        """Test EngineConfig validation."""
        # Valid configuration
        config = EngineConfig(tick_buffer_size=50000, worker_threads=8)
        assert config.tick_buffer_size == 50000

        # Invalid: buffer size too large
        with pytest.raises(ValueError):
            EngineConfig(tick_buffer_size=2000000)

        # Invalid: worker threads too high
        with pytest.raises(ValueError):
            EngineConfig(worker_threads=100)

    def test_data_config_defaults(self):
        """Test DataConfig with default values."""
        config = DataConfig()

        assert config.storage_format == "parquet"
        assert config.compression == "snappy"
        assert config.validation_enabled is True

    def test_data_config_validation(self):
        """Test DataConfig validation."""
        # Valid configuration
        config = DataConfig(storage_format="hdf5", compression="gzip")
        assert config.storage_format == "hdf5"

        # Invalid storage format
        with pytest.raises(ValueError):
            DataConfig(storage_format="invalid")

        # Invalid compression
        with pytest.raises(ValueError):
            DataConfig(compression="invalid")

    def test_broker_config_defaults(self):
        """Test BrokerConfig with default values."""
        config = BrokerConfig()

        assert config.zmq_tick_port == 5555
        assert config.zmq_command_port == 5556
        assert config.connection_timeout_seconds == 30

    def test_risk_config_defaults(self):
        """Test RiskConfig with default values."""
        config = RiskConfig()

        assert config.risk_per_trade_percent == 1.0
        assert config.max_positions == 10
        assert config.max_daily_loss_percent == 5.0
        assert config.enable_circuit_breaker is True


class TestAppConfig:
    """Tests for the root AppConfig schema."""

    def test_app_config_defaults(self):
        """Test AppConfig with all default values."""
        config = AppConfig()

        assert isinstance(config.engine, EngineConfig)
        assert isinstance(config.data, DataConfig)
        assert isinstance(config.broker, BrokerConfig)
        assert isinstance(config.risk, RiskConfig)

    def test_app_config_partial_override(self):
        """Test AppConfig with partial section overrides."""
        config = AppConfig(
            engine=EngineConfig(tick_buffer_size=50000),
            risk=RiskConfig(max_positions=5),
        )

        assert config.engine.tick_buffer_size == 50000
        assert config.risk.max_positions == 5
        assert config.data.storage_format == "parquet"  # Default

    def test_zmq_ports_validation(self):
        """Test that ZMQ ports must be different."""
        with pytest.raises(ValueError, match="ZMQ tick and command ports must be different"):
            AppConfig(
                broker=BrokerConfig(zmq_tick_port=5555, zmq_command_port=5555)
            )

    def test_circuit_breaker_validation(self):
        """Test circuit breaker threshold validation."""
        with pytest.raises(ValueError, match="Circuit breaker threshold"):
            AppConfig(
                risk=RiskConfig(
                    circuit_breaker_threshold_percent=10.0,
                    max_daily_loss_percent=5.0,
                )
            )

    def test_config_freeze(self):
        """Test configuration freezing."""
        config = AppConfig()

        # Before freeze - can modify
        config.engine.tick_buffer_size = 50000
        assert config.engine.tick_buffer_size == 50000

        # After freeze - cannot modify
        config.freeze()
        assert config.is_frozen()

        with pytest.raises(Exception):  # Pydantic validation error
            config.engine.tick_buffer_size = 25000

    def test_config_to_dict(self):
        """Test configuration serialization to dictionary."""
        config = AppConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "engine" in config_dict
        assert "data" in config_dict
        assert config_dict["engine"]["tick_buffer_size"] == 100000


class TestSecretsManager:
    """Tests for secrets management."""

    def test_secrets_manager_initialization(self, tmp_path):
        """Test SecretsManager initialization."""
        secrets = SecretsManager(
            service_name="test_hqt",
            encrypted_file=tmp_path / "secrets.enc",
        )

        assert secrets.service_name == "test_hqt"
        assert secrets.encrypted_file == tmp_path / "secrets.enc"
        # File backend is active when keyring is not available
        assert secrets.get_backend() in ("keyring", "encrypted_file")

    def test_set_and_get_secret(self, tmp_path):
        """Test storing and retrieving secrets."""
        secrets = SecretsManager(
            service_name="test_hqt",
            encrypted_file=tmp_path / "secrets.enc",
        )

        # Store secret
        secrets.set("test.key", "secret_value")

        # Retrieve secret
        value = secrets.get("test.key")
        assert value == "secret_value"

    def test_get_nonexistent_secret(self, tmp_path):
        """Test retrieving non-existent secret returns None."""
        secrets = SecretsManager(
            service_name="test_hqt",
            encrypted_file=tmp_path / "secrets.enc",
        )

        value = secrets.get("nonexistent.key")
        assert value is None

    def test_get_secret_with_default(self, tmp_path):
        """Test retrieving non-existent secret with default."""
        secrets = SecretsManager(
            service_name="test_hqt",
            encrypted_file=tmp_path / "secrets.enc",
        )

        value = secrets.get("nonexistent.key", default="default_value")
        assert value == "default_value"

    def test_delete_secret(self, tmp_path):
        """Test deleting secrets."""
        secrets = SecretsManager(
            service_name="test_hqt",
            encrypted_file=tmp_path / "secrets.enc",
        )

        # Store and verify
        secrets.set("test.key", "secret_value")
        assert secrets.get("test.key") == "secret_value"

        # Delete and verify
        secrets.delete("test.key")
        assert secrets.get("test.key") is None

    def test_list_keys_file_backend(self, tmp_path):
        """Test listing secret keys (file backend only)."""
        secrets = SecretsManager(
            service_name="test_hqt",
            encrypted_file=tmp_path / "secrets.enc",
        )

        # Only test if using file backend
        if secrets.get_backend() == "encrypted_file":
            secrets.set("key1", "value1")
            secrets.set("key2", "value2")

            keys = secrets.list_keys()
            assert "key1" in keys
            assert "key2" in keys


class TestConfigManager:
    """Tests for configuration manager."""

    @pytest.fixture
    def config_dir(self, tmp_path):
        """Create temporary config directory with test files."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create base.toml
        base_toml = """
[engine]
tick_buffer_size = 100000
worker_threads = 4

[data]
storage_format = "parquet"
compression = "snappy"

[risk]
max_positions = 10
risk_per_trade_percent = 1.0
"""
        (config_dir / "base.toml").write_text(base_toml)

        # Create development.toml
        dev_toml = """
[engine]
worker_threads = 2

[risk]
max_positions = 5
"""
        (config_dir / "development.toml").write_text(dev_toml)

        return config_dir

    def test_config_manager_load_base(self, config_dir):
        """Test loading base configuration."""
        manager = ConfigManager(config_dir=config_dir)
        config = manager.load(env="production", freeze=False)

        assert config.engine.tick_buffer_size == 100000
        assert config.engine.worker_threads == 4

    def test_config_manager_load_with_overlay(self, config_dir):
        """Test loading with environment overlay."""
        manager = ConfigManager(config_dir=config_dir)
        config = manager.load(env="development", freeze=False)

        # Base value
        assert config.engine.tick_buffer_size == 100000

        # Overlaid value
        assert config.engine.worker_threads == 2
        assert config.risk.max_positions == 5

    def test_config_manager_missing_base_file(self, tmp_path):
        """Test error when base.toml is missing."""
        manager = ConfigManager(config_dir=tmp_path)

        with pytest.raises(ConfigError, match="Base configuration file not found"):
            manager.load()

    def test_config_manager_freeze(self, config_dir):
        """Test configuration freezing."""
        manager = ConfigManager(config_dir=config_dir)
        config = manager.load(env="development", freeze=True)

        assert manager.is_frozen()
        assert config.is_frozen()

    def test_config_manager_env_variable_resolution(self, config_dir, monkeypatch):
        """Test environment variable resolution."""
        # Set environment variable
        monkeypatch.setenv("TEST_BUFFER_SIZE", "50000")

        # Create config with env variable placeholder
        config_toml = """
[engine]
tick_buffer_size = "${env:TEST_BUFFER_SIZE}"
worker_threads = 4
"""
        (config_dir / "base.toml").write_text(config_toml)

        manager = ConfigManager(config_dir=config_dir)
        config = manager.load(freeze=False)

        # Environment variable should be resolved
        assert config.engine.tick_buffer_size == 50000

    def test_config_manager_secret_resolution(self, config_dir, tmp_path):
        """Test secret resolution."""
        # Create secrets manager and store secret
        secrets = SecretsManager(
            service_name="test_hqt",
            encrypted_file=tmp_path / "secrets.enc",
        )
        secrets.set("broker.port", "5555")

        # Create config with secret placeholder
        config_toml = """
[engine]
tick_buffer_size = 100000

[broker]
zmq_tick_port = "${secret:broker.port}"
zmq_command_port = 5556
"""
        (config_dir / "base.toml").write_text(config_toml)

        manager = ConfigManager(config_dir=config_dir, secrets_manager=secrets)
        config = manager.load(freeze=False)

        # Secret should be resolved
        assert config.broker.zmq_tick_port == 5555

    def test_config_manager_hot_reload(self, config_dir):
        """Test hot reloading of whitelisted keys."""
        manager = ConfigManager(config_dir=config_dir)
        config = manager.load(env="development", freeze=False)

        original_level = config.logging.level

        # Modify config file
        dev_toml = """
[logging]
level = "DEBUG"
"""
        (config_dir / "development.toml").write_text(dev_toml)

        # Hot reload
        manager.reload_hot(["logging.level"])

        # Value should be updated
        assert manager.get_config().logging.level != original_level

    def test_config_manager_hot_reload_invalid_key(self, config_dir):
        """Test hot reload rejects non-whitelisted keys."""
        manager = ConfigManager(config_dir=config_dir)
        manager.load(env="development", freeze=False)

        with pytest.raises(ValueError, match="not whitelisted"):
            manager.reload_hot(["engine.tick_buffer_size"])

    def test_config_manager_reload_callback(self, config_dir):
        """Test reload callback notification."""
        manager = ConfigManager(config_dir=config_dir)
        manager.load(env="development", freeze=False)

        callback_called = False

        def on_reload(config):
            nonlocal callback_called
            callback_called = True

        manager.register_reload_callback(on_reload)
        manager.reload_hot([])

        assert callback_called


class TestConfigIntegration:
    """Integration tests for the configuration system."""

    def test_full_config_lifecycle(self, tmp_path):
        """Test complete configuration lifecycle."""
        # Create config directory
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create configuration file
        config_toml = """
[engine]
tick_buffer_size = 100000
worker_threads = 4

[data]
storage_format = "parquet"

[risk]
max_positions = 10
risk_per_trade_percent = 1.0

[logging]
level = "INFO"
"""
        (config_dir / "base.toml").write_text(config_toml)

        # Initialize manager
        manager = ConfigManager(config_dir=config_dir)

        # Load configuration
        config = manager.load(env="production", freeze=True)

        # Verify configuration
        assert config.engine.tick_buffer_size == 100000
        assert config.data.storage_format == "parquet"
        assert config.risk.max_positions == 10

        # Verify frozen
        assert manager.is_frozen()
