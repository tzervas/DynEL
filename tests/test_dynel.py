import pytest
import yaml
import json
import toml
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from src.dynel import DynelConfig, configure_logging, parse_command_line_args, ContextLevel, handle_exception # Adjusted import

# --- Test Data ---
VALID_CONFIG_DATA_DICT = {
    "debug_mode": True,
    "MyFunction": {
        "exceptions": ["ValueError", "TypeError"],
        "custom_message": "Custom error in MyFunction",
        "tags": ["critical", "data_processing"]
    },
    "AnotherFunction": {
        "exceptions": ["KeyError"],
        "custom_message": "Key not found",
        "tags": ["lookup"]
    }
}

# --- Fixtures ---

@pytest.fixture
def temp_config_file_generator(): # Removed tmp_path from fixture signature
    """
    Factory fixture to generate temporary config files (json, yaml, toml).
    The actual tmp_path should be passed by the test function.
    """
    def _create_temp_file(base_path: Path, filename_prefix: str, extension: str, data: dict): # Added base_path
        file_path = base_path / f"{filename_prefix}.{extension}"
        if extension == "json":
            with open(file_path, "w") as f:
                json.dump(data, f)
        elif extension in ["yaml", "yml"]:
            with open(file_path, "w") as f:
                yaml.dump(data, f)
        elif extension == "toml":
            with open(file_path, "w") as f:
                toml.dump(data, f)
        else:
            raise ValueError(f"Unsupported extension for temp config: {extension}")
        return file_path
    return _create_temp_file

@pytest.fixture
def dynel_config_instance():
    """Returns a default DynelConfig instance."""
    return DynelConfig()

# --- Tests for DynelConfig ---

def test_dynel_config_defaults(dynel_config_instance):
    assert dynel_config_instance.CUSTOM_CONTEXT_LEVEL == ContextLevel.MINIMAL
    assert dynel_config_instance.DEBUG_MODE is False
    assert dynel_config_instance.FORMATTING_ENABLED is True
    assert dynel_config_instance.PANIC_MODE is False
    assert dynel_config_instance.EXCEPTION_CONFIG == {}

@pytest.mark.parametrize("ext", ["json", "yaml", "toml"])
def test_load_exception_config_valid(temp_config_file_generator, dynel_config_instance, ext, tmp_path, monkeypatch): # Added monkeypatch
    config_data = VALID_CONFIG_DATA_DICT.copy()
    filename_prefix = "test_dynel_config"
    temp_config_file_generator(tmp_path, filename_prefix, ext, config_data) # Pass tmp_path from test

    # Temporarily change CWD to where the temp file is, or pass full path
    # The temp_config_file_generator fixture has already used tmp_path to create the file.
    # We need tmp_path directly in the test to patch Path.cwd.
    # The fixture `temp_config_file_generator` returns the function `_create_temp_file`
    # The actual tmp_path is available via the `tmp_path` fixture injected into the test.
    # So, the patch should use the `tmp_path` fixture available in the test's scope.
    # This was an error in my previous reasoning. The `temp_config_file_generator`'s
    # `tmp_path` is what it uses. The test needs its own `tmp_path` reference for the CWD patch.
    # This should be fine as `tmp_path` is function-scoped by default.

    # Correct approach: The test uses `tmp_path` fixture directly for patching cwd.
    # The generator has already placed the file in that tmp_path.
    monkeypatch.chdir(tmp_path) # Use monkeypatch to change CWD
    dynel_config_instance.load_exception_config(filename_prefix=filename_prefix)
    # monkeypatch will automatically revert the CWD after the test

    assert dynel_config_instance.DEBUG_MODE == config_data["debug_mode"]
    assert "MyFunction" in dynel_config_instance.EXCEPTION_CONFIG
    mf_config = dynel_config_instance.EXCEPTION_CONFIG["MyFunction"]
    assert mf_config["custom_message"] == config_data["MyFunction"]["custom_message"]
    assert set(mf_config["tags"]) == set(config_data["MyFunction"]["tags"])
    assert ValueError in mf_config["exceptions"]
    assert TypeError in mf_config["exceptions"]

    assert "AnotherFunction" in dynel_config_instance.EXCEPTION_CONFIG
    af_config = dynel_config_instance.EXCEPTION_CONFIG["AnotherFunction"]
    assert KeyError in af_config["exceptions"]


def test_load_exception_config_file_not_found(dynel_config_instance):
    with pytest.raises(FileNotFoundError):
        dynel_config_instance.load_exception_config("non_existent_config")

@pytest.mark.parametrize("ext", ["json", "yaml", "toml"])
def test_load_exception_config_invalid_format(dynel_config_instance, ext, tmp_path, monkeypatch): # Added monkeypatch
    filename_prefix = "invalid_config"
    file_path = tmp_path / f"{filename_prefix}.{ext}"
    with open(file_path, "w") as f:
        f.write("this is not valid {syntax,, for all formats") # Write an invalid string

    monkeypatch.chdir(tmp_path) # Use monkeypatch to change CWD
    if ext == "yaml":
        # For YAML, a plain string is valid YAML, so it won't be a parsing error,
        # but rather a type error because the root is not a dict.
        with pytest.raises(ValueError, match=r"Invalid DynEL configuration file .* Root of configuration must be a dictionary."):
            dynel_config_instance.load_exception_config(filename_prefix)
    else:
        # For JSON and TOML, it should be a parsing error.
        with pytest.raises(ValueError, match=r"Failed to parse DynEL configuration file"):
            dynel_config_instance.load_exception_config(filename_prefix)


@pytest.mark.parametrize("ext", ["json", "yaml", "toml"])
def test_load_exception_config_safer_exception_loading(temp_config_file_generator, dynel_config_instance, ext, tmp_path, monkeypatch): # Added monkeypatch
    """Tests the safer loading of exception types (built-in, importable, and invalid)."""
    config_data = {
        "debug_mode": False,
        "FuncWithBuiltin": {"exceptions": ["ValueError", "DoesNotExist"]}, # DoesNotExist is not std builtin
        "FuncWithImportable": {"exceptions": ["os.PathLike"]}, # os.PathLike is not an exception
        "FuncWithNonException": {"exceptions": ["src.dynel.ContextLevel"]}, # Valid class, not an exception
        "FuncWithUnresolvable": {"exceptions": ["nonexistent_module.NonExistentError"]},
    }
    filename_prefix = "test_exc_loading"
    temp_config_file_generator(tmp_path, filename_prefix, ext, config_data) # Pass tmp_path from test

    # Mock logger to capture warnings/errors during loading
    mock_logger_warning = MagicMock()
    mock_logger_error = MagicMock()

    monkeypatch.chdir(tmp_path) # Use monkeypatch to change CWD
    with patch('src.dynel.dynel.logger.warning', mock_logger_warning), \
         patch('src.dynel.dynel.logger.error', mock_logger_error):
        dynel_config_instance.load_exception_config(filename_prefix)
    # monkeypatch for CWD is reverted automatically

    assert ValueError in dynel_config_instance.EXCEPTION_CONFIG["FuncWithBuiltin"]["exceptions"]
    # Check that DoesNotExist (not a real exception) was skipped and warned
    assert not any(exc_type.__name__ == "DoesNotExist" for exc_type in dynel_config_instance.EXCEPTION_CONFIG["FuncWithBuiltin"]["exceptions"])
    mock_logger_warning.assert_any_call(
        "Could not load exception 'DoesNotExist' for 'FuncWithBuiltin': not enough values to unpack (expected 2, got 1). Skipping."
    )

    # os.PathLike is not an exception
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithImportable"]["exceptions"]
    mock_logger_warning.assert_any_call(
        "Configured exception 'os.PathLike' for 'FuncWithImportable' is not a valid Exception class. Skipping."
    )

    # src.dynel.ContextLevel is not an exception
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithNonException"]["exceptions"]
    mock_logger_warning.assert_any_call(
        "Configured exception 'src.dynel.ContextLevel' for 'FuncWithNonException' is not a valid Exception class. Skipping."
    )

    # non_existent_module.NonExistentError should fail to import
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithUnresolvable"]["exceptions"]
    mock_logger_warning.assert_any_call(
        "Could not load exception 'nonexistent_module.NonExistentError' for 'FuncWithUnresolvable': No module named 'nonexistent_module'. Skipping."
    )


# --- Tests for configure_logging ---

@patch('src.dynel.dynel.logger') # Corrected path to logger
def test_configure_logging_debug_mode(mock_loguru_logger, dynel_config_instance):
    dynel_config_instance.DEBUG_MODE = True
    configure_logging(dynel_config_instance)

    mock_loguru_logger.remove.assert_called_once()
    # Check that logger.add was called for dynel.log with DEBUG level
    # This is a bit complex due to multiple calls to .add()
    # We can inspect call_args_list
    args_list = mock_loguru_logger.add.call_args_list
    assert any(
        call[1].get('sink') == 'dynel.log' and call[1].get('level') == 'DEBUG'
        for call in args_list
    )
    assert any(
        call[1].get('sink') == 'dynel.json' for call in args_list # serialize implies JSON
    )

@patch('src.dynel.dynel.logger') # Corrected path to logger
def test_configure_logging_production_mode(mock_loguru_logger, dynel_config_instance):
    dynel_config_instance.DEBUG_MODE = False
    configure_logging(dynel_config_instance)

    mock_loguru_logger.remove.assert_called_once()
    args_list = mock_loguru_logger.add.call_args_list
    assert any(
        call[1].get('sink') == 'dynel.log' and call[1].get('level') == 'INFO'
        for call in args_list
    )

# --- Tests for parse_command_line_args ---

def test_parse_command_line_args_defaults():
    with patch('argparse.ArgumentParser.parse_args', return_value=Mock(context_level='min', debug=False, formatting=True)):
        args = parse_command_line_args()
    assert args['context_level'] == 'min'
    assert args['debug'] is False
    assert args['formatting'] is True

@pytest.mark.parametrize("cli_arg, expected_key, expected_value, context_choices", [
    (['--context-level', 'med'], 'context_level', 'med', ['min', 'med', 'det']),
    (['--debug'], 'debug', True, None),
    (['--no-formatting'], 'formatting', False, None)
])
def test_parse_command_line_args_custom(cli_arg, expected_key, expected_value, context_choices):
    # The choices for context_level are defined in the function, so we don't need to pass them all here
    # just ensuring the mechanism works
    with patch('sys.argv', ['dynel.py'] + cli_arg):
         parsed_args = parse_command_line_args()
    assert parsed_args[expected_key] == expected_value


# --- Tests for handle_exception ---

@pytest.fixture
def captured_logs():
    """Fixture to capture Loguru logs in a list."""
    log_capture_list = []

    def capturing_sink(message):
        log_capture_list.append(message.record) # Store the full record for detailed assertions

    # Ensure default logger is clean and add our sink
    # Note: This might interfere if other tests also manipulate the global logger.
    # For isolated tests, this is okay. Consider per-test logger configuration if issues arise.
    from src.dynel.dynel import logger as dynel_logger # get the actual logger instance

    dynel_logger.remove() # Remove all handlers
    handler_id = dynel_logger.add(capturing_sink, format="{message}") # Basic format, we inspect record

    yield log_capture_list

    dynel_logger.remove(handler_id)
    # Optionally, re-add default handlers if needed by other tests, or ensure tests clean up.
    # For now, assuming test isolation or that subsequent tests will reconfigure.


def test_handle_exception_basic_logging(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    error_to_raise = ValueError("Test error for basic logging")

    # Mock inspect.stack() to control func_name
    with patch('inspect.stack') as mock_stack:
        mock_function_name = "mock_function_raising_error"
        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (Mock(), "filename_mock", 123, mock_function_name, ["code_line_mock"], 0)
        mock_stack.return_value = [
            Mock(), # Frame for handle_exception itself
            mock_caller_frame_tuple # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except ValueError as e:
            # Directly call handle_exception as if it was called from within the except block
            # of mock_function_raising_error
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert log_record["level"].name == "ERROR" # Loguru's .exception logs at ERROR level
    assert "Exception caught in mock_function_raising_error" in log_record["message"]
    assert log_record['exception'] is not None
    assert "Test error for basic logging" in str(log_record['exception'].value) # Corrected assertion
    assert "timestamp" in log_record["extra"]


def test_handle_exception_with_custom_message_and_tags(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    func_name = "my_specific_function"
    custom_msg = "A very specific error occurred!"
    tags = ["database", "critical"]

    config.EXCEPTION_CONFIG = {
        func_name: {
            "exceptions": [TypeError],
            "custom_message": custom_msg,
            "tags": tags
        }
    }
    error_to_raise = TypeError("Something went wrong with types")

    with patch('inspect.stack') as mock_stack:
        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (Mock(), "filename_mock", 123, func_name, ["code_line_mock"], 0)
        mock_stack.return_value = [
            Mock(), # Frame for handle_exception itself
            mock_caller_frame_tuple # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except TypeError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert log_record["level"].name == "ERROR"
    expected_log_message = f"Exception caught in {func_name} - Custom Message: {custom_msg}"
    assert log_record["message"] == expected_log_message # Exact message check
    assert log_record['exception'] is not None
    assert "Something went wrong with types" in str(log_record['exception'].value) # Corrected assertion
    assert log_record["extra"]["tags"] == tags
    assert "timestamp" in log_record["extra"]


@pytest.mark.parametrize("level_str, expected_keys_in_extra", [
    ("min", ["timestamp"]),
    ("med", ["timestamp", "local_vars"]),
    ("det", ["timestamp", "local_vars", "free_memory", "cpu_count", "env_details"])
    # Note: env_details might be very large, consider mocking os.environ for tests
])
def test_handle_exception_context_levels(level_str, expected_keys_in_extra, captured_logs):
    # For 'det' level, mock os.environ to avoid logging actual environment
    mock_os_environ = {"TEST_VAR": "test_value"}

    with patch('os.environ', mock_os_environ), \
         patch('src.dynel.dynel.inspect') as mock_dynel_inspect: # Patch inspect used in dynel.py

        config = DynelConfig(context_level=level_str)
        mock_function_name = "context_level_test_func"

        # Setup for inspect.stack()[1][3] to get mock_function_name
        mock_caller_frame_tuple = (Mock(), "filename_mock", 123, mock_function_name, ["code_line_mock"], 0)
        mock_dynel_inspect.stack.return_value = [
            Mock(), # Frame for handle_exception
            mock_caller_frame_tuple
        ]

        # Setup for inspect.currentframe().f_locals
        mock_frame_for_locals = Mock() # This is the mock frame object
        mock_frame_for_locals.f_locals = {"var1": 10, "var2": "test"} # Assign its f_locals
        mock_dynel_inspect.currentframe.return_value = mock_frame_for_locals # Make inspect.currentframe() return this mock frame

        error_to_raise = ConnectionError("A connection problem")

        try:
            raise error_to_raise
        except ConnectionError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert log_record["level"].name == "ERROR"
    assert f"Exception caught in {mock_function_name}" in log_record["message"] # Use mock_function_name
    assert log_record['exception'] is not None
    assert "A connection problem" in str(log_record['exception'].value) # Corrected assertion

    for key in expected_keys_in_extra:
        assert key in log_record["extra"]
        if key == "local_vars":
            assert str({"var1": 10, "var2": "test"}) in log_record["extra"]["local_vars"]
        if key == "env_details" and level_str == "det": # Only check if env_details was expected
             assert log_record["extra"]["env_details"] == mock_os_environ


def test_handle_exception_panic_mode(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    config.PANIC_MODE = True
    error_to_raise = RuntimeError("Critical system failure!")
    func_name = "panicking_function"

    with patch('inspect.stack') as mock_stack, \
         patch('sys.exit') as mock_sys_exit: # Patch sys.exit

        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (Mock(), "filename_mock", 123, func_name, ["code_line_mock"], 0)
        mock_stack.return_value = [
            Mock(), # Frame for handle_exception itself
            mock_caller_frame_tuple # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except RuntimeError as e:
            # handle_exception will call sys.exit, so we expect pytest.raises(SystemExit)
            # However, sys.exit is patched, so the test won't actually exit.
            # We call it directly and check mock_sys_exit.
            handle_exception(config, e)

    assert len(captured_logs) == 2 # One for the exception, one for the panic critical message

    exception_log = captured_logs[0] # Assuming first log is the exception itself
    assert exception_log["level"].name == "ERROR"
    assert f"Exception caught in {func_name}" in exception_log["message"]

    panic_log = captured_logs[1] # Assuming second log is the panic message
    assert panic_log["level"].name == "CRITICAL"
    assert f"PANIC MODE ENABLED: Exiting after handling exception in {func_name}." in panic_log["message"]

    mock_sys_exit.assert_called_once_with(1)


# --- Placeholder for future tests from original file ---
# @pytest.mark.parametrize("config_format", SUPPORTED_CONFIG_FORMATS)
# def test_config_driven_testing(load_config, config_format):
#     config = load_config
#     for error_type, settings in config.get('error_types', {}).items():
#         assert 'level' in settings
#         assert 'message' in settings

# def test_dynamic_assertions(load_config):
#     config = load_config
#     for key, value in config.items():
#         if key == 'debug_mode':
#             assert isinstance(value, bool)
#         # ... additional dynamic assertions

# Additional Tests for Methods in dynel.py, Exception Handling, Context, Debug Mode, Panic Mode
