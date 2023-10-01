"""Dynamic Error Logging Module (Dynel)

This module provides a dynamic and configurable logging and error-handling utility.
It uses the Loguru library and supports both human-readable and machine-readable (JSON) log formats.

Attributes:
    EXCEPTION_CONFIG (dict): A dictionary mapping function names to expected exceptions.

Classes:
    - ContextLevel: Enum for specifying the level of context in log messages.
    - CustomContext: Type hint for custom context data in log messages.
    - DynelConfig: Configuration class for Dynel logging.

Functions:
    - configure_logging(config: DynelConfig) -> None: Configures logging settings.
    - global_exception_handler(config: DynelConfig, message: str) -> None: Logs uncaught exceptions globally.
    - module_exception_handler(config: DynelConfig, module: Any) -> None: Attaches exception handlers to module functions.
    - handle_exception(config: DynelConfig, error: Union[Exception, Callable]) -> None: Handles exceptions based on function configurations.
    - parse_command_line_args() -> Dict[str, Any]: Parses command-line arguments.
"""

import argparse
import inspect
import json
import logging
import os
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, cast

import toml
import yaml
from loguru import logger


class ContextLevel(Enum):
    """Enum for specifying the level of context in log messages."""
    MINIMAL = 'minimal'
    MEDIUM = 'medium'
    DETAILED = 'detailed'


class CustomContext(Dict[str, Union[str, int, Dict[str, Any]]]):
    """Type hint for custom context data in log messages."""


class DynelConfig:
     """Configuration class responsible for managing Dynel's logging settings.
    
    Attributes:
        CONTEXT_LEVEL_MAP (dict): Maps context level strings to ContextLevel Enum.
        CUSTOM_CONTEXT_LEVEL (ContextLevel): Specifies the context level.
        DEBUG_MODE (bool): Indicates if the logger is in debug mode.
        FORMATTING_ENABLED (bool): Indicates if special formatting is enabled.
        EXCEPTION_CONFIG (dict): Maps function names to their exception-handling configurations.
    """

    def __init__(self, context_level: str = 'min', debug: bool = False, formatting: bool = True, panic_mode: bool = False):
        """Initialize a new DynelConfig object.

        Args:
            context_level (str): Level of context to include in log messages.
            debug (bool): Whether to run in debug mode.
            formatting (bool): Whether to enable special formatting.
        """
        self.CONTEXT_LEVEL_MAP: Dict[str, ContextLevel] = {
            'min': ContextLevel.MINIMAL,
            'minimal': ContextLevel.MINIMAL,
            'med': ContextLevel.MEDIUM,
            'medium': ContextLevel.MEDIUM,
            'det': ContextLevel.DETAILED,
            'detailed': ContextLevel.DETAILED
        }
        self.CUSTOM_CONTEXT_LEVEL: ContextLevel = self.CONTEXT_LEVEL_MAP.get(context_level, ContextLevel.MINIMAL)
        self.DEBUG_MODE = debug
        self.FORMATTING_ENABLED = formatting
        self.EXCEPTION_CONFIG: Dict[str, Dict] = {}

    def load_exception_config(self, filename_prefix: str = "dynel_config", supported_extensions: List[str] = ["json", "yaml", "yml", "toml"]) -> None:
        """Load exception configurations from a file.
        
        Args:
            filename_prefix (str): Prefix of the configuration file.
            supported_extensions (List[str]): List of supported file extensions.
            
        Raises:
            FileNotFoundError: If no matching configuration file is found.
            ValueError: If an unsupported file format is encountered.
        """
        for ext in supported_extensions:
            config_file = Path(f"{filename_prefix}.{ext}")
            if config_file.exists():
                break
        else:
            raise FileNotFoundError(f"No matching configuration file found for {filename_prefix}")

        extension = config_file.suffix[1:]
        with config_file.open(mode="r") as f:
            if extension == 'json':
                raw_config = json.load(f)
            elif extension in ['yaml', 'yml']:
                raw_config = yaml.safe_load(f)
            elif extension == 'toml':
                raw_config = toml.load(f)
            else:
                raise ValueError("Unsupported configuration file format")

        self.DEBUG_MODE = raw_config.get("debug_mode", False)
        self.EXCEPTION_CONFIG = {
            key: {
                'exceptions': [eval(exception_str) for exception_str in value.get('exceptions', [])],
                'custom_message': value.get('custom_message', ''),
                'tags': value.get('tags', [])
            }
            for key, value in raw_config.items() if key != "debug_mode"
        }


def configure_logging(config: DynelConfig) -> None:
    """Configure logging settings based on DynelConfig.

    Args:
        config (DynelConfig): Configuration object.
    """
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    logger.remove()
    logger.add(
        sink="dynel.log",
        level="DEBUG" if config.DEBUG_MODE else "INFO",
        format=log_format,
        rotation="10 MB",
    )
    logger.add(sink="dynel.json", serialize=True, rotation="10 MB")


def global_exception_handler(config: DynelConfig, message: str) -> None:
    """Global exception handler.

    Args:
        config (DynelConfig): Configuration object.
        message (str): Exception message.
    """
    logger.exception("An unhandled exception has occurred: {}", message)


def handle_exception(config: DynelConfig, error: Union[Exception, Callable]) -> None:
    """Handles exceptions based on function-specific expected exceptions.

    Args:
        config (DynelConfig): Configuration object.
        error (Union[Exception, Callable]): The exception or callable that raised the exception.
    """
    func_name = inspect.stack()[1][3]
    function_config = config.EXCEPTION_CONFIG.get(func_name, {})
    context_level = config.CUSTOM_CONTEXT_LEVEL

    frame = inspect.currentframe()
    custom_context = cast(CustomContext, {"timestamp": str(datetime.utcnow().isoformat())})

    if context_level in [ContextLevel.MEDIUM, ContextLevel.DETAILED]:
        local_vars = frame.f_locals if frame else None
        if local_vars is not None:
            custom_context["local_vars"] = str(local_vars)

    detailed_context: Dict[str, Any] = {}
    if context_level == ContextLevel.DETAILED:
        detailed_context.update({
            "free_memory": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES"),
            "cpu_count": os.cpu_count(),
            "env_details": dict(os.environ),
        })
    if detailed_context:
        custom_context.update(detailed_context)

    error_message = f"An exception occurred in {func_name if config.FORMATTING_ENABLED else f'<red>{func_name}</red>'}."
    logger.exception(error_message)


def module_exception_handler(config: DynelConfig, module: Any) -> None:
    """Attaches exception handlers to module functions.

    Args:
        config (DynelConfig): Configuration object.
        module (Any): The module to attach exception handlers to.
    """
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj):
            wrapped_function = logger.catch(lambda e: handle_exception(config, e))(obj)
            setattr(module, name, wrapped_function)
            if config.DEBUG_MODE:
                logging.debug("Wrapped function: %s", wrapped_function)


def parse_command_line_args() -> Dict[str, Any]:
    """Parses command-line arguments and returns them as a dictionary.
    
    Returns:
        Dict[str, Any]: Dictionary of parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Error Logging Configuration')
    parser.add_argument('--context-level', type=str, choices=['min', 'minimal', 'med', 'medium', 'det', 'detailed'], default='min', help='Set context level for error logging')
    parser.add_argument('--debug', action='store_true', default=False, dest='debug', help='Run the program in debug mode')
    parser.add_argument('--no-formatting', action='store_false', default=True, dest='formatting', help='Disable special formatting')
    args = parser.parse_args()
    return {
        'context_level': args.context_level,
        'debug': args.debug,
        'formatting': args.formatting
    }


if __name__ == "__main__":
    args = parse_command_line_args()
    config = DynelConfig(**args)
    config.load_exception_config()
    configure_logging(config)
