# DynEL Core Functionality
# This file will contain the main logic for DynEL,
# including data structures and core operations.

class DynelConfig:
    """
    Configuration for DynEL.
    This class will hold settings for context level, debug mode, formatting, etc.
    """
    def __init__(self, context_level: str = "medium", debug: bool = False, formatting: bool = True, colorize: bool | None = None):
        """
        Initialize DynelConfig.
        
        Args:
            context_level (str): Level of context ('medium' by default)
            debug (bool): Enable debug mode (False by default)
            formatting (bool): Enable formatting (True by default)
            colorize (bool | None): Enable colorized output. If None, determined by sys.stderr.isatty() (None by default)
        """
        self.context_level = context_level
        self.debug = debug
        self.formatting = formatting
        self.colorize = sys.stderr.isatty() if colorize is None else colorize

import warnings
import sys # For stderr
from loguru import logger

def _get_log_level(debug: bool) -> str:
    """Determine the log level based on debug setting."""
    return "DEBUG" if debug else "INFO"

def _get_console_format(formatting: bool) -> str:
    """Get the console format string based on formatting setting."""
    if formatting:
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
    return "<level>{message}</level>"

def _get_file_sink_settings(level: str) -> dict:
    """Get common settings for file sinks."""
    return {
        "level": level,
        "rotation": "10 MB",
        "retention": "5 files",
        "encoding": "utf8"
    }

# Global list to track DynEL-specific handler IDs
_dynel_handler_ids = []

def configure_logging(config: DynelConfig):
    """
    Configures logging based on the provided DynelConfig using Loguru.

    - Removes existing DynEL handlers.
    - Adds a console sink (stderr):
        - Level: DEBUG if config.debug else INFO.
        - Format: Detailed if config.formatting else simple.
        - Colorize based on config and stderr.isatty()
    - Adds file sinks:
        - `dynel.log` (human-readable, rotation: 10MB, retention: 5 files)
        - `dynel.json` (JSON format, rotation: 10MB, retention: 5 files)
        - Level: DEBUG if config.debug else INFO.
    """
    global _dynel_handler_ids
    
    # Remove only DynEL-specific handlers
    for handler_id in _dynel_handler_ids:
        logger.remove(handler_id)
    _dynel_handler_ids.clear()

    # Configure console sink
    console_level = _get_log_level(config.debug)
    console_format = _get_console_format(config.formatting)
    # Add console sink and track its ID
    handler_id = logger.add(
        sys.stderr,
        level=console_level,
        format=console_format,
        colorize=config.colorize  # Use config's colorize setting
    )
    _dynel_handler_ids.append(handler_id)

    # Configure file sinks
    file_sink_settings = _get_file_sink_settings(_get_log_level(config.debug))

    # Human-readable file log
    # Add human-readable file log and track its ID
    handler_id = logger.add(
        "dynel.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        **file_sink_settings
    )
    _dynel_handler_ids.append(handler_id)

    # JSON file log
    # Add JSON file log and track its ID
    handler_id = logger.add(
        "dynel.json",
        serialize=True,  # Key for JSON output
        **file_sink_settings
    )
    _dynel_handler_ids.append(handler_id)

    logger.info(f"DynEL logging configured. Console Level: {console_level}, File Level: {file_sink_settings['level']}, Formatting: {config.formatting}")


def module_exception_handler(config: DynelConfig, module):
    """
    Attaches DynEL's exception handler to another module.

    Placeholder: This function does not provide real exception handling yet.
    Do not rely on this for production error handling. No actual error handling is performed.
    """
    warnings.warn(
        "module_exception_handler is a placeholder and does not provide real exception handling. "
        "Dependent code should not assume error handling is in place.",
        UserWarning
    )
    print(f"Exception handler attached to module: {module.__name__} with config: {config.context_level} (placeholder, no real error handling)")
