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

    log_message = f"Exception caught in {func_name if config.FORMATTING_ENABLED else func_name}"
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

    if final_tags:
        custom_context_dict["tags"] = final_tags

    bound_logger = logger.bind(**cast(CustomContext, custom_context_dict))
    bound_logger.exception(log_message, exception=error)


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

            def _onerror_handler(exc_or_result: Union[Exception, Any]):
                if isinstance(exc_or_result, Exception):
                    handle_exception(config, exc_or_result)
                    # Ensure the original exception is re-raised so logger.catch propagates it,
                    # or if the user wants to handle it further up the call stack.
                    raise exc_or_result
                else:
                    # This was a successful function call, return its result
                    return exc_or_result

            # Apply the logger.catch decorator with the custom onerror handler
            # Reraise=True is important if the exception should propagate after logging.
            # If handle_exception might panic (sys.exit), then reraise might not matter for that path.
            # However, if not panicking, reraising allows higher-level handlers or finally blocks to execute.
            wrapped_function = logger.catch(onerror=_onerror_handler, reraise=True)(obj)
            setattr(module, name, wrapped_function)
            if config.DEBUG_MODE:
                # Using standard logging here for debug messages from this utility itself,
                # to avoid complex dependencies if loguru isn't fully set up when this runs,
                # or to separate utility logs from application logs.
                # However, the original used `logging.debug` which might not be configured.
                # If loguru is the standard, `logger.debug` would be more consistent.
                # Let's assume standard logging for this specific debug line for now.
                # If issues arise, this can be switched to loguru's logger.
                # Reconsidering: The original code had `logging.debug`. This means the `logging` module.
                # It's better to be consistent. If Loguru is the primary logger, use it.
                # If `config.DEBUG_MODE` implies Loguru is set to DEBUG, then `logger.debug` is fine.
                module_name_for_log = getattr(module, '__name__', 'UnknownModule')
                logger.debug("Wrapped function: %s in module %s", name, module_name_for_log)
