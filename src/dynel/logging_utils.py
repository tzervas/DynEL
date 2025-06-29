from loguru import logger
from .config import DynelConfig


def configure_logging(config: DynelConfig) -> None:
    """
    Configures Loguru's logging settings based on the provided DynelConfig.

    Removes any existing Loguru handlers and sets up new ones:
    - Rotating file sink for text logs (dynel.log).
    - Rotating file sink for JSON logs (dynel.json).

    Log level is set to "DEBUG" if config.DEBUG_MODE is True, otherwise "INFO".
    If config.FORMATTING_ENABLED is False, disables color tags in log output.
    """
    logger.remove()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    if not config.formatting:
        # Remove color tags if formatting is disabled
        log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"

    logger.add(
        sink="dynel.log",
        level="DEBUG" if config.debug else "INFO",
        format=log_format,
        rotation="10 MB",
        catch=True,
        enqueue=True  # Safer for multi-threaded/multi-process
    )
    logger.add(
        sink="dynel.json",
        serialize=True,
        level="DEBUG" if config.debug else "INFO",
        rotation="10 MB",
        catch=True,
        enqueue=True
    )


def global_exception_handler(config: DynelConfig, message: str) -> None:
    """
    Logs a generic message indicating an unhandled exception using Loguru's exception logging, including traceback information.
    If PANIC_MODE is enabled, exits the program after logging.
    """
    logger.exception("An unhandled exception has occurred: {}", message)
    if getattr(config, 'PANIC_MODE', False):
        import sys
        sys.exit(1)
