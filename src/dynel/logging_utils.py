from loguru import logger
from .config import DynelConfig # Assuming DynelConfig is in config.py


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
        catch=True # Catch errors within the logger itself
    )
    logger.add(
        sink="dynel.json",
        serialize=True,
        level="DEBUG" if config.DEBUG_MODE else "INFO",
        rotation="10 MB",
        catch=True # Catch errors within the logger itself
    )


def global_exception_handler(config: DynelConfig, message: str) -> None:
    """
    A global exception handler utility function.

    Logs a generic message indicating an unhandled exception using Loguru's
    exception logging, which includes traceback information. This function
    is not automatically wired up by DynEL (e.g., to ``sys.excepthook``);
    it's provided as a utility if such a global fallback is needed.

    :param config: The DynelConfig instance. While passed, its direct attributes
                   are not explicitly used in this handler's current version,
                   as Loguru's logger is used directly. It's included for API
                   consistency and potential future enhancements.
    :type config: DynelConfig
    :param message: A descriptive message to include with the logged exception.
    :type message: str
    """
    logger.exception("An unhandled exception has occurred: {}", message)
