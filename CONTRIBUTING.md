# Contributing to DynEL

First off, thank you for considering contributing to DynEL! Your help is greatly appreciated. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## How Can I Contribute?

There are many ways to contribute to DynEL, including:

-   **Reporting Bugs**: If you find a bug, please open an issue on GitHub. Include as much detail as possible: steps to reproduce, what you expected to happen, and what actually happened. Include error messages and stack traces if applicable.
-   **Suggesting Enhancements**: If you have an idea for a new feature or an improvement to an existing one, open an issue to discuss it. This allows us to coordinate efforts and ensure the enhancement aligns with the project's goals.
-   **Writing Code**: If you want to fix a bug or implement a feature, please fork the repository and submit a pull request.
-   **Improving Documentation**: Good documentation is crucial. If you find areas that are unclear, incomplete, or incorrect, please submit a pull request with your improvements.
-   **Writing Tests**: More tests are always welcome! They help ensure stability and prevent regressions.

## Development Setup

Please refer to the `README.md` for instructions on setting up your development environment. Generally, you'll want to:

1.  Fork the repository on GitHub.
2.  Clone your fork locally: `git clone https://github.com/your-username/DynEL.git`
3.  Create a new branch for your changes: `git checkout -b feature/your-feature-name` or `bugfix/your-bug-fix-name`.
4.  Set up a virtual environment and install dependencies (e.g., using Poetry: `poetry install`).
5.  Make your changes.
6.  Write tests for your changes.
7.  Ensure all tests pass: `poetry run pytest` (or `tox`).
8.  Format your code (e.g., using Black, if the project adopts it).
9.  Commit your changes with a clear and descriptive commit message.
10. Push your branch to your fork: `git push origin your-branch-name`.
11. Open a pull request against the `main` branch of the original DynEL repository.

## Pull Request Guidelines

-   Keep your pull requests focused. Each PR should address a single issue or feature.
-   Provide a clear description of the changes in your PR. Explain the "what" and "why" of your contribution.
-   Link to any relevant issues in your PR description (e.g., "Fixes #123").
-   Ensure your code passes all tests.
-   Update documentation if your changes affect it.
-   Be responsive to feedback and questions during the review process.

## Coding Conventions

-   Follow PEP 8 for Python code.
-   Write clear, readable, and maintainable code.
-   Include docstrings for all public modules, classes, functions, and methods.
-   Write unit tests for new functionality.

## Code of Conduct

This project and everyone participating in it is governed by a Code of Conduct (to be added - for now, please be respectful and considerate). Please help us keep DynEL an open and welcoming environment.

## Questions?

If you have any questions, feel free to open an issue or reach out to the maintainers.

Thank you for contributing!
