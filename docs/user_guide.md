# DynEL User Guide

Welcome to the DynEL User Guide! This guide will help you understand how to use the DynEL (Dynamic Error Logging) module in your Python projects to enhance your error logging and handling capabilities.

## Table of Contents

1.  [Introduction](#introduction)
2.  [Installation](#installation)
3.  [Core Concepts](#core-concepts)
    *   [DynelConfig](#dynelconfig)
    *   [Context Levels](#context-levels)
    *   [Exception Configuration](#exception-configuration)
4.  [Basic Usage](#basic-usage)
    *   [Initialization & Logging Setup](#initialization--logging-setup)
    *   [Manual Exception Handling](#manual-exception-handling)
5.  [Configuration File](#configuration-file)
    *   [Structure and Examples](#structure-and-examples)
    *   [Loading Configuration](#loading-configuration)
6.  [Automatic Module-Level Exception Handling](#automatic-module-level-exception-handling)
7.  [Command-Line Arguments](#command-line-arguments)
8.  [Log Output](#log-output)
    *   [Text Logs (`dynel.log`)](#text-logs-dynellog)
    *   [JSON Logs (`dynel.json`)](#json-logs-dyneljson)
9.  [Advanced Usage & Best Practices](#advanced-usage--best-practices)

## 1. Introduction

DynEL is a Python module designed to make error logging more dynamic, configurable, and informative. It uses the powerful [Loguru](https://github.com/Delgan/loguru) library as its backend. With DynEL, you can:

-   Easily set up structured (JSON) and human-readable text logs.
-   Configure how exceptions are logged on a per-function basis with custom messages and tags.
-   Control the amount of context (like local variables, system info) included in error logs.
-   Centralize your logging and error handling configuration.
-   Automatically wrap functions in entire modules for consistent error handling.

## 2. Installation

Please refer to the `README.md` in the main project directory for the most up-to-date installation instructions. Typically, it involves cloning the repository and using Poetry:

```bash
git clone https://github.com/tzervas/DynEL.git
cd DynEL
poetry install
```

## 3. Core Concepts

### DynelConfig

The `dynel.DynelConfig` class is the heart of DynEL's configuration. You create an instance of this class to specify how DynEL should behave. Key parameters include:

-   `context_level`: Controls the verbosity of context in logs ('min', 'med', 'det').
-   `debug`: Sets the logging level (DEBUG if true, INFO if false).
-   `formatting`: Enables/disables rich formatting tags in text logs.
-   `panic_mode`: If true, DynEL will cause the program to exit after logging an exception.
-   `EXCEPTION_CONFIG`: A dictionary (usually loaded from a file) that defines custom handling for specific exceptions in specific functions.

### Context Levels

Defined by the `dynel.ContextLevel` enum:

-   **`MINIMAL`**: Basic exception info and a timestamp.
-   **`MEDIUM`**: Adds local variables from the frame where the error was handled.
-   **`DETAILED`**: Adds system details (memory, CPU, environment variables) to medium-level context. Use with caution if environment variables contain sensitive data.

### Exception Configuration

This allows you to define custom messages and tags for specific exceptions within named functions. This configuration is typically loaded from an external file into `DynelConfig.EXCEPTION_CONFIG`.

## 4. Basic Usage

### Initialization & Logging Setup

```python
from dynel import DynelConfig, configure_logging, handle_exception

# 1. Create a configuration object
# Defaults: context_level='min', debug=False, formatting=True, panic_mode=False
config = DynelConfig(context_level='med', debug=True)

# 2. (Optional) Load external configuration for per-function settings
try:
    config.load_exception_config() # Looks for dynel_config.json/yaml/toml
    print(f"DynEL config file loaded. Debug mode from file: {config.DEBUG_MODE}")
except FileNotFoundError:
    print("No DynEL config file found, using initial settings.")
except ValueError as e:
    print(f"Error loading DynEL config: {e}")

# 3. Apply the configuration to set up Loguru logging
configure_logging(config)

# Now DynEL is ready to log.
print("DynEL initialized and logging configured.")
```

### Manual Exception Handling

Use `dynel.handle_exception` within your `try...except` blocks:

```python
def process_data(data_item):
    try:
        # Simulate some processing
        if not isinstance(data_item, dict):
            raise TypeError("Data item must be a dictionary.")
        value = data_item["value"] / data_item["factor"]
        print(f"Processed value: {value}")
        return value
    except Exception as e: # Catch a broad exception
        # Let DynEL handle the logging
        handle_exception(config, e)
        # You can choose to re-raise, return a default, or exit based on your app's logic
        # e.g., raise if you want the error to propagate further after logging
```

## 5. Configuration File

DynEL can load settings from `dynel_config.json`, `dynel_config.yaml` (or `.yml`), or `dynel_config.toml`.

### Structure and Examples

**`dynel_config.yaml` example:**
```yaml
debug_mode: true # Overrides debug setting from DynelConfig() constructor

# Function-specific configurations
# Key is the function name as it appears in the stack trace (usually module.func_name or just func_name)
"process_data":
  exceptions:
    - "TypeError"      # Built-in exception name as string
    - "ZeroDivisionError"
  custom_message: "Error during data processing operation."
  tags: ["data_pipeline", "critical_process"]

"another_module.risky_call":
  exceptions:
    - "requests.exceptions.Timeout" # Fully qualified for external libraries
  custom_message: "API call to external service timed out."
  tags: ["api_call", "network_issue"]
```

### Loading Configuration

Call the `load_exception_config()` method on your `DynelConfig` instance:

```python
config = DynelConfig()
try:
    config.load_exception_config() # Loads "dynel_config.*"
    # config.load_exception_config("my_custom_prefix") # Loads "my_custom_prefix.*"
except FileNotFoundError:
    # Handle missing config file if necessary
    pass
```
Settings from the file (like `debug_mode` or `EXCEPTION_CONFIG` entries) will update the `config` object.

## 6. Automatic Module-Level Exception Handling

To apply DynEL's error handling to all functions in a module without manual `try...except` blocks:

```python
import your_target_module
from dynel import module_exception_handler

# Assuming 'config' is your initialized and configured DynelConfig object
module_exception_handler(config, your_target_module)

# Now, unhandled exceptions in functions within 'your_target_module'
# will be automatically caught and processed by DynEL.
try:
    your_target_module.some_function_that_might_fail()
except Exception:
    # The exception will be logged by DynEL and then re-raised here
    # (unless panic_mode is on and sys.exit occurs).
    print("Exception was re-raised after DynEL handling, as expected.")
```
**Note**: This wraps functions directly within the module. It does not recursively wrap functions in imported submodules or methods within classes by default.

## 7. Command-Line Arguments

If your script uses `dynel.parse_command_line_args()`, some settings can be controlled via CLI:

```python
# In your main script:
# from dynel import parse_command_line_args, DynelConfig, configure_logging
# if __name__ == "__main__":
#     cli_args = parse_command_line_args()
#     config = DynelConfig(
#         context_level=cli_args['context_level'],
#         debug=cli_args['debug'],
#         formatting=cli_args['formatting']
#     )
#     # ... load file config, then configure_logging(config) ...
```
Then run: `python your_script.py --debug --context-level det`

Available arguments:
-   `--context-level [min|med|det]`: Sets context verbosity.
-   `--debug`: Activates debug logging mode.
-   `--no-formatting`: Disables rich text formatting in console/text logs.

## 8. Log Output

By default, `configure_logging` sets up two log files in the current directory:

### Text Logs (`dynel.log`)
Human-readable, line-based logs. Includes timestamps, levels, function origin, messages, and any extra context. Rotates at 10MB.

Example line:
`2023-10-27 10:00:00 | ERROR | my_module:my_function:42 - Exception caught in my_function - Custom Message: Something specific failed | {'timestamp': '...', 'tags': ['critical']}`

### JSON Logs (`dynel.json`)
Each log entry is a separate JSON object, suitable for machine parsing and log management systems. Includes detailed structured information like `record.time`, `record.level`, `record.message`, `record.extra` (with DynEL's context), and `record.exception` (with type, value, and traceback string). Rotates at 10MB.

## 9. Advanced Usage & Best Practices

-   **Sensitive Information**: Be cautious with `DETAILED` context level or if function-specific local variables might contain sensitive data. DynEL currently stringifies all captured local variables.
-   **Performance**: Rich context logging adds overhead. Profile if performance is critical.
-   **Custom Loguru Sinks**: You can add more Loguru sinks after `configure_logging(config)` if needed.
-   **Framework Integration**: For web frameworks (Flask, Django, etc.), integrate DynEL by using its handlers in the framework's error handling hooks or by configuring Loguru to intercept standard logging.
-   **Token Economy for AI**: When defining custom messages, tags, and choosing context levels, consider how this information can be most effectively used by AI models for analysis or debugging, aiming for a balance of conciseness and completeness.

This guide should help you get started with DynEL. For more details on specific functions or classes, refer to the API documentation (docstrings) or the `docs/developer_guide.md`.
