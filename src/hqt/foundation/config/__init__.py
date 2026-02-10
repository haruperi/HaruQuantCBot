"""
HQT Trading System Configuration Management.

This module provides comprehensive configuration management with:
- Type-safe Pydantic models for all configuration sections
- TOML file loading with environment overlays
- Environment variable and secret resolution
- Configuration validation with cross-field checks
- Hot reload for runtime configuration updates
- Secure secrets management with OS keyring

Quick Start:
    ```python
    from hqt.foundation.config import ConfigManager

    # Load configuration
    manager = ConfigManager(config_dir="config")
    config = manager.load(env="development")

    # Access configuration
    print(f"Buffer size: {config.engine.tick_buffer_size}")
    print(f"Max positions: {config.risk.max_positions}")

    # Hot reload
    manager.reload_hot(["logging.level"])
    ```

Secrets Management:
    ```python
    from hqt.foundation.config import SecretsManager

    secrets = SecretsManager()
    secrets.set("broker.api_key", "sk-secret")
    api_key = secrets.get("broker.api_key")
    ```
"""

# Configuration models
from .models import (
    BrokerConfig,
    BrokerType,
    DataConfig,
    DataProviderType,
    DatabaseConfig,
    EngineConfig,
    LoggingConfig,
    LogLevel,
    NotificationChannel,
    NotificationConfig,
    OptimizationConfig,
    OptimizationMethod,
    PositionSizingMethod,
    RiskConfig,
    UIConfig,
)

# Root schema
from .schema import AppConfig

# Manager and secrets
from .manager import ConfigManager
from .secrets import SecretsManager

__all__ = [
    # Root
    "AppConfig",
    "ConfigManager",
    "SecretsManager",
    # Engine
    "EngineConfig",
    # Data
    "DataConfig",
    "DataProviderType",
    # Broker
    "BrokerConfig",
    "BrokerType",
    # Risk
    "RiskConfig",
    "PositionSizingMethod",
    # Notifications
    "NotificationConfig",
    "NotificationChannel",
    # Logging
    "LoggingConfig",
    "LogLevel",
    # UI
    "UIConfig",
    # Database
    "DatabaseConfig",
    # Optimization
    "OptimizationConfig",
    "OptimizationMethod",
]
