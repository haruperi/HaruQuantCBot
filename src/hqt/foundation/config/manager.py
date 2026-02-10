"""
Configuration manager for the HQT trading system.

This module provides centralized configuration management with TOML loading,
environment overlay, secret resolution, and hot reload capabilities.
"""

import copy
import os
import re
from pathlib import Path
from typing import Any, Callable

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for older Python

from hqt.foundation.exceptions import ConfigError, SchemaError

from .schema import AppConfig
from .secrets import SecretsManager


class ConfigManager:
    """
    Manages application configuration with validation and hot reload.

    Features:
    - Load configuration from TOML files
    - Environment-specific overlays (development, production, testing)
    - Environment variable resolution (${env:VAR})
    - Secret resolution (${secret:key})
    - Configuration freezing to prevent modifications
    - Hot reload for whitelisted keys

    Example:
        ```python
        from hqt.foundation.config import ConfigManager

        # Load configuration
        manager = ConfigManager()
        config = manager.load(env="development")

        # Access configuration
        print(config.engine.tick_buffer_size)
        print(config.risk.max_positions)

        # Hot reload specific keys
        manager.reload_hot(["logging.level", "ui.theme"])
        ```
    """

    # Keys that can be hot-reloaded at runtime
    HOT_RELOAD_WHITELIST = {
        "logging.level",
        "logging.console_level",
        "logging.file_level",
        "ui.theme",
        "ui.chart_update_interval_ms",
        "notifications.enabled",
        "risk.max_positions",
        "risk.max_daily_trades",
    }

    def __init__(
        self,
        config_dir: Path | str = "config",
        secrets_manager: SecretsManager | None = None,
    ) -> None:
        """
        Initialize the configuration manager.

        Args:
            config_dir: Directory containing configuration files
            secrets_manager: SecretsManager instance (created if not provided)
        """
        self.config_dir = Path(config_dir)
        self.secrets = secrets_manager or SecretsManager()
        self.config: AppConfig | None = None
        self._frozen = False
        self._reload_callbacks: list[Callable[[AppConfig], None]] = []

    def load(
        self,
        env: str = "development",
        freeze: bool = True,
    ) -> AppConfig:
        """
        Load and validate configuration.

        Args:
            env: Environment name (development, production, testing)
            freeze: Freeze configuration after loading

        Returns:
            Validated and optionally frozen AppConfig instance

        Raises:
            ConfigError: If configuration files are missing or invalid
            SchemaError: If configuration fails validation

        Example:
            ```python
            config = manager.load(env="production", freeze=True)
            ```
        """
        # Load base configuration
        base_path = self.config_dir / "base.toml"
        if not base_path.exists():
            raise ConfigError(
                error_code="CFG-001",
                module="config.manager",
                message=f"Base configuration file not found: {base_path}",
                config_file=str(base_path),
            )

        try:
            with open(base_path, "rb") as f:
                base_config = tomllib.load(f)
        except Exception as e:
            raise ConfigError(
                error_code="CFG-002",
                module="config.manager",
                message=f"Failed to parse base configuration: {e}",
                config_file=str(base_path),
                error=str(e),
            ) from e

        # Load environment overlay
        env_path = self.config_dir / f"{env}.toml"
        if env_path.exists():
            try:
                with open(env_path, "rb") as f:
                    env_config = tomllib.load(f)
                    base_config = self._deep_merge(base_config, env_config)
            except Exception as e:
                raise ConfigError(
                    error_code="CFG-003",
                    module="config.manager",
                    message=f"Failed to parse environment configuration: {e}",
                    config_file=str(env_path),
                    error=str(e),
                ) from e

        # Resolve environment variables and secrets
        resolved_config = self._resolve_placeholders(base_config)

        # Validate with Pydantic
        try:
            self.config = AppConfig(**resolved_config)
        except Exception as e:
            raise SchemaError(
                error_code="CFG-004",
                module="config.manager",
                message="Configuration validation failed",
                config_file=str(base_path),
                validation_error=str(e),
            ) from e

        # Freeze if requested
        if freeze:
            self.config.freeze()
            self._frozen = True

        return self.config

    def _deep_merge(self, base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
        """
        Deep merge overlay configuration into base.

        Args:
            base: Base configuration dictionary
            overlay: Overlay configuration dictionary

        Returns:
            Merged configuration dictionary
        """
        result = copy.deepcopy(base)

        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _resolve_placeholders(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve environment variable and secret placeholders.

        Supported formats:
        - ${env:VAR_NAME} - Environment variable
        - ${secret:key.name} - Secret from SecretsManager

        Args:
            config: Configuration dictionary with placeholders

        Returns:
            Configuration with resolved placeholders

        Raises:
            ConfigError: If placeholder resolution fails
        """
        def resolve_value(value: Any) -> Any:
            if isinstance(value, str):
                # Resolve environment variables
                env_pattern = r"\$\{env:([A-Z_][A-Z0-9_]*)\}"
                value = re.sub(
                    env_pattern,
                    lambda m: os.environ.get(m.group(1), ""),
                    value,
                )

                # Resolve secrets
                secret_pattern = r"\$\{secret:([a-zA-Z0-9_.]+)\}"
                matches = re.finditer(secret_pattern, value)
                for match in matches:
                    secret_key = match.group(1)
                    secret_value = self.secrets.get(secret_key)
                    if secret_value is None:
                        raise ConfigError(
                            error_code="CFG-005",
                            module="config.manager",
                            message=f"Secret not found: {secret_key}",
                            config_key=secret_key,
                        )
                    value = value.replace(match.group(0), secret_value)

                return value

            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}

            elif isinstance(value, list):
                return [resolve_value(item) for item in value]

            return value

        return resolve_value(config)

    def reload_hot(self, keys: list[str] | None = None) -> None:
        """
        Hot reload whitelisted configuration keys.

        Args:
            keys: Specific keys to reload (None = reload all whitelisted keys)

        Raises:
            ConfigError: If config not loaded or frozen
            ValueError: If keys contain non-whitelisted values

        Example:
            ```python
            # Reload specific keys
            manager.reload_hot(["logging.level"])

            # Reload all whitelisted keys
            manager.reload_hot()
            ```
        """
        if self.config is None:
            raise ConfigError(
                error_code="CFG-006",
                module="config.manager",
                message="Configuration not loaded. Call load() first.",
            )

        if self._frozen:
            raise ConfigError(
                error_code="CFG-007",
                module="config.manager",
                message="Cannot hot reload frozen configuration",
            )

        # Validate keys
        if keys is None:
            keys = list(self.HOT_RELOAD_WHITELIST)
        else:
            invalid_keys = set(keys) - self.HOT_RELOAD_WHITELIST
            if invalid_keys:
                raise ValueError(f"Keys not whitelisted for hot reload: {invalid_keys}")

        # Reload configuration
        env = os.environ.get("HQT_ENV", "development")
        new_config = self.load(env=env, freeze=False)

        # Update only whitelisted keys
        for key in keys:
            parts = key.split(".")
            if len(parts) != 2:
                continue

            section, field = parts
            if hasattr(new_config, section) and hasattr(getattr(new_config, section), field):
                old_value = getattr(getattr(self.config, section), field)
                new_value = getattr(getattr(new_config, section), field)

                if old_value != new_value:
                    setattr(getattr(self.config, section), field, new_value)

        # Notify callbacks
        for callback in self._reload_callbacks:
            callback(self.config)

    def register_reload_callback(self, callback: Callable[[AppConfig], None]) -> None:
        """
        Register a callback for configuration reload events.

        Args:
            callback: Function to call when configuration is reloaded

        Example:
            ```python
            def on_config_reload(config: AppConfig):
                print(f"Config reloaded: {config.logging.level}")

            manager.register_reload_callback(on_config_reload)
            ```
        """
        self._reload_callbacks.append(callback)

    def unregister_reload_callback(self, callback: Callable[[AppConfig], None]) -> None:
        """
        Unregister a reload callback.

        Args:
            callback: Callback function to remove
        """
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)

    def get_config(self) -> AppConfig:
        """
        Get the current configuration.

        Returns:
            Current AppConfig instance

        Raises:
            ConfigError: If configuration not loaded

        Example:
            ```python
            config = manager.get_config()
            print(config.engine.tick_buffer_size)
            ```
        """
        if self.config is None:
            raise ConfigError(
                error_code="CFG-008",
                module="config.manager",
                message="Configuration not loaded. Call load() first.",
            )
        return self.config

    def is_frozen(self) -> bool:
        """
        Check if configuration is frozen.

        Returns:
            True if frozen, False otherwise
        """
        return self._frozen
