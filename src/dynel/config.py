import importlib
import json
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union # Keep Dict, List, Optional, Type, Union for <3.9 compatibility

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
    """Configuration class responsible for managing Dynel's logging settings.

    Attributes:
        CONTEXT_LEVEL_MAP (dict): Maps context level strings to ContextLevel Enum.
        CUSTOM_CONTEXT_LEVEL (ContextLevel): Specifies the context level.
        DEBUG_MODE (bool): Indicates if the logger is in debug mode.
        FORMATTING_ENABLED (bool): Indicates if special formatting is enabled.
        EXCEPTION_CONFIG (dict): Maps function names to their exception-handling configurations.

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
        self.DEBUG_MODE = debug
        self.FORMATTING_ENABLED = formatting
        self.PANIC_MODE = panic_mode
        self.EXCEPTION_CONFIG: Dict[str, Dict[str, Any]] = {}

    def load_exception_config(self, filename_prefix: str = "dynel_config", supported_extensions: Optional[List[str]] = None) -> None:
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

        config_file_found: Optional[Path] = None
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
                    # This case should ideally not be reached
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
                except Exception as e: # Catch any other unexpected error during exception loading
                    logger.error(f"Unexpected error loading exception '{exception_str}' for '{key}': {e}. Skipping.")


            parsed_exception_config[key] = {
                'exceptions': exception_classes,
                'custom_message': str(value.get('custom_message', '')), # Ensure string
                'tags': [str(tag) for tag in value.get('tags', []) if isinstance(tag, (str, int, float))] # Ensure tags are strings
            }
        self.EXCEPTION_CONFIG = parsed_exception_config
