# DynEL User Guide

Welcome to the DynEL User Guide! This guide will help you understand how to use the DynEL (Dynamic Error Logging) module in your Python projects to enhance your error logging and handling capabilities.

## Table of Contents

1.  [Introduction](#introduction)
2.  [Installation](#installation)
3.  [Basic Usage](#basic-usage)
    *   [Initializing DynEL](#initializing-dynel)
    *   [Configuring Logging](#configuring-logging)
    *   [Handling Exceptions](#handling-exceptions)
4.  [Configuration](#configuration)
    *   [Configuration File](#configuration-file)
    *   [DynelConfig Class](#dynelconfig-class)
    *   [Context Levels](#context-levels)
    *   [Function-Specific Configuration](#function-specific-configuration)
5.  [Automatic Module-Level Exception Handling](#automatic-module-level-exception-handling)
6.  [Command-Line Arguments](#command-line-arguments)
7.  [Log Output](#log-output)
    *   [Text Logs (`dynel.log`)](#text-logs-dynellog)
    *   [JSON Logs (`dynel.json`)](#json-logs-dyneljson)
8.  [Advanced Usage & Best Practices](#advanced-usage--best-practices) (To be expanded)

## 1. Introduction

DynEL is a Python module designed to make error logging more dynamic, configurable, and informative. It uses the powerful [Loguru](https://github.com/Delgan/loguru) library as its backend. With DynEL, you can:

-   Easily set up structured (JSON) and human-readable text logs.
-   Configure how exceptions are logged on a per-function basis.
-   Control the amount of context (like local variables, system info) included in error logs.
-   Centralize your logging and error handling configuration.

## 2. Installation

Please refer to the `README.md` in the main project directory for the most up-to-date installation instructions. Typically, it involves cloning the repository and using Poetry:

```bash
git clone https://github.com/tzervas/DynEL.git
cd DynEL
poetry install
```

## 3. Basic Usage

### Initializing DynEL

First, import the necessary components from DynEL:

```python
from dynel import DynelConfig, configure_logging, handle_exception
```

Create an instance of `DynelConfig`. This object will hold your logging preferences.

```python
# Initialize with default settings
config = DynelConfig()

# Or, customize at initialization
# For detailed context, debug mode on, and panic mode on:
config = DynelConfig(context_level='det', debug=True, panic_mode=True)
```

### Configuring Logging

Once you have a `DynelConfig` object, pass it to `configure_logging` to set up the Loguru sinks:

```python
configure_logging(config)
```
This will typically set up `dynel.log` (text) and `dynel.json` (JSON) log files in the current working directory.

### Handling Exceptions

To handle an exception with DynEL, call `handle_exception` from within an `except` block:

```python
def my_function(data):
    try:
        result = data['key'] / data['divisor']
        return result
    except Exception as e: # Catch any exception
        # Pass the config and the caught exception instance to DynEL
        handle_exception(config, e)
        # Optionally, re-raise the exception or handle it further
        # raise

# Example usage that might cause an error
my_function({"key": 10, "divisor": 0}) # Will cause ZeroDivisionError
my_function({"divisor": 2}) # Will cause KeyError
```
DynEL will then log the exception according to the settings in your `config` object.

## 4. Configuration

### Configuration File

DynEL can load its main configuration from external files. By default, it looks for:
- `dynel_config.json`
- `dynel_config.yaml` (or `.yml`)
- `dynel_config.toml`

in the current working directory. The first one it finds will be loaded when you call:

```python
config.load_exception_config()
# Or, specify a custom prefix:
# config.load_exception_config(filename_prefix="my_app_dynel_settings")
```

An example `dynel_config.yaml`:
```yaml
debug_mode: true # Overrides DynelConfig(debug=...) if loaded after

# Function-specific configurations
my_function:
  exceptions:
    - "ValueError" # Name of the exception class as a string
    - "ZeroDivisionError"
  custom_message: "Failed during critical calculation in my_function."
  tags: ["critical", "calculation"]

another_module.utility_func: # For functions in other modules
  exceptions:
    - "requests.exceptions.ConnectionError" # Fully qualified name for non-builtins
  custom_message: "Network issue calling utility."
  tags: ["network", "external_api"]
```

**Note on Exception Names:**
- For built-in exceptions (e.g., `ValueError`, `TypeError`), provide the name as a string.
- For exceptions from other modules (e.g., `requests.exceptions.ConnectionError`), provide the fully qualified string name.

### DynelConfig Class

The `DynelConfig` class is the primary way to control DynEL's behavior in code.

```python
from dynel import DynelConfig, ContextLevel

config = DynelConfig(
    context_level='med',  # 'min', 'med', or 'det' (or full names)
    debug=False,          # True for DEBUG log level, False for INFO
    formatting=True,      # Enable/disable special Loguru formatting tags
    panic_mode=False      # If True, sys.exit(1) after handling an exception
)

# Load external config which can override some of these settings
try:
    config.load_exception_config()
except FileNotFoundError:
    print("No DynEL config file found, using defaults.")
except ValueError as e:
    print(f"Error loading DynEL config: {e}")

# Then, apply this config to the logger
configure_logging(config)
```

### Context Levels

DynEL provides three levels of context detail for logged exceptions, set by `context_level` in `DynelConfig`:

-   **`ContextLevel.MINIMAL` ('min')**: Logs basic exception information and a timestamp.
-   **`ContextLevel.MEDIUM` ('med')**: Includes information from MINIMAL plus local variables from the frame where the exception was handled by DynEL (via `handle_exception`).
-   **`ContextLevel.DETAILED` ('det')**: Includes information from MEDIUM plus system details like free memory, CPU count, and environment variables (be cautious with sensitive data in environment variables).

### Function-Specific Configuration

Loaded via `config.load_exception_config()`, this allows you to define:
-   `exceptions`: A list of specific exception types (as strings) that this configuration applies to for the given function.
-   `custom_message`: A message that will be appended to the standard log entry if one of the listed exceptions occurs in that function.
-   `tags`: A list of string tags that will be added to the `extra` context of the log record, useful for filtering or categorization.

If an exception occurs in a function listed in `EXCEPTION_CONFIG` and the exception type matches one of those specified for that function, the `custom_message` and `tags` will be applied.

## 5. Automatic Module-Level Exception Handling

DynEL can automatically wrap all functions in a given module to use its exception handling. This is useful for instrumenting larger parts of your codebase without manually adding `try...except` blocks everywhere.

```python
import my_module_to_watch
from dynel import module_exception_handler, DynelConfig, configure_logging

config = DynelConfig(context_level='med')
config.load_exception_config() # Load any function-specific settings
configure_logging(config)

# Apply DynEL's handler to all functions in my_module_to_watch
module_exception_handler(config, my_module_to_watch)

# Now, any unhandled exceptions in functions directly within my_module_to_watch
# will be processed by DynEL's handle_exception.
my_module_to_watch.some_function_that_might_fail()
```

**Warning**: `module_exception_handler` modifies the module in-place by replacing functions with their wrapped versions. It currently only wraps functions defined directly in the module, not methods inside classes within the module.

## 6. Command-Line Arguments

If DynEL is initialized from a script that parses command-line arguments using `parse_command_line_args()` (like in its `if __name__ == "__main__:` block), you can override some settings:

-   `--context-level [min|med|det]`: Sets the context level.
-   `--debug`: Enables debug mode.
-   `--no-formatting`: Disables Loguru's rich text formatting tags.

Example:
`python your_script_using_dynel.py --context-level det --debug`

## 7. Log Output

When `configure_logging(config)` is called, DynEL sets up two log files by default:

### Text Logs (`dynel.log`)

-   Human-readable format.
-   Rotates when the file reaches 10 MB.
-   Example format:
    `<green>YYYY-MM-DD HH:mm:ss</green> | <level>ERROR   </level> | <cyan>module:function:line</cyan> - <level>Exception message</level> | <cyan>{'extra_key': 'extra_value'}</cyan>`

### JSON Logs (`dynel.json`)

-   Machine-readable, structured log output where each line is a JSON object.
-   Rotates when the file reaches 10 MB.
-   Useful for log processing, analysis, and integration with log management systems.
-   The JSON structure contains detailed information including timestamp, level, message, function name, line number, and the `extra` dictionary which includes DynEL's custom context (`timestamp`, `local_vars`, `tags`, etc.) and Loguru's `exception` details (type, value, traceback).

## 8. Advanced Usage & Best Practices

-   **Sensitive Data**: Be very careful when using `ContextLevel.DETAILED` or logging local variables, as they might include sensitive information. DynEL currently stringifies all local variables; future versions might offer more filtering.
-   **Performance**: Logging, especially with detailed context, can have a performance impact. Use higher context levels judiciously, perhaps more in development/staging and less in high-performance production paths.
-   **Custom Sinks**: While DynEL configures file sinks by default, you can always add your own Loguru sinks after `configure_logging()` if you need to send logs elsewhere (e.g., console, external services).
-   **Integrating with Frameworks**: When using DynEL with web frameworks (like Flask, Django) or other systems that have their own logging setup, you might need to integrate DynEL carefully, potentially by configuring Loguru to intercept standard library logging or by using DynEL's handlers in framework-specific error handling hooks.

(This User Guide will be expanded with more examples and best practices.)
