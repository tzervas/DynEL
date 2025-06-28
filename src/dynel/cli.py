import argparse
from typing import Any, Dict

# Assuming DynelConfig, configure_logging, handle_exception will be imported
# from their new locations.
# This creates a potential circular dependency if cli.py directly imports from other
# dynel modules that might also want to import cli.py (though unlikely for cli.py).
# For now, direct imports are fine.
from .config import DynelConfig
from .logging_utils import configure_logging
from .exception_handling import handle_exception
# logger will be used from loguru, configured by configure_logging
from loguru import logger


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
    :rtype: Dict[str, Any]
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
        # dest='debug', # Not needed if action is store_true and default is False
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
        # Using print here as logger might not be configured yet, or for CLI feedback.
        # Or, ensure logger is configured before this print.
        # The original code used print.
        print(f"Loaded exception configuration. Debug mode: {config.DEBUG_MODE}")
    except FileNotFoundError:
        print("No DynEL configuration file found. Using default/CLI settings.")
    except ValueError as e:
        print(f"Error loading DynEL configuration: {e}. Using default/CLI settings.")
    except Exception as e:
        print(f"Unexpected error loading DynEL configuration ({type(e).__name__}): {e}. Using default/CLI settings.")

    configure_logging(config) # This sets up Loguru

    logger.info("DynEL logging configured. Debug mode: {}. Context level: {}", config.DEBUG_MODE, config.CUSTOM_CONTEXT_LEVEL.value)

    def example_function_one():
        try:
            x = 1 / 0
        except ZeroDivisionError as e:
            handle_exception(config, e)

    def example_function_two():
        try:
            my_dict: Dict[str, int] = {} # Added type hint for clarity
            _ = my_dict["non_existent_key"]
        except KeyError as e:
            handle_exception(config, e)

    logger.info("Running example functions to demonstrate DynEL.")
    example_function_one()
    example_function_two()

    logger.info("DynEL demonstration finished.")
