"""
DynEL: Dynamic Error Logging Module
===================================

This module provides a dynamic and configurable logging and error-handling
utility for Python applications. It leverages the Loguru library to offer
both human-readable and machine-readable (JSON) log formats.

Key Features:
-------------
- Dynamic error logging with configurable context levels.
- Customizable exception handling based on function configurations.
- Support for multiple configuration file formats (JSON, YAML, TOML).
- Command-line interface for basic configuration overrides.
- Easy integration into other Python scripts and modules.

Module Components:
------------------
Classes:
    ContextLevel: Enum for specifying the level of context in log messages.
    CustomContext: Type hint for custom context data in log messages.
    DynelConfig: Configuration class for Dynel logging settings.

Functions:
    configure_logging: Configures Loguru logging sinks and formatting.
    global_exception_handler: A generic handler for uncaught exceptions.
    module_exception_handler: Attaches DynEL's exception handling to all
                              functions within a specified module.
    handle_exception: Core function for processing and logging exceptions
                      based on the provided configuration.
    parse_command_line_args: Parses command-line arguments for DynEL.

Note:
    The `EXCEPTION_CONFIG` mentioned in older comments is an instance attribute
    of `DynelConfig` now, not a module-level global.
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
    """
    Enum for specifying the level of context detail in log messages.

    Attributes:
        MINIMAL: Log minimal context.
        MEDIUM: Log medium level of context, including local variables.
        DETAILED: Log detailed context, including local variables and system info.
    """
    MINIMAL = 'minimal'
    MEDIUM = 'medium'
    DETAILED = 'detailed'


class CustomContext(Dict[str, Union[str, int, float, bool, None, Dict[str, Any], List[Any]]]):
    """
    Type alias for custom context data passed to the logger.
    This enhances type hinting for the `extra` field in Loguru records.
    """


class DynelConfig:
    """
    Configuration class for DynEL logging settings.

    This class holds all configuration parameters for DynEL, including
    context levels, debug mode, formatting preferences, panic mode, and
    custom exception handling rules loaded from configuration files.

    :ivar CONTEXT_LEVEL_MAP: Maps context level strings (e.g., 'min', 'med')
                             to :class:`ContextLevel` enum members.
    :vartype CONTEXT_LEVEL_MAP: Dict[str, ContextLevel]
    :ivar CUSTOM_CONTEXT_LEVEL: The active context level for logging.
    :vartype CUSTOM_CONTEXT_LEVEL: ContextLevel
    :ivar DEBUG_MODE: If True, sets logging level to DEBUG; otherwise INFO.
    :vartype DEBUG_MODE: bool
    :ivar FORMATTING_ENABLED: If True, enables special formatting (e.g., colors
                              via Loguru tags if supported by the sink).
    :vartype FORMATTING_ENABLED: bool
    :ivar PANIC_MODE: If True, DynEL will exit the program after handling an exception.
    :vartype PANIC_MODE: bool
    :ivar EXCEPTION_CONFIG: A dictionary mapping function names to their specific
                            exception handling configurations (e.g., custom messages, tags).
                            Loaded from external configuration files.
    :vartype EXCEPTION_CONFIG: Dict[str, Dict]
    """

    def __init__(self, context_level: str = 'min', debug: bool = False, formatting: bool = True, panic_mode: bool = False):
        """
        Initializes a new DynelConfig object.

        :param context_level: Short or full string for the desired context level
                              (e.g., 'min', 'minimal', 'med', 'medium', 'det', 'detailed').
                              Defaults to 'min'.
        :type context_level: str
        :param debug: If True, enables debug mode (sets log level to DEBUG).
                      Defaults to False.
        :type debug: bool
        :param formatting: If True, enables special formatting in logs.
                           Defaults to True.
        :type formatting: bool
        :param panic_mode: If True, causes the program to exit via ``sys.exit(1)``
                           after an exception is handled by :func:`handle_exception`.
                           Defaults to False.
        :type panic_mode: bool
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

    def load_exception_config(self, filename_prefix: str = "dynel_config", supported_extensions: Optional[List[str]] = None) -> None:
        """
        Loads exception handling configurations from a file.

        Searches for configuration files named ``<filename_prefix>.<ext>`` where
        `<ext>` is one of the `supported_extensions`. The first one found is loaded.
        The configuration typically includes a ``debug_mode`` boolean and then
        per-function settings for ``exceptions`` (list of exception type names),
        ``custom_message`` (str), and ``tags`` (list of str).

        :param filename_prefix: The base name of the configuration file (e.g., "dynel_config").
                                Defaults to "dynel_config".
        :type filename_prefix: str
        :param supported_extensions: A list of file extensions to try (e.g., ["json", "yaml", "toml"]).
                                     Defaults to ``["json", "yaml", "yml", "toml"]``.
        :type supported_extensions: Optional[List[str]]
        :raises FileNotFoundError: If no configuration file matching the prefix and
                                   supported extensions is found.
        :raises ValueError: If the found configuration file is malformed, uses an
                            unsupported format, or if the root of the configuration
                            is not a dictionary.
        """
        if supported_extensions is None:
            supported_extensions = ["json", "yaml", "yml", "toml"]

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
    """
    Configures Loguru's logging settings based on the provided DynelConfig.

    This function removes any existing Loguru handlers and sets up new ones:
    - A rotating file sink for text logs (``dynel.log``).
    - A rotating file sink for JSON logs (``dynel.json``).

    The log level for these sinks is set to "DEBUG" if ``config.DEBUG_MODE``
    is True, otherwise "INFO".

    :param config: The DynelConfig instance containing logging preferences.
    :type config: DynelConfig
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
    """
    A global exception handler function. (Currently simple, could be expanded).

    Logs a generic message indicating an unhandled exception.
    This function is not automatically wired up by DynEL; it's provided as a utility
    if a global fallback handler is needed (e.g., for ``sys.excepthook``).

    :param config: The DynelConfig instance. Although passed, it's not
                   explicitly used in the current simple version of this handler
                   beyond what Loguru implicitly uses.
    :type config: DynelConfig
    :param message: A message to include with the logged exception.
    :type message: str
    """
    logger.exception("An unhandled exception has occurred: {}", message)


def handle_exception(config: DynelConfig, error: Exception) -> None:
    """
    Handles and logs an exception based on DynEL's configuration.

    This is the core exception processing function. It gathers context,
    checks for function-specific configurations (custom messages, tags),
    and logs the exception using Loguru. If ``config.PANIC_MODE`` is true,
    it will exit the program after logging.

    The function name where the exception is considered to have occurred is
    determined by inspecting the call stack (caller of this function).

    :param config: The DynelConfig instance.
    :type config: DynelConfig
    :param error: The exception instance that was caught.
    :type error: Exception
    """
    # N.B. inspect.stack()[1][3] gets the name of the function that *called* handle_exception.
    # This is appropriate if handle_exception is called directly from an except block,
    # or from a simple wrapper like the one in module_exception_handler.
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
    """
    Attaches DynEL's exception handling to all functions within a given module.

    It iterates over all members of the `module` and wraps any functions
    found with Loguru's ``@logger.catch``, using a custom handler that
    invokes :func:`handle_exception`. This allows DynEL to automatically
    log exceptions from these functions according to the active configuration.

    Original functions are replaced in the module by their wrapped versions.
    This modification happens in-place.

    .. warning::
        This function modifies the provided module by replacing its functions
        with wrapped versions. This is an in-place modification.
        It does not currently handle methods within classes or already
        decorated functions in any special way beyond what ``inspect.isfunction``
        identifies.

    :param config: The DynelConfig instance to use for the exception handlers.
    :type config: DynelConfig
    :param module: The module object whose functions are to be wrapped.
    :type module: Any
    """
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj):

            def _onerror_handler(exc_or_result):
                if isinstance(exc_or_result, Exception):
                    handle_exception(config, exc_or_result) # Call it once
                    raise exc_or_result # Explicitly re-raise
                else:
                    # This was a successful function call, return its result
                    return exc_or_result

            wrapped_function = logger.catch(onerror=_onerror_handler)(obj) # reraise=True is default
            setattr(module, name, wrapped_function)
            if config.DEBUG_MODE:
                logging.debug("Wrapped function: %s", wrapped_function)


def parse_command_line_args() -> Dict[str, Any]:
    """
    Parses command-line arguments for DynEL configuration.

    Defines and parses the following arguments:
    - ``--context-level``: Sets the logging context level.
    - ``--debug``: Enables debug mode.
    - ``--no-formatting``: Disables special log formatting.

    These arguments can be used to override settings from configuration files
    or default initializations when DynEL is run or integrated in a way that
    parses command-line arguments (e.g., via its ``if __name__ == "__main__":`` block).

    :return: A dictionary containing the parsed command-line arguments.
             Keys are 'context_level', 'debug', and 'formatting'.
    :rtype: Dict[str, Any]
    """
    parser = argparse.ArgumentParser(description='DynEL Error Logging Configuration')
    parser.add_argument('--context-level', type=str, choices=['min', 'minimal', 'med', 'medium', 'det', 'detailed'], default='min', help='Set context level for error logging (min, med, det)')
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
