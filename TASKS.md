# DynEL Development Tasks

## Core Functionality (`src/dynel/dynel.py`)
- [x] Implement actual logging setup in `configure_logging`
    - [x] Initialize Loguru logger.
    - [x] Configure sinks (console, file) based on `DynelConfig`.
    - [x] Apply formatting from `DynelConfig`.
    - [x] Set logging level based on `DynelConfig.debug`.
- [ ] Implement `module_exception_handler`
    - [ ] Dynamically wrap functions in the target module.
    - [ ] Ensure wrapped functions call `handle_exception` upon error.
    - [ ] Consider how to handle classes and methods within modules.
- [ ] Define and implement `handle_exception` (currently in `src/dynel/exception_handling.py`, decide if it moves or stays)
    - [ ] Gather context based on `DynelConfig.context_level`.
    - [ ] Log exceptions using the configured logger.
    - [ ] Process `behaviors` from configuration.

## Configuration (`src/dynel/config.py` and `DynelConfig` in `src/dynel/dynel.py`)
- [ ] Implement configuration file loading in `DynelConfig` (or a helper class)
    - [ ] Support `dynel_config.yaml`, `dynel_config.json`, `dynel_config.toml`.
    - [ ] Load `debug_mode`, `context_level`, `formatting` global settings.
    - [ ] Load function-specific exception configurations (`exceptions`, `custom_message`, `tags`, `behaviors`).
    - [ ] Implement robust error handling for file loading and parsing.
- [ ] Resolve paths for `log_to_specific_file` behavior relative to a configurable base path or the config file path.
- [ ] Schema validation for configuration files.

## Exception Handling (`src/dynel/exception_handling.py`)
- [ ] Refine context gathering for `local_vars`, `env_details`.
    - [ ] Consider selective inclusion/exclusion.
    - [ ] Ensure sensitive data is not accidentally captured or is sanitized.
- [ ] Implement `add_metadata` behavior fully.
- [ ] Implement `log_to_specific_file` behavior fully.
    - [ ] Ensure JSON format for these specific log files.
    - [ ] Ensure main log also receives the entry.

## CLI (`src/dynel/cli.py`)
- [ ] Allow CLI arguments to override file configuration settings.
- [ ] Add CLI options for specifying configuration file path.
- [ ] Provide meaningful output for CLI operations (beyond placeholder prints).

## Testing (`tests/`)
- [x] Address review comments for `tests/test_dynel.py` (related to placeholders).
- [ ] Update `tests/test_config.py` to reflect changes in `DynelConfig` and its capabilities.
    - [ ] Adapt tests for file loading once implemented in `DynelConfig`.
    - [ ] Test behavior parsing and application.
- [ ] Update `tests/test_exception_handling.py`
    - [ ] Test `handle_exception` thoroughly with different contexts and behaviors.
    - [ ] Test `module_exception_handler` with various module structures.
- [ ] Update `tests/test_cli.py`
    - [ ] Test argument parsing and its effect on `DynelConfig`.
    - [ ] Test CLI overrides of file configurations.
- [ ] Increase test coverage across all modules.
- [ ] Add integration tests that cover the interaction of different components.

## Documentation
- [ ] Update `README.md` and user guides as features are implemented.
- [ ] Generate API documentation (e.g., using Sphinx).

## General/Refactoring
- [ ] Consolidate `DynelConfig` class: Decide if parts of old `src/dynel/config.py::DynelConfig` should be merged into `src/dynel/dynel.py::DynelConfig` or if `dynel.py` should use the one from `config.py`. (Current direction seems to be enhancing `dynel.py::DynelConfig`).
- [ ] Review and apply security best practices from `README.md` as features are developed.
- [ ] Ensure PEP 8 compliance and consistent code style (consider auto-formatters like Black, and linters like Ruff more strictly).
