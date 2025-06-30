# DynEL: Dynamic Error Logging Module

🚀 **Project Status**: In active development. All components subject to change. Contributions and feedback welcome.

🎯 **Intent**: Provide a flexible and powerful logging and error-handling solution for Python applications, with seamless integration into projects like PeSPr.

🛠️ **Goals**:
- Simplify error logging and handling in Python
- Offer customizable logging configurations
- Support multiple configuration formats
- Integrate easily with other Python scripts and modules

## Table of Contents

1. [Description](#description)
2. [Installation](#installation)
3. [Usage](#usage)
   - [Basic Example](#basic-example)
   - [Using with Other Scripts](#using-with-other-scripts)
   - [CLI Arguments](#cli-arguments)
4. [Features](#features)
5. [Configuration (`dynel_config`)](#configuration-dynel_config)
6. [Testing](#testing)
7. [Development Setup](#development-setup)
8. [Security Best Practices](#security-best-practices)
9. [Contribution](#contribution)
10. [License](#license)
11. [Contact](#contact)
12. [Troubleshooting](#troubleshooting)
13. [Acknowledgments](#acknowledgments)
14. [References](#references)

## Description

DynEL is a dynamic and configurable logging and error-handling utility built with Python. It leverages the [Loguru library](https://github.com/Delgan/loguru) to provide both human-readable and machine-readable (JSON) log formats. Designed to work seamlessly with the [Perihelion Signal Processor (PeSPr)](https://github.com/tzervas/pespr), DynEL enhances error management in Python projects.

## Installation

To install DynEL, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/tzervas/dynel.git
   ```
2. Navigate to the project directory:
   ```bash
   cd dynel
   ```
3. Use [UV](https://docs.astral.sh/uv/) to install dependencies:
   ```bash
   uv sync
   ```

**Note:** Ensure [UV](https://docs.astral.sh/uv/) is installed. See the [installation guide](https://docs.astral.sh/uv/getting-started/installation/) for instructions. For development purposes, refer to the [Development Setup](#development-setup) section.

## Usage

### Basic Example

```python
from dynel import *

# Configure logging
config = dynel.DynelConfig(context_level='medium', debug=True)
dynel.configure_logging(config)
```

### Using with Other Scripts

To use DynEL in other Python scripts, simply import it and configure:

```python
from dynel import *

config = dynel.DynelConfig()
dynel.configure_logging(config)
```

You can also attach DynEL's exception handler to other modules:

```python
import another_module
dynel.module_exception_handler(config, another_module)
```

### CLI Arguments

DynEL accepts the following command-line arguments:

- `--context-level`: Sets the context level (`min`, `minimal`, `med`, `medium`, `det`, `detailed`).
- `--debug`: Enables debug mode.
- `--no-formatting`: Disables special formatting.

**Note**: When integrating DynEL into other scripts, these CLI arguments are reserved.

## Features

- Dynamic error logging
- Customizable context levels: `minimal`, `medium`, `detailed`
- Extensible Configuration: JSON, YAML, YML, TOML
- CLI configurability

## Configuration (`dynel_config`)

DynEL allows you to set configurations through `dynel_config.[json/yaml/yml/toml]`. Each function or module key (e.g., `MyFunction`, `__main__`) can have the following sub-keys:

-   `exceptions`: A list of exception class names (strings) that this configuration applies to.
-   `custom_message`: A string message to be logged when one of these exceptions occurs.
-   `tags`: A list of strings to be added as tags to the log entry.
-   `behaviors`: (New) A dictionary to define advanced error handling behaviors.

### Behavior Configuration

The `behaviors` section allows for defining actions on a per-exception basis, or a default set of actions for any matched exception within that function's configuration block.

```yaml
# Example in YAML format
debug_mode: false

MyFunction:
  exceptions:
    - ValueError
    - FileNotFoundError
    - CustomErrorModule.SpecificError
  custom_message: "An error occurred in MyFunction."
  tags: ["critical", "user_facing"]
  behaviors:
    # Specific behaviors for ValueError in MyFunction
    ValueError:
      add_metadata:
        error_code: "E1001"
        suggestion: "Check input types."
    # Specific behaviors for FileNotFoundError in MyFunction
    FileNotFoundError:
      log_to_specific_file: "file_access_errors.log"
      add_metadata:
        error_category: "File System"
        recovery_tip: "Ensure the path exists and has correct permissions."
    # Default behaviors for any other matched exception (e.g., CustomErrorModule.SpecificError)
    # in MyFunction if not explicitly listed above.
    default:
      add_metadata:
        function_group: "Core Utilities"
        monitoring_alert: "true"

AnotherFunction:
  exceptions:
    - TypeError
  custom_message: "Type issue in AnotherFunction."
  # No specific behaviors defined, so none of the advanced actions will be taken.
  # It will still log with the custom_message and any configured tags.

__main__:
  exceptions:
    - argparse.ArgumentError
  custom_message: "CLI argument error."
  behaviors:
    default:
      add_metadata:
        source: "CLI"
```

**Supported Behaviors (for Proof of Concept):**

*   `log_to_specific_file: "filename.log"`: Routes the log entry for this specific error to the designated file. The main log file will still receive the entry as per global configuration.
*   `add_metadata: {key: value, ...}`: A dictionary of custom key-value pairs that will be added to the structured (JSON) log output for this error. This is useful for adding context for later analysis or ML ingestion.

### General Configuration Examples

#### JSON

```json
{
  "debug_mode": false,
  "MyFunction": {
    "exceptions": ["ValueError", "FileNotFoundError"],
    "custom_message": "An error occurred",
    "tags": ["urgent", "db"],
    "behaviors": {
      "ValueError": {
        "add_metadata": { "error_code": "VAL-001" }
      },
      "default": {
        "log_to_specific_file": "myfunction_other_errors.log"
      }
    }
  }
}
```

#### YAML/YML (as shown in detail above)

```yaml
debug_mode: false
MyFunction:
  exceptions:
    - ValueError
    - FileNotFoundError
  custom_message: "An error occurred"
  tags:
    - urgent
    - db
  behaviors:
    ValueError:
      add_metadata:
        error_code: "VAL-001"
    default:
      log_to_specific_file: "myfunction_other_errors.log"
```

#### TOML

```toml
debug_mode = false

[MyFunction]
exceptions = ["ValueError", "FileNotFoundError"]
custom_message = "An error occurred"
tags = ["urgent", "db"]

[MyFunction.behaviors.ValueError]
add_metadata = { error_code = "VAL-001" }

[MyFunction.behaviors.default]
log_to_specific_file = "myfunction_other_errors.log"
```

## Testing

Run tests with:

```bash
tox
```

**Note**: Tox is used to run tests across multiple environments, including pytest for unit testing.

## Development Setup

For developers looking to contribute to DynEL or extend its functionality, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/tzervas/dynel.git
   ```
2. Navigate to the project directory:
   ```bash
   cd dynel
   ```
3. Use [UV](https://docs.astral.sh/uv/) to install dependencies:
   ```bash
   uv sync
   ```
4. Configure DynEL by creating or updating `dynel_config.[json/yaml/yml/toml]` in the project root. You can also set environment variables to override configuration settings.
5. Run tests to ensure everything is set up correctly:
   ```bash
   tox
   ```
6. To run the application or integrate DynEL into your own scripts, refer to the [Usage](#usage) section.

## Security Best Practices

When using DynEL, consider the following security guidelines:

- **Avoid logging sensitive information**: Ensure that passwords, API keys, or other sensitive data are not included in logs. Use appropriate log levels (e.g., DEBUG for development, INFO or higher for production).
- **Secure configuration files**: Do not commit `dynel_config` files containing sensitive data to version control. Use environment variables or secure storage for such information.
- **Validate inputs**: If DynEL is used to log user inputs or external data, ensure that inputs are validated to prevent injection attacks or log forgery.
- **CLI argument handling**: Be cautious with CLI arguments that may expose sensitive information. Avoid passing sensitive data via CLI where possible.

## Contribution

Contributions are welcome! Please see the [Developer Guide](docs/devel-docs/developer_guide.md) and [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

DynEL is licensed under the MIT license; see [LICENSE](LICENSE) for more information.

## Contact

- **Author**: Tyler Zervas
- **GitHub**: [tzervas](https://github.com/tzervas)
- **X**: [@vec_wt_tech](https://x.com/vec_wt_tech)

## Troubleshooting

If you encounter any issues, please check the [issue tracker](https://github.com/tzervas/dynel/issues) or contact the author.

## Acknowledgments

Special thanks to the Loguru library for simplifying Python logging.

## References

- [Loguru Documentation](https://loguru.readthedocs.io/en/stable/)
- [Perihelion Signal Processor (PeSPr)](https://github.com/tzervas/pespr)
- [UV Documentation](https://docs.astral.sh/uv/)

## JSON Log Structure for ML Consumption

DynEL produces JSON formatted logs (e.g., `dynel.json` and files from `log_to_specific_file` behavior) that are well-suited for ingestion into Machine Learning pipelines. Each log entry is a JSON object. Key fields of interest for ML include:

-   `text`: The human-readable, formatted log message.
-   `record`: A nested object containing detailed information:
    -   `time`: ISO 8601 timestamp (e.g., `record.time.isoformat()`).
    -   `level.name`: Log level string (e.g., "ERROR", "CRITICAL").
    -   `message`: The raw, unformatted log message.
    -   `extra`: A dictionary containing all custom contextual information. This is where DynEL adds most of its value for ML:
        -   `timestamp`: (Duplicate of `record.time` but directly in `extra` for convenience) ISO 8601 timestamp.
        -   `tags`: A list of strings defined in the configuration for the error. Useful for high-level categorization.
        -   `local_vars`: (If `ContextLevel` is Medium/Detailed) A string representation of a dictionary of local variables at the error site. May require parsing for structured use in ML. Can be very rich but also noisy.
        -   `free_memory`, `cpu_count`: (If `ContextLevel` is Detailed) System metrics.
        -   `env_details`: (If `ContextLevel` is Detailed) A string representation of a dictionary of environment variables. May require parsing.
        -   **Custom Metadata (from `add_metadata` behavior):** Any key-value pairs you define in your `dynel_config.yaml` under `behaviors -> add_metadata` will appear here. This is the most powerful way to inject domain-specific, structured features for your ML models (e.g., `error_code`, `user_id`, `transaction_id`, `severity_override`).
    -   `exception`: An object detailing the exception:
        -   `type`: String name of the exception class (e.g., "ValueError").
        -   `value`: String representation of the exception (the error message itself).
        -   `traceback`: A list of strings, where each string is a frame from the traceback.

**Considerations for ML:**

-   **Feature Engineering:** Fields like `record.exception.type`, `record.level.name`, and custom metadata keys in `record.extra` can be used directly as categorical features. Text fields like `record.exception.value` and `record.exception.traceback` can be processed using NLP techniques (tokenization, embedding) for more advanced feature extraction.
-   **`local_vars` and `env_details` Parsing:** These are stored as strings of dictionaries. Your ML pipeline may need a preprocessing step to parse these strings back into structured objects if you intend to use their contents as individual features.
-   **Log Volume and Context Level:** Be mindful of the `ContextLevel` setting. `DETAILED` provides maximum information but can significantly increase log volume and the size of fields like `local_vars`. Choose a level appropriate for your needs.
-   **Schema Consistency:** While `add_metadata` is flexible, establishing a consistent schema for the custom metadata you add across different error types will simplify ML model development and training.
