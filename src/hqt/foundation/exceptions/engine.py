"""
Engine-related exception classes for the HQT trading system.

This module provides exceptions for the C++ core engine and
Python-C++ bridge operations.
"""

from typing import Any

from .base import HQTBaseError


class EngineError(HQTBaseError):
    """
    Base class for all engine-related errors.

    This exception covers errors from the C++ core engine,
    including event processing, state management, and engine lifecycle.

    Additional Context Fields:
        engine_state: Current engine state
        operation: The operation that failed
        tick_count: Number of ticks processed
        event_type: Type of event being processed

    Example:
        ```python
        raise EngineError(
            error_code="ENG-001",
            module="engine.core",
            message="Engine initialization failed",
            engine_state="initializing",
            operation="load_data"
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        engine_state: str | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            engine_state=engine_state,
            **context,
        )


class BridgeError(HQTBaseError):
    """
    Raised when Python-C++ bridge operations fail.

    This exception indicates errors in the Nanobind bridge layer,
    including type conversion errors, GIL issues, and cross-language
    communication failures.

    Additional Context Fields:
        bridge_operation: The bridge operation that failed
        python_type: Python type involved
        cpp_type: C++ type involved
        conversion_direction: "py_to_cpp" or "cpp_to_py"
        gil_state: GIL acquisition state

    Example:
        ```python
        raise BridgeError(
            error_code="BRG-001",
            module="bridge.types",
            message="Failed to convert Python object to C++ type",
            bridge_operation="convert_bar",
            python_type="dict",
            cpp_type="Bar",
            conversion_direction="py_to_cpp"
        )
        ```
    """

    def __init__(
        self,
        error_code: str,
        module: str,
        message: str,
        bridge_operation: str | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            error_code=error_code,
            module=module,
            message=message,
            bridge_operation=bridge_operation,
            **context,
        )
