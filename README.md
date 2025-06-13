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

The long term aim of this project is married to the [Periohelion Signal Processor (PeSPr)]()

## Installation

```bash
poetry install
```

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

```bash
tox
```

## Contribution

Please fork the repository and use a feature branch. Pull requests are welcome.

## License

DynEL is licensed under the MIT license; see `LICENSE` for more information.

## Contact

- **Author**: Tyler Zervas
- **GitLab**: [tzervas](https://github.com/tzervas)
- **X**: [@vec_wt_tech](https://x.com/vec_wt_tech)

## Troubleshooting

This section can be updated over time with common issues and their resolutions.

## Acknowledgments

Special thanks to the Loguru library for simplifying Python logging.
