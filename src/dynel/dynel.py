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
import argparse
import importlib
import inspect
import json
import logging
import os
import sys # Added for sys.exit
import traceback
from datetime import datetime, timezone # Added timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union, cast

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
        self.PANIC_MODE = panic_mode  # Added panic_mode initialization
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
        for ext_loop_var in supported_extensions: # Renamed to avoid conflict with outer 'ext' in test parameterization
            config_file = Path(f"{filename_prefix}.{ext_loop_var}")
            if config_file.exists():
                break
        else:
            raise FileNotFoundError(f"No matching configuration file found for {filename_prefix}")

        extension = config_file.suffix[1:]
        try:
            with config_file.open(mode="r") as f:
                if extension == 'json':
                    raw_config = json.load(f)
                elif extension in ['yaml', 'yml']:
                    raw_config = yaml.safe_load(f)
                elif extension == 'toml':
                    raw_config = toml.load(f)
                else:
                    # This case should ideally not be reached if supported_extensions is maintained
                    logger.error(f"Unsupported configuration file format encountered: {extension}")
                    raise ValueError(f"Unsupported configuration file format: {extension}")
        except (json.JSONDecodeError, yaml.YAMLError, toml.TomlDecodeError) as e:
            logger.error(f"Error parsing DynEL configuration file '{config_file}': {e}")
            # Decide if to raise, or continue with default/empty config, or partial config.
            # For now, let's raise to make the issue prominent.
            raise ValueError(f"Failed to parse DynEL configuration file '{config_file}': {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error reading DynEL configuration file '{config_file}': {e}")
            raise ValueError(f"Unexpected error reading DynEL configuration file '{config_file}': {e}") from e

        if not isinstance(raw_config, dict):
            logger.error(f"Invalid DynEL configuration file '{config_file}': Expected a dictionary (object/map) at the root, got {type(raw_config).__name__}.")
            raise ValueError(f"Invalid DynEL configuration file '{config_file}': Root of configuration must be a dictionary.")

        self.DEBUG_MODE = raw_config.get("debug_mode", False)

        parsed_exception_config: Dict[str, Dict[str, Any]] = {}
        for key, value in raw_config.items(): # type: ignore
            if key == "debug_mode":
                continue

            exception_classes: List[Type[Exception]] = []
            for exception_str in value.get('exceptions', []):
                try:
                    # Try built-in exceptions first
                    exception_class = __builtins__.get(exception_str) # type: ignore
                    if exception_class is None or not issubclass(exception_class, BaseException):
                        # If not a built-in or not an exception, try importing
                        module_name, class_name = exception_str.rsplit('.', 1)
                        module = importlib.import_module(module_name)
                        exception_class = getattr(module, class_name)

                    if issubclass(exception_class, BaseException): # type: ignore
                        exception_classes.append(exception_class) # type: ignore
                    else:
                        logger.warning(f"Configured exception '{exception_str}' for '{key}' is not a valid Exception class. Skipping.")
                except (AttributeError, ImportError, ValueError) as e:
                    logger.warning(f"Could not load exception '{exception_str}' for '{key}': {e}. Skipping.")
                except Exception as e:
                    logger.error(f"Unexpected error loading exception '{exception_str}' for '{key}': {e}. Skipping.")


            parsed_exception_config[key] = {
                'exceptions': exception_classes,
                'custom_message': value.get('custom_message', ''),
                'tags': value.get('tags', [])
            }
        self.EXCEPTION_CONFIG = parsed_exception_config


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
    custom_context = cast(CustomContext, {"timestamp": str(datetime.now(timezone.utc).isoformat())})

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

    log_message = f"Exception caught in {func_name if config.FORMATTING_ENABLED else func_name}"
    final_custom_message = None
    final_tags = None

    if isinstance(error, Exception):
        # Check if this specific exception type is configured for the function
        if func_name in config.EXCEPTION_CONFIG:
            func_conf = config.EXCEPTION_CONFIG[func_name]
            for configured_exc_type in func_conf.get('exceptions', []):
                if isinstance(error, configured_exc_type):
                    final_custom_message = func_conf.get('custom_message')
                    final_tags = func_conf.get('tags')
                    if final_custom_message:
                        log_message += f" - Custom Message: {final_custom_message}"
                    break

    # Ensure custom_context is correctly passed to logger
    # Loguru's .exception() method automatically includes exception info.
    # If we want to add custom context fields AND specific tags, we might need to use .opt(record=True) or structure the message.

    # For now, let's add tags to the custom_context if they exist
    if final_tags:
        custom_context["tags"] = final_tags
    if final_custom_message and not isinstance(error, Exception): # Error is a callable for logger.catch
        # This case is tricky with logger.catch as error is the exception instance, not the callable
        pass


    # Log with the gathered context and potentially modified message
    # The `error` argument itself, if an Exception, provides the traceback to logger.exception
    # If `error` is a callable (from logger.catch initial setup), logger.exception() won't use it directly.
    # However, when logger.catch invokes this handler, 'error' will be the actual exception instance.

    current_logger = logger.bind(**custom_context)
    if isinstance(error, Exception):
        current_logger.exception(log_message) # error provides traceback
    else:
        # This branch should ideally not be hit if used with logger.catch correctly,
        # as 'error' will be the exception instance.
        # If 'error' is some other arbitrary callable not an exception, this is generic.
        current_logger.error(f"{log_message} - (No direct exception instance provided to handler)")

    if config.PANIC_MODE:
        logger.critical(f"PANIC MODE ENABLED: Exiting after handling exception in {func_name}.")
        sys.exit(1)


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
