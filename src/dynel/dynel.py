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
<<<<<<< HEAD
from typing import Any, Callable, Dict, List, Optional, Type, Union, cast # Keep Dict, List, Optional, Type, Union for <3.9 compatibility if ever needed, though target is 3.12
=======
from typing import Any, Callable, Dict, List, Optional, Type, Union, cast
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd

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
<<<<<<< HEAD
    """
=======
    """Configuration class responsible for managing Dynel's logging settings.
    
    Attributes:
        CONTEXT_LEVEL_MAP (dict): Maps context level strings to ContextLevel Enum.
        CUSTOM_CONTEXT_LEVEL (ContextLevel): Specifies the context level.
        DEBUG_MODE (bool): Indicates if the logger is in debug mode.
        FORMATTING_ENABLED (bool): Indicates if special formatting is enabled.
        EXCEPTION_CONFIG (dict): Maps function names to their exception-handling configurations.

>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
    Configuration class for DynEL logging settings.

    This class holds all configuration parameters for DynEL, including
    context levels, debug mode, formatting preferences, panic mode, and
    custom exception handling rules loaded from configuration files.

    :ivar CONTEXT_LEVEL_MAP: Maps context level strings (e.g., 'min', 'med')
                             to :class:`ContextLevel` enum members.
<<<<<<< HEAD
    :vartype CONTEXT_LEVEL_MAP: dict[str, ContextLevel]
=======
    :vartype CONTEXT_LEVEL_MAP: Dict[str, ContextLevel]
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
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
<<<<<<< HEAD
    :vartype EXCEPTION_CONFIG: dict[str, dict[str, Any]]
    """

    def __init__(self, context_level: str = 'min', debug: bool = False, formatting: bool = True, panic_mode: bool = False):
=======
    :vartype EXCEPTION_CONFIG: Dict[str, Dict[str, Any]]
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
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
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
<<<<<<< HEAD
        self.DEBUG_MODE: bool = debug
        self.FORMATTING_ENABLED: bool = formatting
        self.PANIC_MODE: bool = panic_mode
        self.EXCEPTION_CONFIG: dict[str, dict[str, Any]] = {} # Python 3.9+ dict hint

    def load_exception_config(self, filename_prefix: str = "dynel_config", supported_extensions: Optional[list[str]] = None) -> None: # Python 3.9+ list hint
=======
        self.DEBUG_MODE = debug
        self.FORMATTING_ENABLED = formatting
        self.PANIC_MODE = panic_mode
        self.EXCEPTION_CONFIG: Dict[str, Dict[str, Any]] = {}

    def load_exception_config(self, filename_prefix: str = "dynel_config", supported_extensions: Optional[List[str]] = None) -> None:
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
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
<<<<<<< HEAD
        :type supported_extensions: Optional[list[str]], optional
=======
        :type supported_extensions: Optional[List[str]], optional
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
        :raises FileNotFoundError: If no configuration file matching the prefix and
                                   supported extensions is found.
        :raises ValueError: If the found configuration file is malformed, uses an
                            unsupported format, or if the root of the configuration
                            is not a dictionary.
        """
        if supported_extensions is None:
            supported_extensions = ["json", "yaml", "yml", "toml"]

<<<<<<< HEAD
        config_file_found: Path | None = None # Python 3.10+ union syntax
=======
        config_file_found: Optional[Path] = None
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
        for ext_loop_var in supported_extensions:
            config_file = Path(f"{filename_prefix}.{ext_loop_var}")
            if config_file.exists():
                config_file_found = config_file
                break

        if not config_file_found:
            raise FileNotFoundError(f"No matching configuration file found for {filename_prefix} with extensions {supported_extensions}")

        extension = config_file_found.suffix[1:]
<<<<<<< HEAD
        raw_config: Any = None # Initialize raw_config
=======
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
        try:
            with config_file_found.open(mode="r") as f:
                if extension == 'json':
                    raw_config = json.load(f)
                elif extension in ['yaml', 'yml']:
                    raw_config = yaml.safe_load(f)
                elif extension == 'toml':
                    raw_config = toml.load(f)
                else:
<<<<<<< HEAD
=======
                    # This case should ideally not be reached
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
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

<<<<<<< HEAD
        self.DEBUG_MODE = raw_config.get("debug_mode", self.DEBUG_MODE)

        parsed_exception_config: dict[str, dict[str, Any]] = {} # Python 3.9+
        for key, value in raw_config.items():
            if key == "debug_mode":
                continue
            if not isinstance(value, dict):
                logger.warning(f"Configuration for '{key}' is not a dictionary. Skipping.")
                continue

            exception_classes: list[Type[Exception]] = [] # Python 3.9+
=======
        self.DEBUG_MODE = raw_config.get("debug_mode", self.DEBUG_MODE) # Retain init debug_mode if not in file

        parsed_exception_config: Dict[str, Dict[str, Any]] = {}
        for key, value in raw_config.items():
            if key == "debug_mode":
                continue
            if not isinstance(value, dict): # Ensure function config is a dict
                logger.warning(f"Configuration for '{key}' is not a dictionary. Skipping.")
                continue

            exception_classes: List[Type[Exception]] = []
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
            for exception_str in value.get('exceptions', []):
                if not isinstance(exception_str, str):
                    logger.warning(f"Invalid exception name type for '{key}': {exception_str}. Must be a string. Skipping.")
                    continue
                try:
<<<<<<< HEAD
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
=======
                    exception_class = __builtins__.get(exception_str) # type: ignore
                    if not (exception_class and issubclass(exception_class, BaseException)):
                        module_name, class_name = exception_str.rsplit('.', 1)
                        module = importlib.import_module(module_name)
                        exception_class = getattr(module, class_name)

                    if not issubclass(exception_class, BaseException): # type: ignore
                        raise TypeError(f"'{exception_str}' is not an Exception subclass.")
                    exception_classes.append(exception_class) # type: ignore
                except (AttributeError, ImportError, ValueError, TypeError) as e:
                    logger.warning(f"Could not load or validate exception '{exception_str}' for '{key}': {e}. Skipping.")
                except Exception as e: # Catch any other unexpected errors during loading
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
                    logger.error(f"Unexpected error loading exception '{exception_str}' for '{key}': {e}. Skipping.")

            parsed_exception_config[key] = {
                'exceptions': exception_classes,
<<<<<<< HEAD
                'custom_message': str(value.get('custom_message', '')), # Ensure string
                'tags': [str(tag) for tag in value.get('tags', []) if isinstance(tag, (str, int, float))] # Ensure tags are strings
=======
                'custom_message': value.get('custom_message', ''),
                'tags': value.get('tags', [])
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
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
    logger.remove() # Remove all existing handlers
    logger.add(
        sink="dynel.log",
        level="DEBUG" if config.DEBUG_MODE else "INFO",
        format=log_format,
        rotation="10 MB",
<<<<<<< HEAD
        catch=True
=======
        catch=True # Catch errors within the logger itself
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
    )
    logger.add(
        sink="dynel.json",
        serialize=True,
        level="DEBUG" if config.DEBUG_MODE else "INFO",
        rotation="10 MB",
<<<<<<< HEAD
        catch=True
=======
        catch=True # Catch errors within the logger itself
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
    )


def global_exception_handler(config: DynelConfig, message: str) -> None:
    """
    A global exception handler utility function.

    Logs a generic message indicating an unhandled exception using Loguru's
    exception logging, which includes traceback information. This function
    is not automatically wired up by DynEL (e.g., to ``sys.excepthook``);
    it's provided as a utility if such a global fallback is needed.

<<<<<<< HEAD
    :param config: The DynelConfig instance.
=======
    :param config: The DynelConfig instance. While passed, its direct attributes
                   are not explicitly used in this handler's current version,
                   as Loguru's logger is used directly. It's included for API
                   consistency and potential future enhancements.
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
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

<<<<<<< HEAD
    The function name where the exception occurred for configuration lookup
    is determined by inspecting the call stack (caller of this function).

    :param config: The DynelConfig instance.
    :type config: DynelConfig
    :param error: The exception instance that was caught.
=======
    The function name, where the exception is considered to have occurred for
    configuration lookup, is determined by inspecting the call stack (specifically,
    the caller of this ``handle_exception`` function).

    :param config: The DynelConfig instance containing all operational settings.
    :type config: DynelConfig
    :param error: The exception instance that was caught and needs to be handled.
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
    :type error: Exception
    """
    func_name = inspect.stack()[1][3]
    function_config = config.EXCEPTION_CONFIG.get(func_name, {})
    context_level = config.CUSTOM_CONTEXT_LEVEL

<<<<<<< HEAD
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
=======
    frame = inspect.currentframe()
    custom_context_dict: Dict[str, Any] = {"timestamp": str(datetime.now(timezone.utc).isoformat())}

    if context_level in [ContextLevel.MEDIUM, ContextLevel.DETAILED]:
        # Ensure frame is not None before accessing f_locals
        current_frame_obj = inspect.currentframe()
        if current_frame_obj:
            # Get locals from the *caller* of handle_exception, not handle_exception's own locals.
            # This requires going one step further up the stack if handle_exception is called directly.
            # However, if used with logger.catch, the frame context might be different.
            # For direct calls (as in tests), stack()[1] is the caller. Its frame is stack()[1].frame.
            # For simplicity and current use with logger.catch, using currentframe().f_back might be more robust
            # if we want the caller of the function that was decorated by logger.catch.
            # The current inspect.stack()[1][3] gets the name of the *caller of handle_exception*.
            # For local_vars, we want the locals from *that* frame.
            caller_frame = inspect.stack()[1].frame
            local_vars = caller_frame.f_locals if caller_frame else None
            if local_vars:
                try:
                    custom_context_dict["local_vars"] = str(local_vars)
                except Exception: # Catch potential errors during string conversion of complex locals
                    custom_context_dict["local_vars"] = "Error converting local_vars to string"
        else: # Fallback if current_frame_obj is None
            custom_context_dict["local_vars"] = "Frame information unavailable"


    if context_level == ContextLevel.DETAILED:
        detailed_context: Dict[str, Any] = {}
        try:
            detailed_context["free_memory"] = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES")
            detailed_context["cpu_count"] = os.cpu_count()
        except (OSError, AttributeError): # Handle cases where sysconf or cpu_count might not be available/work
            detailed_context["system_info_error"] = "Could not retrieve some system info (memory/CPU)"

        try: # Separate try-except for env_details for more granular error reporting
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
            detailed_context["env_details"] = dict(os.environ)
        except Exception:
            detailed_context["env_details_error"] = "Could not retrieve environment variables"

        custom_context_dict.update(detailed_context)

    log_message_str = f"Exception caught in {func_name if config.FORMATTING_ENABLED else func_name}"
<<<<<<< HEAD

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

=======
    final_custom_message = None
    final_tags = None

    if isinstance(error, Exception): # This check is somewhat redundant given type hint, but safe
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
                        log_message_str += f" - Custom Message: {final_custom_message}"
                    break

    if final_tags:
        custom_context_dict["tags"] = final_tags

    # Use cast to satisfy type checker for custom_context_dict if it expects CustomContext type strictly
    bound_logger = logger.bind(**cast(CustomContext, custom_context_dict))

    # Loguru's logger.exception() automatically appends exception info including traceback.
    bound_logger.exception(log_message_str, exception=error)


>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
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

<<<<<<< HEAD
            def _onerror_handler(exc_or_result: Exception | Any): # Python 3.10+ union
                if isinstance(exc_or_result, Exception):
                    handle_exception(config, exc_or_result)
                    raise exc_or_result
                else:
=======
            def _onerror_handler(exc_or_result: Union[Exception, Any]):
                if isinstance(exc_or_result, Exception):
                    handle_exception(config, exc_or_result)
                    raise exc_or_result # Explicitly re-raise so logger.catch propagates it
                else:
                    # This was a successful function call, return its result
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
                    return exc_or_result

            wrapped_function = logger.catch(onerror=_onerror_handler, reraise=True)(obj)
            setattr(module, name, wrapped_function)
            if config.DEBUG_MODE:
<<<<<<< HEAD
                module_name_for_log = getattr(module, '__name__', 'UnknownModule')
                logging.debug("Wrapped function: %s in module %s", name, module_name_for_log)


def parse_command_line_args() -> dict[str, Any]: # Python 3.9+
=======
                logging.debug("Wrapped function: %s in module %s", name, module.__name__)


def parse_command_line_args() -> Dict[str, Any]:
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
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
<<<<<<< HEAD
    :rtype: dict[str, Any]
=======
    :rtype: Dict[str, Any]
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
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
<<<<<<< HEAD
=======
        # dest='debug', # Not needed if action is store_true and default is False
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
        help='Run the program in debug mode'
    )
    parser.add_argument(
        '--no-formatting',
        action='store_false',
<<<<<<< HEAD
        default=True,
        dest='formatting',
=======
        default=True, # Default is formatting enabled
        dest='formatting', # Destination for store_false
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
        help='Disable special formatting'
    )
    args = parser.parse_args()
    return {
        'context_level': args.context_level,
        'debug': args.debug,
        'formatting': args.formatting
    }


if __name__ == "__main__":
<<<<<<< HEAD
    cli_args = parse_command_line_args()

=======
    # This block is for basic testing or direct execution of the module.
    # In a real application, you would import and use DynelConfig, configure_logging, etc.

    # Parse command line arguments first
    cli_args = parse_command_line_args()

    # Initialize DynelConfig with values from CLI or defaults
    # CLI args will override constructor defaults if provided.
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
    config = DynelConfig(
        context_level=cli_args['context_level'],
        debug=cli_args['debug'],
        formatting=cli_args['formatting']
<<<<<<< HEAD
    )

=======
        # panic_mode can be set here or loaded from file
    )

    # Attempt to load further configuration from a file.
    # This might override debug_mode again if it's in the file.
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
    try:
        config.load_exception_config()
        print(f"Loaded exception configuration. Debug mode: {config.DEBUG_MODE}")
    except FileNotFoundError:
        print("No DynEL configuration file found. Using default/CLI settings.")
    except ValueError as e:
        print(f"Error loading DynEL configuration: {e}. Using default/CLI settings.")

<<<<<<< HEAD
=======
    # Configure the actual logging sinks
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
    configure_logging(config)

    logger.info("DynEL logging configured. Debug mode: {}. Context level: {}", config.DEBUG_MODE, config.CUSTOM_CONTEXT_LEVEL.value)

<<<<<<< HEAD
=======
    # Example of using handle_exception
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
    def example_function_one():
        try:
            x = 1 / 0
        except ZeroDivisionError as e:
            handle_exception(config, e)

    def example_function_two():
        try:
<<<<<<< HEAD
            my_dict: dict = {} # Python 3.9+
            _ = my_dict["non_existent_key"]
        except KeyError as e:
=======
            my_dict = {}
            _ = my_dict["non_existent_key"]
        except KeyError as e:
            # Override context level for this specific call if needed, though not standard API
            # Forcing a different config for a single call is not directly supported by handle_exception
            # It always uses the passed 'config' object.
            # If different behavior is needed, a different 'config' object would be passed.
>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
            handle_exception(config, e)

    logger.info("Running example functions to demonstrate DynEL.")
    example_function_one()
    example_function_two()

<<<<<<< HEAD
=======
    # Example of module_exception_handler
    # Create a dummy module for demonstration
    class TestModule:
        def func_a(self):
            return 1 + "a" # TypeError

        def func_b(self):
            return "This works"

    test_mod = TestModule()
    # Note: module_exception_handler expects a module object.
    # To demonstrate with a class instance's methods, one would typically wrap them individually
    # or adapt module_exception_handler. For simplicity, this demo won't fully run this part.
    # module_exception_handler(config, test_mod) # This would not work as expected for class methods

    # To test module_exception_handler properly, you'd have a separate .py file:
    # my_test_module.py:
    # def module_func1():
    #     raise ValueError("Error in module_func1")
    #
    # In this script:
    # import my_test_module
    # module_exception_handler(config, my_test_module)
    # my_test_module.module_func1()

>>>>>>> 8e85544daf4c61d4cdb6c7bdde8eb4fcf00a8ecd
    logger.info("DynEL demonstration finished.")
