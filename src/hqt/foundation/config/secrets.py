"""
Secrets management for the HQT trading system.

This module provides secure storage and retrieval of sensitive configuration
values using OS keyring and encrypted file fallback.
"""

import json
from pathlib import Path
from typing import Any

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

from cryptography.fernet import Fernet

from hqt.foundation.exceptions import SecretError


class SecretsManager:
    """
    Manages secure storage and retrieval of secrets.

    Uses OS keyring as primary storage with encrypted file as fallback.
    Secrets are never stored in plaintext configuration files.

    Example:
        ```python
        from hqt.foundation.config import SecretsManager

        secrets = SecretsManager(service_name="hqt_trading")

        # Store a secret
        secrets.set("broker.api_key", "sk-1234567890")

        # Retrieve a secret
        api_key = secrets.get("broker.api_key")

        # Delete a secret
        secrets.delete("broker.api_key")
        ```
    """

    def __init__(
        self,
        service_name: str = "hqt_trading",
        encrypted_file: Path | None = None,
        encryption_key: bytes | None = None,
    ) -> None:
        """
        Initialize the secrets manager.

        Args:
            service_name: Service name for OS keyring
            encrypted_file: Path to encrypted secrets file (fallback)
            encryption_key: Encryption key for file (generated if not provided)

        Note:
            If OS keyring is unavailable, falls back to encrypted file storage.
        """
        self.service_name = service_name
        self.use_keyring = KEYRING_AVAILABLE

        # Encrypted file fallback
        if encrypted_file is None:
            encrypted_file = Path.home() / ".hqt" / "secrets.enc"

        self.encrypted_file = Path(encrypted_file)
        self.encrypted_file.parent.mkdir(parents=True, exist_ok=True)

        # Encryption key
        if encryption_key is None:
            encryption_key = self._load_or_generate_key()

        self.cipher = Fernet(encryption_key)

        # In-memory cache for encrypted file backend
        self._file_secrets: dict[str, str] = {}
        if not self.use_keyring:
            self._load_file_secrets()

    def _load_or_generate_key(self) -> bytes:
        """
        Load or generate encryption key.

        Returns:
            Encryption key bytes

        Note:
            Key is stored in .hqt/secrets.key in user's home directory.
        """
        key_file = Path.home() / ".hqt" / "secrets.key"
        key_file.parent.mkdir(parents=True, exist_ok=True)

        if key_file.exists():
            return key_file.read_bytes()

        # Generate new key
        key = Fernet.generate_key()
        key_file.write_bytes(key)
        key_file.chmod(0o600)  # Owner read/write only
        return key

    def _load_file_secrets(self) -> None:
        """Load secrets from encrypted file."""
        if not self.encrypted_file.exists():
            self._file_secrets = {}
            return

        try:
            encrypted_data = self.encrypted_file.read_bytes()
            decrypted_data = self.cipher.decrypt(encrypted_data)
            self._file_secrets = json.loads(decrypted_data.decode())
        except Exception as e:
            raise SecretError(
                error_code="CFG-101",
                module="config.secrets",
                message="Failed to load encrypted secrets file",
                operation="load",
                backend="encrypted_file",
                error=str(e),
            ) from e

    def _save_file_secrets(self) -> None:
        """Save secrets to encrypted file."""
        try:
            json_data = json.dumps(self._file_secrets).encode()
            encrypted_data = self.cipher.encrypt(json_data)
            self.encrypted_file.write_bytes(encrypted_data)
            self.encrypted_file.chmod(0o600)  # Owner read/write only
        except Exception as e:
            raise SecretError(
                error_code="CFG-102",
                module="config.secrets",
                message="Failed to save encrypted secrets file",
                operation="save",
                backend="encrypted_file",
                error=str(e),
            ) from e

    def get(self, key: str, default: str | None = None) -> str | None:
        """
        Retrieve a secret value.

        Args:
            key: Secret key (e.g., "broker.api_key")
            default: Default value if secret not found

        Returns:
            Secret value or default if not found

        Raises:
            SecretError: If retrieval fails

        Example:
            ```python
            api_key = secrets.get("broker.api_key")
            password = secrets.get("broker.password", default="")
            ```
        """
        try:
            if self.use_keyring:
                value = keyring.get_password(self.service_name, key)
                return value if value is not None else default
            else:
                return self._file_secrets.get(key, default)

        except Exception as e:
            raise SecretError(
                error_code="CFG-103",
                module="config.secrets",
                message=f"Failed to retrieve secret: {key}",
                secret_key=key,
                operation="get",
                backend="keyring" if self.use_keyring else "encrypted_file",
                error=str(e),
            ) from e

    def set(self, key: str, value: str) -> None:
        """
        Store a secret value.

        Args:
            key: Secret key (e.g., "broker.api_key")
            value: Secret value to store

        Raises:
            SecretError: If storage fails

        Example:
            ```python
            secrets.set("broker.api_key", "sk-1234567890")
            secrets.set("broker.password", "mysecret")
            ```
        """
        try:
            if self.use_keyring:
                keyring.set_password(self.service_name, key, value)
            else:
                self._file_secrets[key] = value
                self._save_file_secrets()

        except Exception as e:
            raise SecretError(
                error_code="CFG-104",
                module="config.secrets",
                message=f"Failed to store secret: {key}",
                secret_key=key,
                operation="set",
                backend="keyring" if self.use_keyring else "encrypted_file",
                error=str(e),
            ) from e

    def delete(self, key: str) -> None:
        """
        Delete a secret.

        Args:
            key: Secret key to delete

        Raises:
            SecretError: If deletion fails

        Example:
            ```python
            secrets.delete("broker.api_key")
            ```
        """
        try:
            if self.use_keyring:
                try:
                    keyring.delete_password(self.service_name, key)
                except keyring.errors.PasswordDeleteError:
                    pass  # Secret doesn't exist, ignore
            else:
                if key in self._file_secrets:
                    del self._file_secrets[key]
                    self._save_file_secrets()

        except Exception as e:
            raise SecretError(
                error_code="CFG-105",
                module="config.secrets",
                message=f"Failed to delete secret: {key}",
                secret_key=key,
                operation="delete",
                backend="keyring" if self.use_keyring else "encrypted_file",
                error=str(e),
            ) from e

    def list_keys(self) -> list[str]:
        """
        List all secret keys.

        Returns:
            List of secret keys

        Note:
            Only works with encrypted file backend.
            OS keyring doesn't support listing keys.

        Example:
            ```python
            keys = secrets.list_keys()
            print(f"Stored secrets: {keys}")
            ```
        """
        if self.use_keyring:
            raise NotImplementedError("OS keyring backend does not support listing keys")

        return list(self._file_secrets.keys())

    def clear_all(self) -> None:
        """
        Clear all secrets.

        Raises:
            SecretError: If clearing fails

        Warning:
            This operation cannot be undone!

        Example:
            ```python
            secrets.clear_all()  # Remove all stored secrets
            ```
        """
        if self.use_keyring:
            raise NotImplementedError("OS keyring backend does not support clearing all secrets")

        try:
            self._file_secrets = {}
            self._save_file_secrets()
        except Exception as e:
            raise SecretError(
                error_code="CFG-106",
                module="config.secrets",
                message="Failed to clear all secrets",
                operation="clear",
                backend="encrypted_file",
                error=str(e),
            ) from e

    def get_backend(self) -> str:
        """
        Get the active secrets backend.

        Returns:
            Backend name: "keyring" or "encrypted_file"

        Example:
            ```python
            backend = secrets.get_backend()
            print(f"Using secrets backend: {backend}")
            ```
        """
        return "keyring" if self.use_keyring else "encrypted_file"
