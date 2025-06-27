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
    The EXCEPTION_CONFIG mentioned in older comments is an instance attribute
    of :class:`DynelConfig` now, not a module-level global.
"""

import argparse
import importlib
import inspect
import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union, cast # Keep Dict, List, Optional, Type, Union for <3.9 compatibility if ever needed, though target is 3.12

import toml
import yaml
from loguru import logger


class ContextLevel(Enum):
    """
    Enum for specifying the level of context detail in log messages.

    :cvar MINIMAL: Log minimal context.
    :cvar MEDIUM: Log medium level of context, including local variables.
    :cvar DETAILED: Log detailed context, including local variables and system info.
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
    :vartype CONTEXT_LEVEL_MAP: dict[str, ContextLevel]
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
    :vartype EXCEPTION_CONFIG: dict[str, dict[str, Any]]
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
        self.CONTEXT_LEVEL_MAP: dict[str, ContextLevel] = { # Python 3.9+ dict hint
            'min': ContextLevel.MINIMAL,
            'minimal': ContextLevel.MINIMAL,
            'med': ContextLevel.MEDIUM,
            'medium': ContextLevel.MEDIUM,
            'det': ContextLevel.DETAILED,
            'detailed': ContextLevel.DETAILED
        }
        self.CUSTOM_CONTEXT_LEVEL: ContextLevel = self.CONTEXT_LEVEL_MAP.get(context_level, ContextLevel.MINIMAL)
        self.DEBUG_MODE: bool = debug
        self.FORMATTING_ENABLED: bool = formatting
        self.PANIC_MODE: bool = panic_mode
        self.EXCEPTION_CONFIG: dict[str, dict[str, Any]] = {} # Python 3.9+ dict hint

    def load_exception_config(self, filename_prefix: str = "dynel_config", supported_extensions: Optional[list[str]] = None) -> None: # Python 3.9+ list hint
        """
        Loads exception handling configurations from a file.

        Searches for configuration files named ``<filename_prefix>.<ext>`` where
        `<ext>` is one of the `supported_extensions`. The first one found is loaded.
        The configuration typically includes a ``debug_mode`` boolean and then
        per-function settings for ``exceptions`` (list of exception type names),
        ``custom_message`` (str), and ``tags`` (list of str).

        :param filename_prefix: The base name of the configuration file, defaults to "dynel_config".
        :type filename_prefix: str, optional
        :param supported_extensions: A list of file extensions to try, defaults to ["json", "yaml", "yml", "toml"].
        :type supported_extensions: Optional[list[str]], optional
        :raises FileNotFoundError: If no configuration file matching the prefix and
                                   supported extensions is found.
        :raises ValueError: If the found configuration file is malformed, uses an
                            unsupported format, or if the root of the configuration
                            is not a dictionary.
        """
        if supported_extensions is None:
            supported_extensions = ["json", "yaml", "yml", "toml"]

        config_file_found: Path | None = None # Python 3.10+ union syntax
        for ext_loop_var in supported_extensions:
            config_file = Path(f"{filename_prefix}.{ext_loop_var}")
            if config_file.exists():
                config_file_found = config_file
                break

        if not config_file_found:
            raise FileNotFoundError(f"No matching configuration file found for {filename_prefix} with extensions {supported_extensions}")

        extension = config_file_found.suffix[1:]
        raw_config: Any = None # Initialize raw_config
        try:
            with config_file_found.open(mode="r") as f:
                if extension == 'json':
                    raw_config = json.load(f)
                elif extension in ['yaml', 'yml']:
                    raw_config = yaml.safe_load(f)
                elif extension == 'toml':
                    raw_config = toml.load(f)
                else:
                    logger.error(f"Unsupported configuration file format encountered: {extension}")
                    raise ValueError(f"Unsupported configuration file format: {extension}")
        except (json.JSONDecodeError, yaml.YAMLError, toml.TomlDecodeError) as e:
            logger.error(f"Error parsing DynEL configuration file '{config_file_found}': {e}")
            raise ValueError(f"Failed to parse DynEL configuration file '{config_file_found}': {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error reading DynEL configuration file '{config_file_found}': {e}")
            raise ValueError(f"Unexpected error reading DynEL configuration file '{config_file_found}': {e}") from e

        if not isinstance(raw_config, dict):
            logger.error(f"Invalid DynEL configuration file '{config_file_found}': Expected a dictionary (object/map) at the root, got {type(raw_config).__name__}.")
            raise ValueError(f"Invalid DynEL configuration file '{config_file_found}': Root of configuration must be a dictionary.")

        self.DEBUG_MODE = raw_config.get("debug_mode", self.DEBUG_MODE)

        parsed_exception_config: dict[str, dict[str, Any]] = {} # Python 3.9+
        for key, value in raw_config.items():
            if key == "debug_mode":
                continue
            if not isinstance(value, dict):
                logger.warning(f"Configuration for '{key}' is not a dictionary. Skipping.")
                continue

            exception_classes: list[Type[Exception]] = [] # Python 3.9+
            for exception_str in value.get('exceptions', []):
                if not isinstance(exception_str, str):
                    logger.warning(f"Invalid exception name type for '{key}': {exception_str}. Must be a string. Skipping.")
                    continue
                try:
                    exception_class_val: Any = __builtins__.get(exception_str) # type: ignore
                    if not (exception_class_val and isinstance(exception_class_val, type) and issubclass(exception_class_val, BaseException)):
                        module_name, class_name = exception_str.rsplit('.', 1)
                        module = importlib.import_module(module_name)
                        exception_class_val = getattr(module, class_name)

                    if not (isinstance(exception_class_val, type) and issubclass(exception_class_val, BaseException)):
                        raise TypeError(f"'{exception_str}' is not an Exception subclass.")
                    exception_classes.append(exception_class_val)
                except (AttributeError, ImportError, ValueError, TypeError) as e:
                    logger.warning(f"Could not load or validate exception '{exception_str}' for '{key}': {e}. Skipping.")
                except Exception as e:
                    logger.error(f"Unexpected error loading exception '{exception_str}' for '{key}': {e}. Skipping.")

            parsed_exception_config[key] = {
                'exceptions': exception_classes,
                'custom_message': str(value.get('custom_message', '')), # Ensure string
                'tags': [str(tag) for tag in value.get('tags', []) if isinstance(tag, (str, int, float))] # Ensure tags are strings
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
        catch=True
    )
    logger.add(
        sink="dynel.json",
        serialize=True,
        level="DEBUG" if config.DEBUG_MODE else "INFO",
        rotation="10 MB",
        catch=True
    )


def global_exception_handler(config: DynelConfig, message: str) -> None:
    """
    A global exception handler utility function.

    Logs a generic message indicating an unhandled exception using Loguru's
    exception logging, which includes traceback information. This function
    is not automatically wired up by DynEL (e.g., to ``sys.excepthook``);
    it's provided as a utility if such a global fallback is needed.

    :param config: The DynelConfig instance.
    :type config: DynelConfig
    :param message: A descriptive message to include with the logged exception.
    :type message: str
    """
    logger.exception("An unhandled exception has occurred: {}", message)


def handle_exception(config: DynelConfig, error: Exception) -> None:
    """
    Handles and logs an exception based on DynEL's configuration.

    This is the core exception processing function. It gathers context based on
    the configured :class:`ContextLevel`, checks for function-specific configurations
    (like custom messages and tags) from ``config.EXCEPTION_CONFIG``, and logs
    the exception using Loguru.

    If ``config.PANIC_MODE`` is true, this function will call ``sys.exit(1)``
    after logging the exception.

    The function name where the exception occurred for configuration lookup
    is determined by inspecting the call stack (caller of this function).

    :param config: The DynelConfig instance.
    :type config: DynelConfig
    :param error: The exception instance that was caught.
    :type error: Exception
    """
    func_name = inspect.stack()[1][3]
    function_config = config.EXCEPTION_CONFIG.get(func_name, {})
    context_level = config.CUSTOM_CONTEXT_LEVEL

    custom_context_dict: dict[str, Any] = {"timestamp": str(datetime.now(timezone.utc).isoformat())} # Python 3.9+

    if context_level in [ContextLevel.MEDIUM, ContextLevel.DETAILED]:
        caller_frame_info = inspect.stack()[1] # This is a FrameInfo object (named tuple like)
        caller_frame = caller_frame_info[0]    # Access the frame object by index
        local_vars = caller_frame.f_locals if caller_frame else None
        if local_vars:
            try:
                custom_context_dict["local_vars"] = str(local_vars)
            except Exception:
                custom_context_dict["local_vars"] = "Error converting local_vars to string"
        else:
            custom_context_dict["local_vars"] = "Local variables information unavailable"


    if context_level == ContextLevel.DETAILED:
        detailed_context: dict[str, Any] = {} # Python 3.9+
        try:
            detailed_context["free_memory"] = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES")
            detailed_context["cpu_count"] = os.cpu_count()
        except (OSError, AttributeError):
            detailed_context["system_info_error"] = "Could not retrieve some system info (memory/CPU)"

        try:
            detailed_context["env_details"] = dict(os.environ)
        except Exception:
            detailed_context["env_details_error"] = "Could not retrieve environment variables"

        custom_context_dict.update(detailed_context)

    log_message_str = f"Exception caught in {func_name if config.FORMATTING_ENABLED else func_name}"

    if func_name in config.EXCEPTION_CONFIG:
        func_conf = config.EXCEPTION_CONFIG[func_name]
        for configured_exc_type in func_conf.get('exceptions', []):
            if isinstance(error, configured_exc_type):
                final_custom_message = func_conf.get('custom_message')
                final_tags = func_conf.get('tags')
                if final_custom_message:
                    log_message_str += f" - Custom Message: {final_custom_message}"
                if final_tags: # Ensure tags are added if this specific exception matched
                    custom_context_dict["tags"] = final_tags
                break

    bound_logger = logger.bind(**cast(CustomContext, custom_context_dict))
    bound_logger.exception(log_message_str, exception=error)

    if config.PANIC_MODE:
        logger.critical(f"PANIC MODE ENABLED: Exiting after handling exception in {func_name}.")
        sys.exit(1)


def module_exception_handler(config: DynelConfig, module: Any) -> None:
    """
    Attaches DynEL's exception handling to all functions within a given module.

    It iterates over all members of the `module` and wraps any functions
    found with Loguru's ``@logger.catch``, using a custom ``onerror`` handler.
    This custom handler ensures that :func:`handle_exception` is invoked for
    exceptions, and successful return values are passed through.

    Original functions in the module are replaced by their wrapped versions
    (in-place modification).

    .. warning::
        This function modifies the provided module by replacing its functions
        with wrapped versions. It does not currently handle methods within classes
        or already decorated functions in any special way beyond what
        ``inspect.isfunction`` identifies.

    :param config: The DynelConfig instance to use for the exception handlers.
    :type config: DynelConfig
    :param module: The module object whose functions are to be wrapped.
    :type module: Any
    """
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj):

            def _onerror_handler(exc_or_result: Exception | Any): # Python 3.10+ union
                if isinstance(exc_or_result, Exception):
                    handle_exception(config, exc_or_result)
                    raise exc_or_result
                else:
                    return exc_or_result

            wrapped_function = logger.catch(onerror=_onerror_handler, reraise=True)(obj)
            setattr(module, name, wrapped_function)
            if config.DEBUG_MODE:
                module_name_for_log = getattr(module, '__name__', 'UnknownModule')
                logging.debug("Wrapped function: %s in module %s", name, module_name_for_log)


def parse_command_line_args() -> dict[str, Any]: # Python 3.9+
    """
    Parses command-line arguments for DynEL configuration.

    Defines and parses the following arguments:
    - ``--context-level``: Sets the logging context level.
      Choices: 'min', 'minimal', 'med', 'medium', 'det', 'detailed'.
    - ``--debug``: Enables debug mode (sets log level to DEBUG).
    - ``--no-formatting``: Disables special log formatting.

    These arguments can be used to override settings from configuration files
    or default initializations when DynEL is run or integrated in a way that
    parses command-line arguments (e.g., via its ``if __name__ == "__main__":`` block).

    :return: A dictionary containing the parsed command-line arguments.
             Keys are 'context_level', 'debug', and 'formatting'.
    :rtype: dict[str, Any]
    """
    parser = argparse.ArgumentParser(description='DynEL Error Logging Configuration')
    parser.add_argument(
        '--context-level',
        type=str,
        choices=['min', 'minimal', 'med', 'medium', 'det', 'detailed'],
        default='min',
        help='Set context level for error logging (min, med, det)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        default=False,
        help='Run the program in debug mode'
    )
    parser.add_argument(
        '--no-formatting',
        action='store_false',
        default=True,
        dest='formatting',
        help='Disable special formatting'
    )
    args = parser.parse_args()
    return {
        'context_level': args.context_level,
        'debug': args.debug,
        'formatting': args.formatting
    }


if __name__ == "__main__":
    cli_args = parse_command_line_args()

    config = DynelConfig(
        context_level=cli_args['context_level'],
        debug=cli_args['debug'],
        formatting=cli_args['formatting']
    )

    try:
        config.load_exception_config()
        print(f"Loaded exception configuration. Debug mode: {config.DEBUG_MODE}")
    except FileNotFoundError:
        print("No DynEL configuration file found. Using default/CLI settings.")
    except ValueError as e:
        print(f"Error loading DynEL configuration: {e}. Using default/CLI settings.")

    configure_logging(config)

    logger.info("DynEL logging configured. Debug mode: {}. Context level: {}", config.DEBUG_MODE, config.CUSTOM_CONTEXT_LEVEL.value)

    def example_function_one():
        try:
            x = 1 / 0
        except ZeroDivisionError as e:
            handle_exception(config, e)

    def example_function_two():
        try:
            my_dict: dict = {} # Python 3.9+
            _ = my_dict["non_existent_key"]
        except KeyError as e:
            handle_exception(config, e)

    logger.info("Running example functions to demonstrate DynEL.")
    example_function_one()
    example_function_two()

    logger.info("DynEL demonstration finished.")
