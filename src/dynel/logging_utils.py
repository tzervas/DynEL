from loguru import logger
from .config import DynelConfig
from typing import List

_tracked_handler_ids: List[int] = []

def configure_logging(config: DynelConfig, log_file: str = "dynel.log", json_file: str = "dynel.json") -> None:
    """
    Configures Loguru's logging settings based on the provided DynelConfig.

    Removes previously tracked Loguru handlers and sets up new ones:
    - Rotating file sink for text logs (dynel.log).
    - Rotating file sink for JSON logs (dynel.json).

    Log level is set to "DEBUG" if config.DEBUG_MODE is True, otherwise "INFO".
    If config.FORMATTING_ENABLED is False, disables color tags in log output.
    """
    global _tracked_handler_ids
    
    # Remove previously tracked handlers
    for handler_id in _tracked_handler_ids:
        try:
            logger.remove(handler_id)
        except ValueError:
            # Handler was already removed or doesn't exist
            pass
    _tracked_handler_ids.clear()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level> | {extra}"
    )
    if not config.FORMATTING_ENABLED:
        # Remove color tags if formatting is disabled
        log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message} | {extra}"

    # Add and track new handlers
    handler_id = logger.add(
        sink=log_file,
        level="DEBUG" if config.DEBUG_MODE else "INFO",
        format=log_format,
        rotation="10 MB",
        catch=True,
        enqueue=True  # Safer for multi-threaded/multi-process
    )
    _tracked_handler_ids.append(handler_id)

    handler_id = logger.add(
        sink=json_file,
        serialize=True,
        level="DEBUG" if config.DEBUG_MODE else "INFO",
        rotation="10 MB",
        catch=True,
        enqueue=True
    )
    _tracked_handler_ids.append(handler_id)


def global_exception_handler(config: DynelConfig, message: str) -> None:
    """
    Logs a generic message indicating an unhandled exception using Loguru's exception logging, including traceback information.
    If PANIC_MODE is enabled, exits the program after logging.
    """
    logger.exception("An unhandled exception has occurred: {}", message)
    if getattr(config, 'PANIC_MODE', False):
        import sys
        sys.exit(1)
