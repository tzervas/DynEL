import inspect
import os
import sys
from datetime import datetime, timezone
from typing import Any, Union, cast

from loguru import logger

from .config import DynelConfig, ContextLevel, CustomContext


def handle_exception(config: DynelConfig, error: Exception) -> None:
    """
    Handles and logs an exception based on DynEL's configuration.

    This is the core exception processing function. It gathers context based on
    the configured :class:`ContextLevel`, checks for function-specific configurations
    (like custom messages and tags) from ``config.EXCEPTION_CONFIG``, and logs
    the exception using Loguru.

    If ``config.PANIC_MODE`` is true, this function will call ``sys.exit(1)``
    after logging the exception.

    The function name, where the exception is considered to have occurred for
    configuration lookup, is determined by inspecting the call stack (specifically,
    the caller of this ``handle_exception`` function).

    :param config: The DynelConfig instance containing all operational settings.
    :type config: DynelConfig
    :param error: The exception instance that was caught and needs to be handled.
    :type error: Exception
    """
    func_name = inspect.stack()[1][3]
    # Use function_config for all function-specific settings
    function_config = config.EXCEPTION_CONFIG.get(func_name)
    context_level = config.CUSTOM_CONTEXT_LEVEL

    custom_context_dict: dict[str, Any] = {"timestamp": str(datetime.now(timezone.utc).isoformat())}

    if context_level in [ContextLevel.MEDIUM, ContextLevel.DETAILED]:
        caller_frame_info = inspect.stack()[1]
        caller_frame = caller_frame_info[0]
        local_vars = caller_frame.f_locals if caller_frame else None
        if local_vars:
            try:
                custom_context_dict["local_vars"] = str(local_vars)
            except Exception:
                custom_context_dict["local_vars"] = "Error converting local_vars to string"
        else:
            custom_context_dict["local_vars"] = "Local variables information unavailable"

    if context_level == ContextLevel.DETAILED:
        detailed_context: dict[str, Any] = {}
        try:
            detailed_context["free_memory"] = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES")
            detailed_context["cpu_count"] = os.cpu_count()
        except (OSError, AttributeError):
            detailed_context["system_info_error"] = "Could not retrieve some system info (memory/CPU)"
        try:
            detailed_context["env_details"] = dict(os.environ)
        except Exception:
            detailed_context["env_details_error"] = "Could not retrieve environment variables"
        custom_context_dict |= detailed_context

    log_message = f"Exception caught in {func_name}"
    final_custom_message = None
    final_tags = None
    specific_behaviors = None
    default_behaviors = {} # Initialize to empty dict

    if function_config:
        # Default behaviors for the function, if any
        default_behaviors = function_config.get('behaviors', {}).get('default', {})

        for configured_exc_type in function_config.get('exceptions', []):
            if isinstance(error, configured_exc_type):
                final_custom_message = function_config.get('custom_message')
                final_tags = function_config.get('tags')

                # Check for behaviors specific to this exception type
                exception_type_name = type(error).__name__ # More robust: error.__class__.__name__
                # Also consider fully qualified name if needed for config: f"{error.__class__.__module__}.{error.__class__.__name__}"
                # For now, simple name, assuming config uses simple names for specific overrides
                specific_behaviors = function_config.get('behaviors', {}).get(exception_type_name, {})

                if final_custom_message:
                    log_message += f" - Custom Message: {final_custom_message}"
                break # Found the matching configured exception type

    # Apply default behaviors first, then override with specific behaviors
    # Ensure specific_behaviors is a dict if None
    applied_behaviors: dict[str, Any] = {**default_behaviors, **(specific_behaviors if specific_behaviors is not None else {})}

    if final_tags:
        custom_context_dict["tags"] = final_tags

    # Implement 'add_metadata' behavior
    if 'add_metadata' in applied_behaviors:
        # Ensure metadata is a dict, though validation should happen in config parsing
        metadata_to_add = applied_behaviors['add_metadata']
        if isinstance(metadata_to_add, dict):
            custom_context_dict |= metadata_to_add
        else:
            logger.warning(f"Invalid 'add_metadata' format for {func_name}. Expected dict, got {type(metadata_to_add)}. Skipping.")

    # Bind context (including added metadata) to the logger
    bound_logger = logger.bind(**cast(CustomContext, custom_context_dict))

    # Log the main exception message
    bound_logger.exception(log_message, exception=error)

    # Implement 'log_to_specific_file' behavior
    if 'log_to_specific_file' in applied_behaviors:
        target_file = applied_behaviors['log_to_specific_file']
        if isinstance(target_file, str):
            handler_id = None
            try:
                # Use a format that matches the main JSON log for consistency if possible, or a simpler one
                # For PoC, let's make it clear this is an auxiliary log.
                # Ensure the sink can handle concurrent writes if this function is called from multiple threads.
                # Loguru handlers are thread-safe by default.
                # We use a simple format here; it could be made configurable.
                # The level should be the same as the main exception log, or configurable.
                # Using enqueue=True for safety if multiple errors hit this quickly.
                log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | Extra: {extra}"
                if not config.FORMATTING_ENABLED:
                     log_format = log_format.replace("<level>", "").replace("</level>", "") # basic color removal

                handler_id = logger.add(
                    target_file,
                    level="ERROR", # Or config.DEBUG_MODE related level
                    format=log_format,
                    rotation="5 MB", # Smaller rotation for specific error logs
                    catch=True, # Catch errors within this specific logger too
                    serialize=True, # Keep it structured
                    enqueue=True
                )
                # Log again, this time it will go to the specific file as well as existing handlers.
                # We re-bind here to ensure the context is included in this specific log too.
                # Alternatively, the bound_logger from above would also send to this new handler.
                logger.bind(**cast(CustomContext, custom_context_dict)).exception(
                    f"[Mirrored to {target_file}] {log_message}",
                    exception=error
                )
                logger.info(f"Logged details for error in {func_name} to {target_file}")
            except Exception as e_handler:
                logger.error(f"Failed to log to specific file {target_file} for {func_name}: {e_handler}")
            finally:
                if handler_id is not None:
                    logger.remove(handler_id)
        else:
            logger.warning(f"Invalid 'log_to_specific_file' path for {func_name}. Expected string, got {type(target_file)}. Skipping.")


    if config.PANIC_MODE:
        logger.critical(f"PANIC MODE ENABLED: Exiting after handling exception in {func_name}.")
        sys.exit(1)


def module_exception_handler(config: DynelConfig, module: Any) -> None:
    """
    Attaches DynEL's exception handling to all functions within a given module.

    It iterates over all members of the `module` (functions and classes) and
    wraps any functions or methods found with Loguru's ``@logger.catch``,
    using a custom ``onerror`` handler. This custom handler ensures that
    :func:`handle_exception` is invoked for exceptions.

    Original functions and methods in the module/classes are replaced by their
    wrapped versions (in-place modification).

    .. warning::
        This function modifies the provided module and its classes by replacing
        functions/methods with wrapped versions.
        - It attempts to handle regular instance methods, static methods, and class methods.
        - Complex descriptors (like `@property` getters/setters if they raise externally)
          or methods heavily modified by other decorators might not be wrapped correctly
          or might behave unexpectedly. The PoC focuses on typical method types.
        - The name used for configuration lookup in `handle_exception` will be the
          method's name (e.g., `my_method`). If different configurations are needed for
          methods with the same name in different classes, the config keys would need
          to be more specific (e.g., `MyClass.my_method`), which is not currently
          supported by `handle_exception`'s `inspect.stack()[1][3]` logic without changes.

    :param config: The DynelConfig instance to use for the exception handlers.
    :type config: DynelConfig
    :param module: The module object whose functions/methods are to be wrapped.
    :type module: Any
    """
    module_name_for_log = getattr(module, '__name__', 'UnknownModule')

    def _onerror_handler_factory(cfg: DynelConfig):
        # Factory to ensure 'config' is correctly scoped for the onerror handler
        def _onerror_handler(exc_or_result: Union[Exception, Any]):
            if isinstance(exc_or_result, Exception):
                handle_exception(cfg, exc_or_result) # Use cfg from factory scope
                raise exc_or_result
            else:
                return exc_or_result
        return _onerror_handler

    # Get the actual onerror handler instance for this module_exception_handler call
    actual_onerror_handler = _onerror_handler_factory(config)

    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj): # Handles regular functions and staticmethods if not yet bound
            wrapped_member = logger.catch(onerror=actual_onerror_handler, reraise=True)(obj)
            setattr(module, name, wrapped_member)
            if config.DEBUG_MODE:
                logger.debug("Wrapped function/staticmethod: %s in module %s", name, module_name_for_log)

        elif inspect.isclass(obj):
            # Iterate through members of the class
            for class_attr_name, class_attr_value in inspect.getmembers(obj):
                # Check for functions (potential instance methods, class methods, static methods)
                # inspect.isfunction: for regular methods, staticmethods (if not yet bound by decorator)
                # inspect.ismethod: for classmethods (already bound by @classmethod)
                # We need to be careful not to double-wrap or misinterpret.
                # logger.catch should work on callables.

                if callable(class_attr_value):
                    # Distinguish between staticmethod, classmethod, and regular instance method
                    # For staticmethod and classmethod, they might appear as functions if accessed via __dict__
                    # or as methods if accessed via getattr(obj, class_attr_name) after class creation.
                    # We are iterating via inspect.getmembers(obj) where obj is the class itself.

                    original_member = class_attr_value

                    # If it's a staticmethod or classmethod, it's already a descriptor.
                    # We need to wrap the underlying function if possible.
                    if isinstance(original_member, (staticmethod, classmethod)):
                        # The actual function is in __func__
                        actual_func = original_member.__func__
                        wrapped_func = logger.catch(onerror=actual_onerror_handler, reraise=True)(actual_func)
                        # Re-apply the original decorator type
                        if isinstance(original_member, staticmethod):
                            wrapped_member = staticmethod(wrapped_func)
                        else: # classmethod
                            wrapped_member = classmethod(wrapped_func)
                    elif inspect.isfunction(original_member): # Regular function defined in class (becomes instance method)
                        wrapped_member = logger.catch(onerror=actual_onerror_handler, reraise=True)(original_member)
                    else:
                        # Not a function, staticmethod, or classmethod we can easily wrap (e.g. already bound method, other callable object)
                        # Could also be a C-implemented method, which inspect.isfunction might miss.
                        # For PoC, we'll skip these more complex cases.
                        if config.DEBUG_MODE:
                            logger.debug("Skipping non-standard callable: %s.%s of type %s", obj.__name__, class_attr_name, type(original_member).__name__)
                        continue

                    try:
                        setattr(obj, class_attr_name, wrapped_member)
                        if config.DEBUG_MODE:
                            logger.debug("Wrapped method: %s.%s in module %s", obj.__name__, class_attr_name, module_name_for_log)
                    except Exception as e: # Catch potential errors like trying to set on built-in types
                        if config.DEBUG_MODE:
                            logger.error("Failed to wrap method %s.%s: %s", obj.__name__, class_attr_name, e)
