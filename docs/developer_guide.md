# DynEL Developer Guide

This guide provides information for developers working on the DynEL library itself. For information on how to *use* DynEL in your project, please refer to the `README.md` and the User Guide (`docs/user_guide.md`).

## Project Structure

-   `src/dynel/`: Contains the core source code for the DynEL library.
    -   `dynel.py`: Main module implementing the DynEL functionality.
    -   `__init__.py`: Makes DynEL a package and exports key components.
-   `tests/`: Contains all unit and integration tests.
    -   `test_dynel.py`: Pytest tests for `dynel.py`.
-   `pyproject.toml`: Project metadata and dependencies, managed by Poetry.
-   `README.md`: Overview of the project, installation, and basic usage.
-   `CONTRIBUTING.md`: Guidelines for contributing to the project.
-   `LICENSE`: Project license (MIT).
-   `dynel_config.yaml` (example): An example configuration file. Users can create their own `dynel_config.[json/yaml/toml]`.
-   `docs/`: Contains project documentation.

## Development Environment

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/tzervas/DynEL.git
    cd DynEL
    ```
2.  **Install Poetry**: If you don't have Poetry, follow the instructions at [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation).
3.  **Install Dependencies**:
    ```bash
    poetry install
    ```
    This will create a virtual environment and install all dependencies listed in `pyproject.toml`, including development dependencies.
4.  **Activate the Virtual Environment**:
    ```bash
    poetry shell
    ```

## Running Tests

Tests are written using `pytest`. To run all tests:

```bash
pytest
# or
poetry run pytest
```

Ensure all tests pass before submitting any changes. New features or bug fixes should include corresponding tests. Code coverage should be maintained or increased.

## Code Style and Linting

(To be defined - e.g., Black, Flake8, isort. For now, follow PEP 8 and strive for clarity and consistency with existing code.)

## Key Design Principles

-   **Configurability**: DynEL should be highly configurable through external files (JSON, YAML, TOML) and/or code.
-   **Flexibility**: Adaptable to various logging needs and project structures.
-   **Clarity**: Log outputs should be clear and provide useful context. Error messages from DynEL itself should also be clear.
-   **Ease of Integration**: Simple to add to existing Python projects.
-   **Performance**: While providing rich context, strive to keep logging overhead reasonable.
-   **Token Economy (for AI model usage)**: Log messages and context levels should be designed with AI model consumption in mind. Aim for structured, concise, yet informative logs that are efficient for models to process and understand. This helps in reducing token usage during development and analysis by AI.

## Working with Loguru

DynEL uses [Loguru](https://github.com/Delgan/loguru) as its underlying logging engine. Familiarity with Loguru's concepts (sinks, formatters, `record` object, `@logger.catch`) is beneficial for understanding DynEL's internals.

## Improving Docstrings

Docstrings should follow a reStructuredText format compatible with Sphinx for future API documentation generation. Key elements include:
- Clear summary line.
- More detailed explanation if needed.
- `:param <name>: <description>` for parameters.
- `:type <name>: <type>` for parameter types.
- `:return: <description>` for return value.
- `:rtype: <type>` for return type.
- `:raises <ExceptionType>: <condition>` for exceptions.
- `:ivar <name>: <description>` for instance variables.
- `:vartype <name>: <type>` for instance variable types.

## Future Development Areas

(This section can list planned features or areas for improvement.)

-   More sophisticated context gathering (e.g., selective inclusion/exclusion of variables).
-   Advanced filtering capabilities for logs based on tags or other criteria.
-   Integration examples with popular frameworks (e.g., Flask, Django).
-   Schema validation for configuration files (currently basic, could be more robust).
-   Enhanced `module_exception_handler` to support class methods or selective function decoration within modules.
-   Setup Sphinx for automated API documentation generation.

## Submitting Changes

Please follow the guidelines in `CONTRIBUTING.md`. In summary:

-   Create a feature or bugfix branch from the latest `main`.
-   Make your changes, including tests and documentation updates.
-   Ensure all tests pass.
-   Open a Pull Request against the `main` branch.

Thank you for contributing to the development of DynEL!
