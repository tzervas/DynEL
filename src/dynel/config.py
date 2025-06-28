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
    :ivar LOG_FORMAT: The primary log format string for general logging.
    :vartype LOG_FORMAT: str
    :ivar AUX_LOG_FORMAT: The log format string for auxiliary logs (e.g., specific error files).
                         Defaults to a simpler format if not specified.
    :vartype AUX_LOG_FORMAT: str
    """
    DEFAULT_LOG_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    DEFAULT_AUX_LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | Extra: {extra}"


    def __init__(self, context_level: str = 'min', debug: bool = False, formatting: bool = True, panic_mode: bool = False, log_format: Optional[str] = None, aux_log_format: Optional[str] = None):
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
        self.LOG_FORMAT = log_format if log_format is not None else self.DEFAULT_LOG_FORMAT
        self.AUX_LOG_FORMAT = aux_log_format if aux_log_format is not None else self.DEFAULT_AUX_LOG_FORMAT
        self.EXCEPTION_CONFIG: Dict[str, Dict[str, Any]] = {}

    def load_exception_config(self, filename_prefix: str = "dynel_config", supported_extensions: Optional[List[str]] = None) -> None:
        """
        Loads exception handling configurations from a file.
        Also loads 'LOG_FORMAT' and 'AUX_LOG_FORMAT' if present at the root of the config file.
        """
        if supported_extensions is None:
            supported_extensions = ["json", "yaml", "yml", "toml"]

        config_file_found = self._find_config_file(filename_prefix, supported_extensions)
        raw_config = self._load_config_file(config_file_found)
        self._validate_config_dict(raw_config, config_file_found)

        self.DEBUG_MODE = raw_config.get("debug_mode", self.DEBUG_MODE)
        # Load log formats from config file if they exist, otherwise keep current (default or constructor-set)
        self.LOG_FORMAT = raw_config.get("LOG_FORMAT", self.LOG_FORMAT)
        self.AUX_LOG_FORMAT = raw_config.get("AUX_LOG_FORMAT", self.AUX_LOG_FORMAT)

        self.EXCEPTION_CONFIG = self._parse_exception_config(raw_config)

    def _find_config_file(self, filename_prefix: str, supported_extensions: List[str]) -> Path:
        for ext in supported_extensions:
            config_file = Path(f"{filename_prefix}.{ext}")
            if config_file.exists():
                return config_file
        raise FileNotFoundError(f"No matching configuration file found for {filename_prefix} with extensions {supported_extensions}")

    def _load_config_file(self, config_file: Path) -> Any:
        extension = config_file.suffix[1:]
        try:
            with config_file.open(mode="r") as f:
                if extension == 'json':
                    return json.load(f)
                elif extension in ['yaml', 'yml']:
                    return yaml.safe_load(f)
                elif extension == 'toml':
                    return toml.load(f)
                else:
                    logger.error(f"Unsupported configuration file format encountered: {extension}")
                    raise ValueError(f"Unsupported configuration file format: {extension}")
        except (json.JSONDecodeError, yaml.YAMLError, toml.TomlDecodeError) as e:
            logger.error(f"Error parsing DynEL configuration file '{config_file}': {e}")
            raise ValueError(f"Failed to parse DynEL configuration file '{config_file}': {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error reading DynEL configuration file '{config_file}': {e}")
            raise ValueError(f"Unexpected error reading DynEL configuration file '{config_file}': {e}") from e

    def _validate_config_dict(self, raw_config: Any, config_file: Path) -> None:
        if not isinstance(raw_config, dict):
            logger.error(f"Invalid DynEL configuration file '{config_file}': Expected a dictionary (object/map) at the root, got {type(raw_config).__name__}.")
            raise ValueError(f"Invalid DynEL configuration file '{config_file}': Root of configuration must be a dictionary.")

    def _parse_exception_config(self, raw_config: dict) -> dict:
        parsed_exception_config: dict[str, dict[str, Any]] = {}
        for key, value in raw_config.items():
            if key == "debug_mode":
                continue
            if not isinstance(value, dict):
                logger.warning(f"Configuration for '{key}' is not a dictionary. Skipping.")
                continue
            exception_classes = self._load_exception_classes(key, value.get('exceptions', []))
            # Parse behaviors
            behaviors_config = value.get('behaviors', {})
            parsed_behaviors = self._parse_behaviors(key, behaviors_config)

            parsed_exception_config[key] = {
                'exceptions': exception_classes,
                'custom_message': str(value.get('custom_message', '')),
                'tags': [str(tag) for tag in value.get('tags', []) if isinstance(tag, (str, int, float))],
                'behaviors': parsed_behaviors
            }
        return parsed_exception_config

    def _parse_behaviors(self, func_key: str, behaviors_config: Any) -> Dict[str, Dict[str, Any]]:
        """
        Parses the 'behaviors' sub-configuration for a given function.
        Validates the structure and specific behavior definitions.
        """
        if not isinstance(behaviors_config, dict):
            logger.warning(f"Behaviors config for '{func_key}' is not a dictionary. Skipping behaviors.")
            return {}

        parsed_behaviors: Dict[str, Dict[str, Any]] = {}
        for behavior_key, behavior_def in behaviors_config.items():
            if not isinstance(behavior_def, dict):
                logger.warning(f"Definition for behavior key '{behavior_key}' under function '{func_key}' is not a dictionary. Skipping this behavior entry.")
                continue

            current_behavior_actions: Dict[str, Any] = {}
            # Validate 'add_metadata'
            if 'add_metadata' in behavior_def:
                metadata = behavior_def['add_metadata']
                if isinstance(metadata, dict):
                    current_behavior_actions['add_metadata'] = metadata
                else:
                    logger.warning(f"'add_metadata' for behavior '{behavior_key}' under function '{func_key}' is not a dictionary. Skipping 'add_metadata'.")

            # Validate 'log_to_specific_file'
            if 'log_to_specific_file' in behavior_def:
                log_file = behavior_def['log_to_specific_file']
                if isinstance(log_file, str) and log_file.strip():
                    current_behavior_actions['log_to_specific_file'] = log_file.strip()
                else:
                    logger.warning(f"'log_to_specific_file' for behavior '{behavior_key}' under function '{func_key}' is not a valid string. Skipping 'log_to_specific_file'.")

            # (Future: Add validation for 'custom_callback' or other behaviors here)

            if current_behavior_actions:
                # behavior_key here can be an exception name string (e.g., "ValueError") or "default"
                parsed_behaviors[behavior_key] = current_behavior_actions
            else:
                logger.info(f"No valid actions found for behavior key '{behavior_key}' under function '{func_key}'.")

        return parsed_behaviors

    def _load_exception_classes(self, key: str, exceptions: list) -> list:
        exception_classes: list[Type[BaseException]] = []
        for exception_str in exceptions:
            if not isinstance(exception_str, str):
                logger.warning(f"Invalid exception name type for '{key}': {exception_str}. Must be a string. Skipping.")
                continue
            exception_class_val: Any = None
            try:
                exception_class_val = getattr(__builtins__, exception_str, None)  # type: ignore
                if not (exception_class_val and isinstance(exception_class_val, type) and issubclass(exception_class_val, BaseException)):
                    if '.' in exception_str:
                        module_name, class_name = exception_str.rsplit('.', 1)
                        module = importlib.import_module(module_name)
                        exception_class_val = getattr(module, class_name)
                if not (isinstance(exception_class_val, type) and issubclass(exception_class_val, BaseException)):
                    raise TypeError(f"'{exception_str}' is not a BaseException subclass.")
            except (AttributeError, ImportError, ValueError, TypeError) as e:
                logger.warning(f"Could not load or validate exception '{exception_str}' for '{key}': {e}. Skipping.")
                continue
            except Exception as e:
                logger.error(f"Unexpected error loading exception '{exception_str}' for '{key}': {e}. Skipping.")
                continue
            exception_classes.append(exception_class_val)
        return exception_classes
