# DynEL: Dynamic Error Logging Module

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
7. [Contribution](#contribution)
8. [License](#license)
9. [Contact](#contact)
10. [Troubleshooting](#troubleshooting)
11. [Acknowledgments](#acknowledgments)

## Description

DynEL is a dynamic and configurable logging and error-handling utility built with Python. It uses the [Loguru library](https://github.com/Delgan/loguru) and supports both human-readable and machine-readable (JSON) log formats.

The long-term aim of this project is married to the [Perihelion Signal Processor (PeSPr)](https://github.com/tzervas/pespr). <!-- Update with actual link if different -->

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

**Note:** Ensure [UV](https://docs.astral.sh/uv/) is installed. See the [installation guide](https://docs.astral.sh/uv/getting-started/installation/) for instructions.

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
