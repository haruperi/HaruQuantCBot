"""
Configuration-related exception classes for the HQT trading system.

This module provides exceptions for configuration management,
validation, and secrets handling.
"""

from typing import Any

from .base import HQTBaseError


class ConfigError(HQTBaseError):
    """
    Base class for all configuration-related errors.

    This exception covers configuration loading, parsing,
    validation, and access errors.

    Additional Context Fields:
        config_file: Configuration file path
        config_key: Specific configuration key
        config_section: Configuration section

    Example:
        ```python
        raise ConfigError(
            error_code="CFG-001",
            module="config.manager",
            message="Failed to load configuration file",
            config_file="config/production.toml"
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        config_file: str | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            config_file=config_file,
            **context,
        )


class SchemaError(ConfigError):
    """
    Raised when configuration fails schema validation.

    This exception indicates that configuration data does not
    conform to the expected schema or contains invalid values.

    Additional Context Fields:
        schema_field: Field that failed validation
        expected_type: Expected data type
        actual_type: Actual data type
        constraint: Constraint that was violated
        validation_error: Underlying validation error message

    Example:
        ```python
        raise SchemaError(
            error_code="CFG-002",
            module="config.schema",
            message="Invalid configuration value",
            config_file="config/base.toml",
            schema_field="engine.tick_buffer_size",
            expected_type="int",
            actual_type="str",
            constraint="must be positive integer"
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        schema_field: str | None = None,
        expected_type: str | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            schema_field=schema_field,
            expected_type=expected_type,
            **context,
        )


class SecretError(ConfigError):
    """
    Raised when secrets management operations fail.

    This exception indicates errors in retrieving, storing,
    or decrypting secrets from the secrets manager.

    Additional Context Fields:
        secret_key: The secret key being accessed
        operation: The operation that failed (get, set, delete)
        backend: Secrets backend (keyring, encrypted_file)
        keyring_service: OS keyring service name

    Example:
        ```python
        raise SecretError(
            error_code="CFG-003",
            module="config.secrets",
            message="Failed to retrieve API key from keyring",
            secret_key="broker.api_key",
            operation="get",
            backend="keyring",
            keyring_service="hqt_trading"
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        secret_key: str | None = None,
        operation: str | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            secret_key=secret_key,
            operation=operation,
            **context,
        )
