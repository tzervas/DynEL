# flake8: noqa
"""
DynEL: Dynamic Error Logging Module
===================================

This module provides a dynamic and configurable logging and error-handling
utility for Python applications.

For full functionality, ensure Loguru is installed and configured,
though basic setup is handled by `configure_logging`.
"""

from .config import (
    ContextLevel,
    CustomContext,
    DynelConfig
)
from .logging_utils import (
    configure_logging,
    global_exception_handler
)
from .exception_handling import (
    handle_exception,
    module_exception_handler
)
from .cli import (
    parse_command_line_args
)

__all__ = [
    # From config
    "ContextLevel",
    "CustomContext",
    "DynelConfig",
    # From logging_utils
    "configure_logging",
    "global_exception_handler",
    # From exception_handling
    "handle_exception",
    "module_exception_handler",
    # From cli
    "parse_command_line_args",
]

# Version of the dynel package
__version__ = "0.1.0" # Example version, can be updated
