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

DynEL allows you to set configurations through `dynel_config.[json/yaml/yml/toml]`:

### JSON

```json
{
  "debug_mode": false,
  "MyFunction": {
    "exceptions": ["ValueError", "FileNotFoundError"],
    "custom_message": "An error occurred",
    "tags": ["urgent", "db"]
  }
}
```

### YAML/YML

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
```

### TOML

```toml
debug_mode = false

[MyFunction]
exceptions = ["ValueError", "FileNotFoundError"]
custom_message = "An error occurred"
tags = ["urgent", "db"]
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
