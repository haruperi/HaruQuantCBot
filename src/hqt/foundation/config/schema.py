"""
Root configuration schema for the HQT trading system.

This module defines the AppConfig root model that aggregates all
configuration sections with cross-field validation.
"""

from typing import Any
import types

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .models import (
    BrokerConfig,
    DataConfig,
    DatabaseConfig,
    EngineConfig,
    LoggingConfig,
    NotificationConfig,
    OptimizationConfig,
    RiskConfig,
    UIConfig,
)


class AppConfig(BaseModel):
    """
    Root configuration model for the HQT trading system.

    Aggregates all configuration sections and provides cross-field validation
    to ensure consistency across components.

    Example:
        ```python
        from hqt.foundation.config import AppConfig

        config = AppConfig(
            engine=EngineConfig(tick_buffer_size=50000),
            data=DataConfig(storage_format="parquet"),
            # ... other sections
        )
        ```
    """

    _is_frozen: bool = False

    engine: EngineConfig = EngineConfig()
    """C++ core engine configuration"""

    data: DataConfig = DataConfig()
    """Data management and storage configuration"""

    broker: BrokerConfig = BrokerConfig()
    """Broker connectivity configuration"""

    risk: RiskConfig = RiskConfig()
    """Risk management configuration"""

    notifications: NotificationConfig = NotificationConfig()
    """Notification system configuration"""

    logging: LoggingConfig = LoggingConfig()
    """Logging system configuration"""

    ui: UIConfig = UIConfig()
    """Desktop UI configuration"""

    database: DatabaseConfig = DatabaseConfig()
    """Database connectivity configuration"""

    optimization: OptimizationConfig = OptimizationConfig()
    """Parameter optimization configuration"""

    model_config = ConfigDict(
        frozen=False,  # Will be frozen after validation
        validate_assignment=True,
        extra="forbid",  # Reject unknown fields
    )

    @model_validator(mode="after")
    def validate_zmq_ports(self) -> "AppConfig":
        """Validate that ZMQ ports are different."""
        if self.broker.zmq_tick_port == self.broker.zmq_command_port:
            raise ValueError("ZMQ tick and command ports must be different")
        return self

    @model_validator(mode="after")
    def validate_optimization_workers(self) -> "AppConfig":
        """Validate optimization workers don't exceed engine threads."""
        if self.optimization.max_parallel_workers > self.engine.worker_threads * 2:
            raise ValueError(
                f"Optimization workers ({self.optimization.max_parallel_workers}) "
                f"should not exceed 2x engine threads ({self.engine.worker_threads})"
            )
        return self

    @model_validator(mode="after")
    def validate_risk_circuit_breaker(self) -> "AppConfig":
        """Validate circuit breaker threshold is less than daily loss limit."""
        if self.risk.enable_circuit_breaker:
            if self.risk.circuit_breaker_threshold_percent >= self.risk.max_daily_loss_percent:
                raise ValueError(
                    f"Circuit breaker threshold ({self.risk.circuit_breaker_threshold_percent}%) "
                    f"must be less than daily loss limit ({self.risk.max_daily_loss_percent}%)"
                )
        return self

    @model_validator(mode="after")
    def validate_notification_config(self) -> "AppConfig":
        """Validate notification channel configuration."""
        if self.notifications.enabled:
            from .models import NotificationChannel

            if NotificationChannel.TELEGRAM in self.notifications.channels:
                if not self.notifications.telegram_bot_token or not self.notifications.telegram_chat_id:
                    raise ValueError("Telegram bot token and chat ID required when Telegram channel is enabled")

            if NotificationChannel.EMAIL in self.notifications.channels:
                if not self.notifications.email_smtp_host or not self.notifications.email_to:
                    raise ValueError("Email SMTP host and recipients required when Email channel is enabled")

        return self

    @model_validator(mode="after")
    def validate_broker_mt5_config(self) -> "AppConfig":
        """Validate MT5 broker configuration."""
        from .models import BrokerType

        if self.broker.broker_type == BrokerType.MT5:
            if not self.broker.mt5_login or not self.broker.mt5_server:
                raise ValueError("MT5 login and server required when using MT5 broker")

        return self

    def freeze(self) -> None:
        """
        Freeze the configuration to prevent further modifications.

        After calling this method, any attempt to modify the configuration
        will raise an error.

        Example:
            ```python
            config = AppConfig()
            config.freeze()
            config.engine.tick_buffer_size = 1000  # Raises error
            ```

        Note:
            This creates frozen copies of all configuration sections.
        """
        # Import the config classes
        from .models import (
            EngineConfig, DataConfig, BrokerConfig, RiskConfig,
            NotificationConfig, LoggingConfig, UIConfig,
            DatabaseConfig, OptimizationConfig
        )

        # Create frozen version of each config class
        config_classes = {
            'engine': EngineConfig,
            'data': DataConfig,
            'broker': BrokerConfig,
            'risk': RiskConfig,
            'notifications': NotificationConfig,
            'logging': LoggingConfig,
            'ui': UIConfig,
            'database': DatabaseConfig,
            'optimization': OptimizationConfig,
        }

        # Replace each section with a frozen copy
        for attr_name, config_class in config_classes.items():
            section = getattr(self, attr_name)

            # Create a frozen subclass
            class FrozenConfig(config_class):  # type: ignore
                model_config = ConfigDict(frozen=True, validate_assignment=True)

            # Create frozen instance
            frozen_section = FrozenConfig(**section.model_dump())
            object.__setattr__(self, attr_name, frozen_section)

        # Mark as frozen
        object.__setattr__(self, '_is_frozen', True)

    def is_frozen(self) -> bool:
        """
        Check if the configuration is frozen.

        Returns:
            True if configuration is frozen, False otherwise
        """
        return getattr(self, '_is_frozen', False)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of the configuration

        Example:
            ```python
            config = AppConfig()
            config_dict = config.to_dict()
            ```
        """
        return self.model_dump()

    def to_toml_dict(self) -> dict[str, Any]:
        """
        Convert configuration to TOML-compatible dictionary.

        Returns:
            Dictionary suitable for TOML serialization

        Example:
            ```python
            import tomli_w

            config = AppConfig()
            toml_dict = config.to_toml_dict()

            with open("config.toml", "wb") as f:
                tomli_w.dump(toml_dict, f)
            ```
        """
        config_dict = self.model_dump()

        # Convert Path objects to strings
        def convert_paths(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_paths(item) for item in obj]
            elif hasattr(obj, "__fspath__"):  # Path object
                return str(obj)
            return obj

        return convert_paths(config_dict)
