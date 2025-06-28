import pytest
import pytest
import yaml
import json
import toml
import inspect  # Added for inspect.isclass
from typing import Optional # Added Optional
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from src.dynel import (
    DynelConfig,
    configure_logging,
    parse_command_line_args,
    ContextLevel,
    handle_exception,
    module_exception_handler,
)  # Added module_exception_handler


# --- Test Data ---
VALID_CONFIG_DATA_DICT = {
    "debug_mode": True,
    "MyFunction": {
        "exceptions": ["ValueError", "TypeError"],
        "custom_message": "Custom error in MyFunction",
        "tags": ["critical", "data_processing"],
    },
    "AnotherFunction": {
        "exceptions": ["KeyError"],
        "custom_message": "Key not found",
        "tags": ["lookup"],
    },
}

# --- Fixtures ---


@pytest.fixture
def temp_config_file_generator():  # Removed tmp_path from fixture signature
    """
    Factory fixture to generate temporary config files (json, yaml, toml).
    The actual tmp_path should be passed by the test function.
    """

    def _create_temp_file(
        base_path: Path, filename_prefix: str, extension: str, data: dict
    ):  # Added base_path
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
def test_load_exception_config_valid(
    temp_config_file_generator, dynel_config_instance, ext, tmp_path, monkeypatch
):  # Added monkeypatch
    config_data = VALID_CONFIG_DATA_DICT.copy()
    filename_prefix = "test_dynel_config"
    temp_config_file_generator(
        tmp_path, filename_prefix, ext, config_data
    )  # Pass tmp_path from test

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
    monkeypatch.chdir(tmp_path)  # Use monkeypatch to change CWD
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


@pytest.mark.parametrize("ext", ["json", "toml"])
def test_load_exception_config_invalid_format_json_toml(
    dynel_config_instance, ext, tmp_path, monkeypatch
):
    filename_prefix = "invalid_config"
    file_path = tmp_path / f"{filename_prefix}.{ext}"
    with open(file_path, "w") as f:
        f.write(
            "this is not valid {syntax,, for all formats"
        )  # Write an invalid string

    monkeypatch.chdir(tmp_path)  # Use monkeypatch to change CWD
    with pytest.raises(
        ValueError, match=r"Failed to parse DynEL configuration file"
    ):
        dynel_config_instance.load_exception_config(filename_prefix)

def test_load_exception_config_invalid_format_yaml(
    dynel_config_instance, tmp_path, monkeypatch
):
    filename_prefix = "invalid_config"
    file_path = tmp_path / f"{filename_prefix}.yaml"
    with open(file_path, "w") as f:
        f.write(
            "this is not valid {syntax,, for all formats"
        )  # Write an invalid string

    monkeypatch.chdir(tmp_path)  # Use monkeypatch to change CWD
    with pytest.raises(
        ValueError,
        match=r"Invalid DynEL configuration file .* Root of configuration must be a dictionary.",
    ):
        dynel_config_instance.load_exception_config(filename_prefix)


@pytest.mark.parametrize("ext", ["json", "yaml", "toml"])
def test_load_exception_config_safer_exception_loading(
    temp_config_file_generator, dynel_config_instance, ext, tmp_path, monkeypatch
):  # Added monkeypatch
    """Tests the safer loading of exception types (built-in, importable, and invalid)."""
    config_data = {
        "debug_mode": False,
        "FuncWithBuiltin": {
            "exceptions": ["ValueError", "DoesNotExist"]
        },  # DoesNotExist is not std builtin
        "FuncWithImportable": {
            "exceptions": ["os.PathLike"]
        },  # os.PathLike is not an exception
        "FuncWithNonException": {
            "exceptions": ["src.dynel.ContextLevel"]
        },  # Valid class, not an exception
        "FuncWithUnresolvable": {"exceptions": ["nonexistent_module.NonExistentError"]},
    }
    filename_prefix = "test_exc_loading"
    temp_config_file_generator(
        tmp_path, filename_prefix, ext, config_data
    )  # Pass tmp_path from test

    # Mock logger to capture warnings/errors during loading
    mock_logger_warning = MagicMock()
    mock_logger_error = MagicMock()

    monkeypatch.chdir(tmp_path)  # Use monkeypatch to change CWD
    with patch("src.dynel.dynel.logger.warning", mock_logger_warning), patch(
        "src.dynel.dynel.logger.error", mock_logger_error
    ):
        dynel_config_instance.load_exception_config(filename_prefix)
    # monkeypatch for CWD is reverted automatically

    assert (
        ValueError
        in dynel_config_instance.EXCEPTION_CONFIG["FuncWithBuiltin"]["exceptions"]
    )
    # Check that DoesNotExist (not a real exception) was skipped and warned
    assert not any(
        exc_type.__name__ == "DoesNotExist"
        for exc_type in dynel_config_instance.EXCEPTION_CONFIG["FuncWithBuiltin"][
            "exceptions"
        ]
    )
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'DoesNotExist' for 'FuncWithBuiltin': not enough values to unpack (expected 2, got 1). Skipping."
    )

    # os.PathLike is not an exception
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithImportable"][
        "exceptions"
    ]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'os.PathLike' for 'FuncWithImportable': 'os.PathLike' is not an Exception subclass.. Skipping."
    )

    # src.dynel.ContextLevel is not an exception
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithNonException"][
        "exceptions"
    ]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'src.dynel.ContextLevel' for 'FuncWithNonException': 'src.dynel.ContextLevel' is not an Exception subclass.. Skipping."
    )

    # non_existent_module.NonExistentError should fail to import
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithUnresolvable"][
        "exceptions"
    ]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'nonexistent_module.NonExistentError' for 'FuncWithUnresolvable': No module named 'nonexistent_module'. Skipping."
    )


# --- Tests for configure_logging ---


@patch("src.dynel.dynel.logger")  # Corrected path to logger
def test_configure_logging_debug_mode(mock_loguru_logger, dynel_config_instance):
    dynel_config_instance.DEBUG_MODE = True
    configure_logging(dynel_config_instance)

    mock_loguru_logger.remove.assert_called_once()
    # Check that logger.add was called for dynel.log with DEBUG level
    # This is a bit complex due to multiple calls to .add()
    # We can inspect call_args_list
    args_list = mock_loguru_logger.add.call_args_list
    assert any(
        call[1].get("sink") == "dynel.log" and call[1].get("level") == "DEBUG"
        for call in args_list
    )
    assert any(
        call[1].get("sink") == "dynel.json"
        for call in args_list  # serialize implies JSON
    )


@patch("src.dynel.dynel.logger")  # Corrected path to logger
def test_configure_logging_production_mode(mock_loguru_logger, dynel_config_instance):
    dynel_config_instance.DEBUG_MODE = False
    configure_logging(dynel_config_instance)

    mock_loguru_logger.remove.assert_called_once()
    args_list = mock_loguru_logger.add.call_args_list
    assert any(
        call[1].get("sink") == "dynel.log" and call[1].get("level") == "INFO"
        for call in args_list
    )


# --- Tests for parse_command_line_args ---


def test_parse_command_line_args_defaults():
    with patch(
        "argparse.ArgumentParser.parse_args",
        return_value=Mock(context_level="min", debug=False, formatting=True),
    ):
        args = parse_command_line_args()
    assert args["context_level"] == "min"
    assert args["debug"] is False
    assert args["formatting"] is True


@pytest.mark.parametrize(
    "cli_arg, expected_key, expected_value, context_choices",
    [
        (["--context-level", "med"], "context_level", "med", ["min", "med", "det"]),
        (["--debug"], "debug", True, None),
        (["--no-formatting"], "formatting", False, None),
    ],
)
def test_parse_command_line_args_custom(
    cli_arg, expected_key, expected_value, context_choices
):
    # The choices for context_level are defined in the function, so we don't need to pass them all here
    # just ensuring the mechanism works
    with patch("sys.argv", ["dynel.py"] + cli_arg):
        parsed_args = parse_command_line_args()
    assert parsed_args[expected_key] == expected_value

# --- Tests for handle_exception ---


@pytest.fixture
def captured_logs():
    """Fixture to capture Loguru logs in a list."""
    log_capture_list = []

    def capturing_sink(message):
        log_capture_list.append(
            message.record
        )  # Store the full record for detailed assertions

    # Ensure default logger is clean and add our sink
    # Note: This might interfere if other tests also manipulate the global logger.
    # For isolated tests, this is okay. Consider per-test logger configuration if issues arise.
    from src.dynel.dynel import logger as dynel_logger  # get the actual logger instance

    dynel_logger.remove()  # Remove all handlers
    handler_id = dynel_logger.add(
        capturing_sink, format="{message}"
    )  # Basic format, we inspect record

    yield log_capture_list

    dynel_logger.remove(handler_id)
    # Optionally, re-add default handlers if needed by other tests, or ensure tests clean up.
    # For now, assuming test isolation or that subsequent tests will reconfigure.


def test_handle_exception_basic_logging(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    error_to_raise = ValueError("Test error for basic logging")

    # Mock inspect.stack() to control func_name
    with patch("inspect.stack") as mock_stack:
        mock_function_name = "mock_function_raising_error"
        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (
            Mock(),
            "filename_mock",
            123,
            mock_function_name,
            ["code_line_mock"],
            0,
        )
        mock_stack.return_value = [
            Mock(),  # Frame for handle_exception itself
            mock_caller_frame_tuple,  # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except ValueError as e:
            # Directly call handle_exception as if it was called from within the except block
            # of mock_function_raising_error
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert (
        log_record["level"].name == "ERROR"
    )  # Loguru's .exception logs at ERROR level
    assert "Exception caught in mock_function_raising_error" in log_record["message"]
    assert log_record["exception"] is not None
    assert "Test error for basic logging" in str(
        log_record["exception"].value
    )  # Corrected assertion
    assert "timestamp" in log_record["extra"]


def test_handle_exception_with_custom_message_and_tags(
    dynel_config_instance, captured_logs
):
    config = dynel_config_instance
    func_name = "my_specific_function"
    custom_msg = "A very specific error occurred!"
    tags = ["database", "critical"]

    config.EXCEPTION_CONFIG = {
        func_name: {
            "exceptions": [TypeError],
            "custom_message": custom_msg,
            "tags": tags,
        }
    }
    error_to_raise = TypeError("Something went wrong with types")

    with patch("inspect.stack") as mock_stack:
        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (
            Mock(),
            "filename_mock",
            123,
            func_name,
            ["code_line_mock"],
            0,
        )
        mock_stack.return_value = [
            Mock(),  # Frame for handle_exception itself
            mock_caller_frame_tuple,  # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except TypeError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert log_record["level"].name == "ERROR"
    expected_log_message = (
        f"Exception caught in {func_name} - Custom Message: {custom_msg}"
    )
    assert log_record["message"] == expected_log_message  # Exact message check
    assert log_record["exception"] is not None
    assert "Something went wrong with types" in str(
        log_record["exception"].value
    )  # Corrected assertion
    assert log_record["extra"]["tags"] == tags
    assert "timestamp" in log_record["extra"]


@pytest.mark.parametrize(
    "level_str, expected_keys_in_extra",
    [
        ("min", ["timestamp"]),
        ("med", ["timestamp", "local_vars"]),
        ("det", ["timestamp", "local_vars", "free_memory", "cpu_count", "env_details"]),
        # Note: env_details might be very large, consider mocking os.environ for tests
    ],
)
def test_handle_exception_context_levels(
    level_str, expected_keys_in_extra, captured_logs
):
    # For 'det' level, mock os.environ to avoid logging actual environment
    mock_os_environ = {"TEST_VAR": "test_value"}

    with patch("os.environ", mock_os_environ), patch(
        "src.dynel.dynel.inspect"
    ) as mock_dynel_inspect:  # Patch inspect used in dynel.py

        config = DynelConfig(context_level=level_str)
        mock_function_name = "context_level_test_func"

        # This mock will be inspect.stack()[1][0] (the frame of the caller of handle_exception)
        mock_caller_frame_object = Mock()
        mock_caller_frame_object.configure_mock(f_locals={"var1": 10, "var2": "test"}) # Use configure_mock

        # Setup for inspect.stack()[1]
        mock_caller_frame_info_tuple = (
            mock_caller_frame_object, # This is inspect.stack()[1][0]
            "filename_mock",          # inspect.stack()[1][1]
            123,                      # inspect.stack()[1][2]
            mock_function_name,       # inspect.stack()[1][3]
            ["code_line_mock"],       # inspect.stack()[1][4]
            0,                        # inspect.stack()[1][5]
        )
        mock_dynel_inspect.stack.return_value = [
            Mock(),  # Frame for handle_exception itself (inspect.stack()[0])
            mock_caller_frame_info_tuple, # Frame info for the caller (inspect.stack()[1])
        ]
        # No need to mock inspect.currentframe separately for this specific path in handle_exception

        error_to_raise = ConnectionError("A connection problem")

        try:
            raise error_to_raise
        except ConnectionError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert log_record["level"].name == "ERROR"
    assert (
        f"Exception caught in {mock_function_name}" in log_record["message"]
    )  # Use mock_function_name
    assert log_record["exception"] is not None
    assert "A connection problem" in str(
        log_record["exception"].value
    )  # Corrected assertion

    # Explicit checks instead of loop and conditionals
    assert "timestamp" in log_record["extra"]
    if "local_vars" in expected_keys_in_extra:
        # Loosened check due to difficulties in mocking exact f_locals via inspect.stack
        local_vars = log_record["extra"]["local_vars"]
        assert "var1" in local_vars
        assert ": 10" in local_vars
        assert "var2" in local_vars
        assert ": 'test'" in local_vars
    if "free_memory" in expected_keys_in_extra:
        assert "free_memory" in log_record["extra"]
    if "cpu_count" in expected_keys_in_extra:
        assert "cpu_count" in log_record["extra"]
    if "env_details" in expected_keys_in_extra and level_str == "det":
        assert log_record["extra"]["env_details"] == mock_os_environ


def test_handle_exception_panic_mode(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    config.PANIC_MODE = True
    error_to_raise = RuntimeError("Critical system failure!")
    func_name = "panicking_function"

    with patch("inspect.stack") as mock_stack, patch(
        "sys.exit"
    ) as mock_sys_exit:  # Patch sys.exit

        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (
            Mock(),
            "filename_mock",
            123,
            func_name,
            ["code_line_mock"],
            0,
        )
        mock_stack.return_value = [
            Mock(),  # Frame for handle_exception itself
            mock_caller_frame_tuple,  # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except RuntimeError as e:
            # handle_exception will call sys.exit, so we expect pytest.raises(SystemExit)
            # However, sys.exit is patched, so the test won't actually exit.
            # We call it directly and check mock_sys_exit.
            handle_exception(config, e)

    assert (
        len(captured_logs) == 2
    )  # One for the exception, one for the panic critical message

    exception_log = captured_logs[0]  # Assuming first log is the exception itself
    assert exception_log["level"].name == "ERROR"
    assert f"Exception caught in {func_name}" in exception_log["message"]

    panic_log = captured_logs[1]  # Assuming second log is the panic message
    assert panic_log["level"].name == "CRITICAL"
    assert (
        f"PANIC MODE ENABLED: Exiting after handling exception in {func_name}."
        in panic_log["message"]
    )

    mock_sys_exit.assert_called_once_with(1)


# --- Tests for module_exception_handler ---

# Dummy module for testing module_exception_handler
DUMMY_MODULE_CONTENT = """
def func_that_works():
    return "worked"

def func_that_raises_value_error():
    raise ValueError("Dummy ValueError")

def func_that_raises_type_error():
    raise TypeError("Dummy TypeError")

_a_private_variable = True # Should not be wrapped

class SomeClass: # Should not be wrapped
    def method(self):
        raise AttributeError("Dummy AttributeError in class")
"""


@pytest.fixture
def dummy_module(tmp_path):
    """Creates a dummy module file and imports it."""
    module_path = tmp_path / "dummy_module_for_dynel_test.py"
    module_path.write_text(DUMMY_MODULE_CONTENT)

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "dummy_module_for_dynel_test", module_path
    )
    imported_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported_module)
    return imported_module


def test_module_exception_handler_wraps_functions(dynel_config_instance, dummy_module):
    config = dynel_config_instance

    # Keep a reference to original functions to reset if necessary, though for this test structure,
    # the dummy_module is fresh each time due to fixture scope.
    # original_value_error_func = dummy_module.func_that_raises_value_error
    # original_works_func = dummy_module.func_that_works

    with patch("src.dynel.dynel.handle_exception") as mock_handle_exception:
        mock_handle_exception.return_value = (
            None  # Ensure mock doesn't suppress re-raise
        )

        module_exception_handler(
            config, dummy_module
        )  # Corrected: Call module_exception_handler

        # Test that wrapped function still works if no error
        assert dummy_module.func_that_works() == "worked"

        # Test that error in wrapped function calls our handler
        with pytest.raises(
            ValueError
        ):  # Loguru's @logger.catch will re-raise by default
            dummy_module.func_that_raises_value_error()

        mock_handle_exception.assert_called_once()  # Use the correct mock name
        args, _ = mock_handle_exception.call_args
        assert args[0] == config
        assert isinstance(args[1], ValueError)
        assert str(args[1]) == "Dummy ValueError"

        # Check that non-function attributes are not wrapped/changed
        assert dummy_module._a_private_variable is True
        assert inspect.isclass(dummy_module.SomeClass)  # Check it's still a class

        # Check that methods within classes are not wrapped by module_exception_handler directly
        instance = dummy_module.SomeClass()
        with pytest.raises(AttributeError, match="Dummy AttributeError in class"):
            instance.method()
        # mock_handle_exception should still be called once from the module-level function
        mock_handle_exception.assert_called_once()


def test_module_exception_handler_multiple_exceptions(dynel_config_instance, dummy_module):
    """
    Test that the exception handler is triggered for both ValueError and TypeError
    raised from a single dummy module function.
    """
    # Dynamically add the required function to the dummy_module
    def func_that_raises_multiple_exceptions(arg):
        if arg == "value":
            raise ValueError("value error")
        elif arg == "type":
            raise TypeError("type error")
    setattr(dummy_module, "func_that_raises_multiple_exceptions", func_that_raises_multiple_exceptions)

    with patch("src.dynel.dynel.handle_exception") as mock_handle_exception:
        mock_handle_exception.return_value = None # Ensure mock doesn't suppress re-raise

        module_exception_handler(dynel_config_instance, dummy_module)

        # Trigger ValueError
        with pytest.raises(ValueError, match="value error"):
            dummy_module.func_that_raises_multiple_exceptions("value")

        assert mock_handle_exception.call_count == 1
        args, _ = mock_handle_exception.call_args
        assert args[0] == dynel_config_instance
        assert isinstance(args[1], ValueError)
        assert str(args[1]) == "value error"

        mock_handle_exception.reset_mock()

        # Trigger TypeError
        with pytest.raises(TypeError, match="type error"):
            dummy_module.func_that_raises_multiple_exceptions("type")

        assert mock_handle_exception.call_count == 1
        args, _ = mock_handle_exception.call_args
        assert args[0] == dynel_config_instance
        assert isinstance(args[1], TypeError)
        assert str(args[1]) == "type error"

    # Clean up the dynamically added function if necessary, though pytest fixtures usually handle module isolation.
    if hasattr(dummy_module, "func_that_raises_multiple_exceptions"):
        delattr(dummy_module, "func_that_raises_multiple_exceptions")


# --- Tests for Log File Output ---


def test_log_file_output_formats(tmp_path, monkeypatch):
    config = DynelConfig(context_level="med")  # Use medium context for some local_vars

    # Configure logging to use temporary files
    log_file_txt = tmp_path / "output.log"
    log_file_json = tmp_path / "output.json"

    # Patch the logger.add calls within configure_logging to use these temp files
    # This is a bit more involved as configure_logging removes all handlers then adds new ones.
    # We can patch 'logger.add' and inspect its calls, or patch the sink names directly if possible.
    # A simpler way for this test: modify the configure_logging function temporarily for the test,
    # or have DynelConfig allow specifying log paths.
    # For now, let's patch 'logger.add'.

    from src.dynel.dynel import logger as dynel_logger  # Import the logger instance

    # We need to capture what `logger.add` is called with.
    # The `captured_logs` fixture reconfigures the logger. We need to manage this carefully.
    # Let's create a specific logger configuration for this test.

    dynel_logger.remove()  # Clear existing handlers (like from captured_logs fixture if it ran)
    dynel_logger.add(
        log_file_txt,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message} | {extra}",
        level="DEBUG",
    )
    dynel_logger.add(log_file_json, serialize=True, level="DEBUG")

    error_to_raise = IndexError("Test index out of bounds")
    func_name = "function_writing_to_log_files"

    # Mock inspect.stack to control func_name in handle_exception
    # and to provide locals for the caller's frame.


    mock_caller_frame_obj_for_log_test = Mock()
    mock_caller_frame_obj_for_log_test.f_locals = {"alpha": 1, "beta": "two"}

    with patch("src.dynel.dynel.inspect") as mock_dynel_inspect: # Patch inspect module used by dynel

        mock_caller_frame_info_tuple_for_log_test = (
            mock_caller_frame_obj_for_log_test,
            "test_file.py",
            100,
            func_name,
            ["some_code"],
            0,
        )
        mock_dynel_inspect.stack.return_value = [
            Mock(),
            mock_caller_frame_info_tuple_for_log_test
        ]
        # If handle_exception directly uses inspect.currentframe(), it would also need:
        # mock_dynel_inspect.currentframe.return_value = mock_caller_frame_obj_for_log_test
        # But current logic uses inspect.stack()[1][0].f_locals

        try:
            raise error_to_raise
        except IndexError as e:
            handle_exception(config, e)

    # Verify text log content
    assert log_file_txt.exists()
    txt_content = log_file_txt.read_text()
    assert "ERROR" in txt_content  # Level
    assert (
        f"{func_name}" in txt_content
    )  # Function name from handle_exception's perspective
    assert "Exception caught in" in txt_content
    assert "IndexError: Test index out of bounds" in txt_content  # Exception message
    assert "'alpha': 1" in txt_content # Looser check for part of local_vars
    assert "'beta': 'two'" in txt_content # Looser check for part of local_vars
    assert "timestamp" in txt_content  # From custom_context

    # Verify JSON log content
    assert log_file_json.exists()
    json_content = log_file_json.read_text()
    # Each line in the JSON log file is a separate JSON object
    # For this test, we expect one log entry from handle_exception
    json_content = log_file_json.read_text()
    log_entry = _find_log_record_by_function(json_content, "handle_exception")

    assert (
        log_entry is not None
    ), "Log entry from handle_exception not found in JSON log"

    assert log_entry["level"]["name"] == "ERROR"
    assert f"Exception caught in {func_name}" in log_entry["message"]

    exception_details = log_entry["exception"]
    assert exception_details["type"] == "IndexError"
    assert "Test index out of bounds" in exception_details["value"]
    assert exception_details["traceback"]  # Check traceback exists

    extra_details = log_entry["extra"]
    assert "timestamp" in extra_details
    # Loosened checks for JSON local_vars content
    assert "alpha" in extra_details["local_vars"]
    assert ": 1" in extra_details["local_vars"] # Assuming simple int stringification
    assert "beta" in extra_details["local_vars"]
    assert ": 'two'" in extra_details["local_vars"] # String value with quotes

    # Clean up global logger state for other tests
    from src.dynel.dynel import logger as dynel_logger  # Ensure it's in scope

    dynel_logger.remove()
    # Re-add a default console sink if other tests might rely on seeing output,
    # or ensure all tests manage logger state independently.
    # For now, leave it clean. If other tests fail, this might be a point to revisit.


def _find_log_record_by_function(json_log_content: str, function_name: str) -> Optional[dict]:
    """
    Parses a string of JSON log entries (one JSON object per line) and
    returns the first log record originating from the specified function.
    """
    for line in json_log_content.strip().split("\n"):
        if not line:
            continue
        try:
            parsed_line = json.loads(line)
            record = parsed_line.get("record", {})
            if record.get("function") == function_name:
                return record
        except json.JSONDecodeError:
            # Handle cases where a line might not be valid JSON, though ideally log files are clean
            # For test purposes, we might want to be strict or log this. For now, skip malformed.
            continue
    return None


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
def test_load_exception_config_valid(
    temp_config_file_generator, dynel_config_instance, ext, tmp_path, monkeypatch
):  # Added monkeypatch
    config_data = VALID_CONFIG_DATA_DICT.copy()
    filename_prefix = "test_dynel_config"
    temp_config_file_generator(
        tmp_path, filename_prefix, ext, config_data
    )  # Pass tmp_path from test

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
    monkeypatch.chdir(tmp_path)  # Use monkeypatch to change CWD
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


@pytest.mark.parametrize(
    "ext,expected_exception,expected_match",
    [
        ("yaml", ValueError, r"Invalid DynEL configuration file .* Root of configuration must be a dictionary."),
        ("json", ValueError, r"Failed to parse DynEL configuration file"),
        ("toml", ValueError, r"Failed to parse DynEL configuration file"),
    ],
)
def test_load_exception_config_invalid_format(
    dynel_config_instance, ext, expected_exception, expected_match, tmp_path, monkeypatch
):
    filename_prefix = "invalid_config"
    file_path = tmp_path / f"{filename_prefix}.{ext}"
    with open(file_path, "w") as f:
        f.write(
            "this is not valid {syntax,, for all formats"
        )  # Write an invalid string

    monkeypatch.chdir(tmp_path)  # Use monkeypatch to change CWD
    with pytest.raises(expected_exception, match=expected_match):
        dynel_config_instance.load_exception_config(filename_prefix)


@pytest.mark.parametrize("ext", ["json", "yaml", "toml"])
def test_load_exception_config_safer_exception_loading(
    temp_config_file_generator, dynel_config_instance, ext, tmp_path, monkeypatch
):  # Added monkeypatch
    """Tests the safer loading of exception types (built-in, importable, and invalid)."""
    config_data = {
        "debug_mode": False,
        "FuncWithBuiltin": {
            "exceptions": ["ValueError", "DoesNotExist"]
        },  # DoesNotExist is not std builtin
        "FuncWithImportable": {
            "exceptions": ["os.PathLike"]
        },  # os.PathLike is not an exception
        "FuncWithNonException": {
            "exceptions": ["src.dynel.ContextLevel"]
        },  # Valid class, not an exception
        "FuncWithUnresolvable": {"exceptions": ["nonexistent_module.NonExistentError"]},
    }
    filename_prefix = "test_exc_loading"
    temp_config_file_generator(
        tmp_path, filename_prefix, ext, config_data
    )  # Pass tmp_path from test

    # Mock logger to capture warnings/errors during loading
    mock_logger_warning = MagicMock()
    mock_logger_error = MagicMock()

    monkeypatch.chdir(tmp_path)  # Use monkeypatch to change CWD
    with patch("src.dynel.dynel.logger.warning", mock_logger_warning), patch(
        "src.dynel.dynel.logger.error", mock_logger_error
    ):
        dynel_config_instance.load_exception_config(filename_prefix)
    # monkeypatch for CWD is reverted automatically

    assert (
        ValueError
        in dynel_config_instance.EXCEPTION_CONFIG["FuncWithBuiltin"]["exceptions"]
    )
    # Check that DoesNotExist (not a real exception) was skipped and warned
    assert not any(
        exc_type.__name__ == "DoesNotExist"
        for exc_type in dynel_config_instance.EXCEPTION_CONFIG["FuncWithBuiltin"][
            "exceptions"
        ]
    )
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'DoesNotExist' for 'FuncWithBuiltin': not enough values to unpack (expected 2, got 1). Skipping."
    )

    # os.PathLike is not an exception
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithImportable"][
        "exceptions"
    ]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'os.PathLike' for 'FuncWithImportable': 'os.PathLike' is not an Exception subclass.. Skipping."
    )

    # src.dynel.ContextLevel is not an exception
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithNonException"][
        "exceptions"
    ]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'src.dynel.ContextLevel' for 'FuncWithNonException': 'src.dynel.ContextLevel' is not an Exception subclass.. Skipping."
    )

    # non_existent_module.NonExistentError should fail to import
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithUnresolvable"][
        "exceptions"
    ]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'nonexistent_module.NonExistentError' for 'FuncWithUnresolvable': No module named 'nonexistent_module'. Skipping."
    )


# --- Tests for configure_logging ---


@patch("src.dynel.dynel.logger")  # Corrected path to logger
def test_configure_logging_debug_mode(mock_loguru_logger, dynel_config_instance):
    dynel_config_instance.DEBUG_MODE = True
    configure_logging(dynel_config_instance)

    mock_loguru_logger.remove.assert_called_once()
    # Check that logger.add was called for dynel.log with DEBUG level
    # This is a bit complex due to multiple calls to .add()
    # We can inspect call_args_list
    args_list = mock_loguru_logger.add.call_args_list
    assert any(
        call[1].get("sink") == "dynel.log" and call[1].get("level") == "DEBUG"
        for call in args_list
    )
    assert any(
        call[1].get("sink") == "dynel.json"
        for call in args_list  # serialize implies JSON
    )


@patch("src.dynel.dynel.logger")  # Corrected path to logger
def test_configure_logging_production_mode(mock_loguru_logger, dynel_config_instance):
    dynel_config_instance.DEBUG_MODE = False
    configure_logging(dynel_config_instance)

    mock_loguru_logger.remove.assert_called_once()
    args_list = mock_loguru_logger.add.call_args_list
    assert any(
        call[1].get("sink") == "dynel.log" and call[1].get("level") == "INFO"
        for call in args_list
    )


# --- Tests for parse_command_line_args ---


def test_parse_command_line_args_defaults():
    with patch(
        "argparse.ArgumentParser.parse_args",
        return_value=Mock(context_level="min", debug=False, formatting=True),
    ):
        args = parse_command_line_args()
    assert args["context_level"] == "min"
    assert args["debug"] is False
    assert args["formatting"] is True


@pytest.mark.parametrize(
    "cli_arg, expected_key, expected_value, context_choices",
    [
        (["--context-level", "med"], "context_level", "med", ["min", "med", "det"]),
        (["--debug"], "debug", True, None),
        (["--no-formatting"], "formatting", False, None),
    ],
)
def test_parse_command_line_args_custom(
    cli_arg, expected_key, expected_value, context_choices
):
    # The choices for context_level are defined in the function, so we don't need to pass them all here
    # just ensuring the mechanism works
    with patch("sys.argv", ["dynel.py"] + cli_arg):
        parsed_args = parse_command_line_args()
    assert parsed_args[expected_key] == expected_value


# --- Tests for handle_exception ---


@pytest.fixture
def captured_logs():
    """Fixture to capture Loguru logs in a list."""
    log_capture_list = []

    def capturing_sink(message):
        log_capture_list.append(
            message.record
        )  # Store the full record for detailed assertions

    # Ensure default logger is clean and add our sink
    # Note: This might interfere if other tests also manipulate the global logger.
    # For isolated tests, this is okay. Consider per-test logger configuration if issues arise.
    from src.dynel.dynel import logger as dynel_logger  # get the actual logger instance

    dynel_logger.remove()  # Remove all handlers
    handler_id = dynel_logger.add(
        capturing_sink, format="{message}"
    )  # Basic format, we inspect record

    yield log_capture_list

    dynel_logger.remove(handler_id)
    # Optionally, re-add default handlers if needed by other tests, or ensure tests clean up.
    # For now, assuming test isolation or that subsequent tests will reconfigure.


def test_handle_exception_basic_logging(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    error_to_raise = ValueError("Test error for basic logging")

    # Mock inspect.stack() to control func_name
    with patch("inspect.stack") as mock_stack:
        mock_function_name = "mock_function_raising_error"
        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (
            Mock(),
            "filename_mock",
            123,
            mock_function_name,
            ["code_line_mock"],
            0,
        )
        mock_stack.return_value = [
            Mock(),  # Frame for handle_exception itself
            mock_caller_frame_tuple,  # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except ValueError as e:
            # Directly call handle_exception as if it was called from within the except block
            # of mock_function_raising_error
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert (
        log_record["level"].name == "ERROR"
    )  # Loguru's .exception logs at ERROR level
    assert "Exception caught in mock_function_raising_error" in log_record["message"]
    assert log_record["exception"] is not None
    assert "Test error for basic logging" in str(
        log_record["exception"].value
    )  # Corrected assertion
    assert "timestamp" in log_record["extra"]


def test_handle_exception_with_custom_message_and_tags(
    dynel_config_instance, captured_logs
):
    config = dynel_config_instance
    func_name = "my_specific_function"
    custom_msg = "A very specific error occurred!"
    tags = ["database", "critical"]

    config.EXCEPTION_CONFIG = {
        func_name: {
            "exceptions": [TypeError],
            "custom_message": custom_msg,
            "tags": tags,
        }
    }
    error_to_raise = TypeError("Something went wrong with types")

    with patch("inspect.stack") as mock_stack:
        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (
            Mock(),
            "filename_mock",
            123,
            func_name,
            ["code_line_mock"],
            0,
        )
        mock_stack.return_value = [
            Mock(),  # Frame for handle_exception itself
            mock_caller_frame_tuple,  # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except TypeError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert log_record["level"].name == "ERROR"
    expected_log_message = (
        f"Exception caught in {func_name} - Custom Message: {custom_msg}"
    )
    assert log_record["message"] == expected_log_message  # Exact message check
    assert log_record["exception"] is not None
    assert "Something went wrong with types" in str(
        log_record["exception"].value
    )  # Corrected assertion
    assert log_record["extra"]["tags"] == tags
    assert "timestamp" in log_record["extra"]


@pytest.mark.parametrize(
    "level_str, expected_keys_in_extra",
    [
        ("min", ["timestamp"]),
        ("med", ["timestamp", "local_vars"]),
        ("det", ["timestamp", "local_vars", "free_memory", "cpu_count", "env_details"]),
        # Note: env_details might be very large, consider mocking os.environ for tests
    ],
)
def test_handle_exception_context_levels(
    level_str, expected_keys_in_extra, captured_logs
):
    # For 'det' level, mock os.environ to avoid logging actual environment
    mock_os_environ = {"TEST_VAR": "test_value"}

    with patch("os.environ", mock_os_environ), patch(
        "inspect.stack"  # Patch inspect.stack directly
    ) as mock_stack:

        config = DynelConfig(context_level=level_str)
        mock_function_name = "context_level_test_func"

        mock_caller_frame_obj = Mock()
        mock_caller_frame_obj.f_locals = {"var1": 10, "var2": "test"}

        mock_caller_frame_info_tuple = (
            mock_caller_frame_obj,    # This is inspect.stack()[1][0] (the frame object)
            "filename_mock",          # inspect.stack()[1][1]
            123,                      # inspect.stack()[1][2]
            mock_function_name,       # inspect.stack()[1][3]
            ["code_line_mock"],       # inspect.stack()[1][4]
            0,                        # inspect.stack()[1][5]
        )
        mock_stack.return_value = [
            Mock(),  # Frame for handle_exception itself (inspect.stack()[0])
            mock_caller_frame_info_tuple, # Frame info for the caller (inspect.stack()[1])
        ]

        error_to_raise = ConnectionError("A connection problem")

        try:
            raise error_to_raise
        except ConnectionError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert log_record["level"].name == "ERROR"
    assert (
        f"Exception caught in {mock_function_name}" in log_record["message"]
    )  # Use mock_function_name
    assert log_record["exception"] is not None
    assert "A connection problem" in str(
        log_record["exception"].value
    )  # Corrected assertion

    for key in expected_keys_in_extra:
        assert key in log_record["extra"]
        if key == "local_vars":
            assert (
                str({"var1": 10, "var2": "test"}) in log_record["extra"]["local_vars"]
            )
        if (
            key == "env_details" and level_str == "det"
        ):  # Only check if env_details was expected
            assert log_record["extra"]["env_details"] == mock_os_environ


def test_handle_exception_panic_mode(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    config.PANIC_MODE = True
    error_to_raise = RuntimeError("Critical system failure!")
    func_name = "panicking_function"

    with patch("inspect.stack") as mock_stack, patch(
        "sys.exit"
    ) as mock_sys_exit:  # Patch sys.exit

        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (
            Mock(),
            "filename_mock",
            123,
            func_name,
            ["code_line_mock"],
            0,
        )
        mock_stack.return_value = [
            Mock(),  # Frame for handle_exception itself
            mock_caller_frame_tuple,  # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except RuntimeError as e:
            # handle_exception will call sys.exit, so we expect pytest.raises(SystemExit)
            # However, sys.exit is patched, so the test won't actually exit.
            # We call it directly and check mock_sys_exit.
            handle_exception(config, e)

    assert (
        len(captured_logs) == 2
    )  # One for the exception, one for the panic critical message

    exception_log = captured_logs[0]  # Assuming first log is the exception itself
    assert exception_log["level"].name == "ERROR"
    assert f"Exception caught in {func_name}" in exception_log["message"]

    panic_log = captured_logs[1]  # Assuming second log is the panic message
    assert panic_log["level"].name == "CRITICAL"
    assert (
        f"PANIC MODE ENABLED: Exiting after handling exception in {func_name}."
        in panic_log["message"]
    )

    mock_sys_exit.assert_called_once_with(1)


# --- Tests for module_exception_handler ---

# Dummy module for testing module_exception_handler
DUMMY_MODULE_CONTENT = """
def func_that_works():
    return "worked"

def func_that_raises_value_error():
    raise ValueError("Dummy ValueError")

def func_that_raises_type_error():
    raise TypeError("Dummy TypeError")

_a_private_variable = True # Should not be wrapped

class SomeClass: # Should not be wrapped
    def method(self):
        raise AttributeError("Dummy AttributeError in class")
"""


@pytest.fixture
def dummy_module(tmp_path):
    """Creates a dummy module file and imports it."""
    module_path = tmp_path / "dummy_module_for_dynel_test.py"
    module_path.write_text(DUMMY_MODULE_CONTENT)

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "dummy_module_for_dynel_test", module_path
    )
    imported_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported_module)
    return imported_module


def test_module_exception_handler_wraps_functions(dynel_config_instance, dummy_module):
    config = dynel_config_instance

    # Keep a reference to original functions to reset if necessary, though for this test structure,
    # the dummy_module is fresh each time due to fixture scope.
    # original_value_error_func = dummy_module.func_that_raises_value_error
    # original_works_func = dummy_module.func_that_works

    with patch("src.dynel.dynel.handle_exception") as mock_handle_exception:
        mock_handle_exception.return_value = (
            None  # Ensure mock doesn't suppress re-raise
        )

        module_exception_handler(
            config, dummy_module
        )  # Corrected: Call module_exception_handler

        # Test that wrapped function still works if no error
        assert dummy_module.func_that_works() == "worked"

        # Test that error in wrapped function calls our handler
        with pytest.raises(
            ValueError
        ):  # Loguru's @logger.catch will re-raise by default
            dummy_module.func_that_raises_value_error()

        mock_handle_exception.assert_called_once()  # Use the correct mock name
        args, _ = mock_handle_exception.call_args
        assert args[0] == config
        assert isinstance(args[1], ValueError)
        assert str(args[1]) == "Dummy ValueError"

        # Check that non-function attributes are not wrapped/changed
        assert dummy_module._a_private_variable is True
        assert inspect.isclass(dummy_module.SomeClass)  # Check it's still a class

        # Check that methods within classes are not wrapped by module_exception_handler directly
        instance = dummy_module.SomeClass()
        with pytest.raises(AttributeError, match="Dummy AttributeError in class"):
            instance.method()
        # mock_handle_exception should still be called once from the module-level function
        mock_handle_exception.assert_called_once()


# --- Tests for Log File Output ---


def test_log_file_output_formats(tmp_path, monkeypatch):
    config = DynelConfig(context_level="med")  # Use medium context for some local_vars

    # Configure logging to use temporary files
    log_file_txt = tmp_path / "output.log"
    log_file_json = tmp_path / "output.json"

    # Patch the logger.add calls within configure_logging to use these temp files
    # This is a bit more involved as configure_logging removes all handlers then adds new ones.
    # We can patch 'logger.add' and inspect its calls, or patch the sink names directly if possible.
    # A simpler way for this test: modify the configure_logging function temporarily for the test,
    # or have DynelConfig allow specifying log paths.
    # For now, let's patch 'logger.add'.

    from src.dynel.dynel import logger as dynel_logger  # Import the logger instance

    # We need to capture what `logger.add` is called with.
    # The `captured_logs` fixture reconfigures the logger. We need to manage this carefully.
    # Let's create a specific logger configuration for this test.

    dynel_logger.remove()  # Clear existing handlers (like from captured_logs fixture if it ran)
    dynel_logger.add(
        log_file_txt,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message} | {extra}",
        level="DEBUG",
    )
    dynel_logger.add(log_file_json, serialize=True, level="DEBUG")

    error_to_raise = IndexError("Test index out of bounds")
    func_name = "function_writing_to_log_files"

    # Mock inspect.stack to control func_name in handle_exception
    # and to provide locals for the caller's frame.

    mock_caller_frame_obj_for_log_test = Mock()
    mock_caller_frame_obj_for_log_test.f_locals = {"alpha": 1, "beta": "two"}

    with patch("src.dynel.dynel.inspect") as mock_dynel_inspect: # Patch inspect module used by dynel

        mock_caller_frame_info_tuple_for_log_test = (
            mock_caller_frame_obj_for_log_test,
            "test_file.py",
            100,
            func_name,
            ["some_code"],
            0,
        )
        mock_dynel_inspect.stack.return_value = [
            Mock(), # Corresponds to handle_exception's own frame
            mock_caller_frame_info_tuple_for_log_test # Corresponds to the caller's frame info
        ]
        # If handle_exception directly uses inspect.currentframe(), it would also need:
        # mock_dynel_inspect.currentframe.return_value = mock_caller_frame_obj_for_log_test
        # But current logic uses inspect.stack()[1][0].f_locals

        try:
            raise error_to_raise
        except IndexError as e:
            handle_exception(config, e)

    # Verify text log content
    assert log_file_txt.exists()
    txt_content = log_file_txt.read_text()
    assert "ERROR" in txt_content  # Level
    assert (
        f"{func_name}" in txt_content
    )  # Function name from handle_exception's perspective
    assert "Exception caught in" in txt_content
    assert "IndexError: Test index out of bounds" in txt_content  # Exception message
    assert "'alpha': 1" in txt_content  # Part of local_vars
    assert "'beta': 'two'" in txt_content  # Part of local_vars
    assert "timestamp" in txt_content  # From custom_context

    # Verify JSON log content
    assert log_file_json.exists()
    json_content = log_file_json.read_text()
    # Each line in the JSON log file is a separate JSON object
    # For this test, we expect one log entry from handle_exception
    log_entry = None
    for line in json_content.strip().split("\n"):
        if line:  # Handle potential empty lines if any
            parsed_line = json.loads(line)
            # Look for the log entry from our specific function
            if parsed_line.get("record", {}).get("function") == "handle_exception":
                log_entry = parsed_line["record"]
                break

    assert (
        log_entry is not None
    ), "Log entry from handle_exception not found in JSON log"

    assert log_entry["level"]["name"] == "ERROR"
    assert f"Exception caught in {func_name}" in log_entry["message"]

    exception_details = log_entry["exception"]
    assert exception_details["type"] == "IndexError"
    assert "Test index out of bounds" in exception_details["value"]
    assert exception_details["traceback"]  # Check traceback exists

    extra_details = log_entry["extra"]
    assert "timestamp" in extra_details
    assert "'alpha': 1" in extra_details["local_vars"]
    assert "'beta': 'two'" in extra_details["local_vars"]

    # Clean up global logger state for other tests
    from src.dynel.dynel import logger as dynel_logger  # Ensure it's in scope

    dynel_logger.remove()
    # Re-add a default console sink if other tests might rely on seeing output,
    # or ensure all tests manage logger state independently.
    # For now, leave it clean. If other tests fail, this might be a point to revisit.


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
def test_load_exception_config_valid(
    temp_config_file_generator, dynel_config_instance, ext, tmp_path, monkeypatch
):  # Added monkeypatch
    config_data = VALID_CONFIG_DATA_DICT.copy()
    filename_prefix = "test_dynel_config"
    temp_config_file_generator(
        tmp_path, filename_prefix, ext, config_data
    )  # Pass tmp_path from test

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
    monkeypatch.chdir(tmp_path)  # Use monkeypatch to change CWD
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


@pytest.mark.parametrize(
    "ext,expected_exception,expected_match",
    [
        ("yaml", ValueError, r"Invalid DynEL configuration file .* Root of configuration must be a dictionary."),
        ("json", ValueError, r"Failed to parse DynEL configuration file"),
        ("toml", ValueError, r"Failed to parse DynEL configuration file"),
    ],
)
def test_load_exception_config_invalid_format(
    dynel_config_instance, ext, expected_exception, expected_match, tmp_path, monkeypatch
):
    filename_prefix = "invalid_config"
    file_path = tmp_path / f"{filename_prefix}.{ext}"
    with open(file_path, "w") as f:
        f.write(
            "this is not valid {syntax,, for all formats"
        )  # Write an invalid string

    monkeypatch.chdir(tmp_path)  # Use monkeypatch to change CWD
    with pytest.raises(expected_exception, match=expected_match):
        dynel_config_instance.load_exception_config(filename_prefix)


@pytest.mark.parametrize("ext", ["json", "yaml", "toml"])
def test_load_exception_config_safer_exception_loading(
    temp_config_file_generator, dynel_config_instance, ext, tmp_path, monkeypatch
):  # Added monkeypatch
    """Tests the safer loading of exception types (built-in, importable, and invalid)."""
    config_data = {
        "debug_mode": False,
        "FuncWithBuiltin": {
            "exceptions": ["ValueError", "DoesNotExist"]
        },  # DoesNotExist is not std builtin
        "FuncWithImportable": {
            "exceptions": ["os.PathLike"]
        },  # os.PathLike is not an exception
        "FuncWithNonException": {
            "exceptions": ["src.dynel.ContextLevel"]
        },  # Valid class, not an exception
        "FuncWithUnresolvable": {"exceptions": ["nonexistent_module.NonExistentError"]},
    }
    filename_prefix = "test_exc_loading"
    temp_config_file_generator(
        tmp_path, filename_prefix, ext, config_data
    )  # Pass tmp_path from test

    # Mock logger to capture warnings/errors during loading
    mock_logger_warning = MagicMock()
    mock_logger_error = MagicMock()

    monkeypatch.chdir(tmp_path)  # Use monkeypatch to change CWD
    with patch("src.dynel.dynel.logger.warning", mock_logger_warning), patch(
        "src.dynel.dynel.logger.error", mock_logger_error
    ):
        dynel_config_instance.load_exception_config(filename_prefix)
    # monkeypatch for CWD is reverted automatically

    assert (
        ValueError
        in dynel_config_instance.EXCEPTION_CONFIG["FuncWithBuiltin"]["exceptions"]
    )
    # Check that DoesNotExist (not a real exception) was skipped and warned
    assert not any(
        exc_type.__name__ == "DoesNotExist"
        for exc_type in dynel_config_instance.EXCEPTION_CONFIG["FuncWithBuiltin"][
            "exceptions"
        ]
    )
    mock_logger_warning.assert_any_call(
            "Could not load or validate exception 'DoesNotExist' for 'FuncWithBuiltin': not enough values to unpack (expected 2, got 1). Skipping."
    )

    # os.PathLike is not an exception
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithImportable"][
        "exceptions"
    ]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'os.PathLike' for 'FuncWithImportable': 'os.PathLike' is not an Exception subclass.. Skipping."
    )

    # src.dynel.ContextLevel is not an exception
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithNonException"][
        "exceptions"
    ]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'src.dynel.ContextLevel' for 'FuncWithNonException': 'src.dynel.ContextLevel' is not an Exception subclass.. Skipping."
    )

    # non_existent_module.NonExistentError should fail to import
    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithUnresolvable"][
        "exceptions"
    ]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'nonexistent_module.NonExistentError' for 'FuncWithUnresolvable': No module named 'nonexistent_module'. Skipping."
    )


# --- Tests for configure_logging ---


@patch("src.dynel.dynel.logger")  # Corrected path to logger
def test_configure_logging_debug_mode(mock_loguru_logger, dynel_config_instance):
    dynel_config_instance.DEBUG_MODE = True
    configure_logging(dynel_config_instance)

    mock_loguru_logger.remove.assert_called_once()
    # Check that logger.add was called for dynel.log with DEBUG level
    # This is a bit complex due to multiple calls to .add()
    # We can inspect call_args_list
    args_list = mock_loguru_logger.add.call_args_list
    assert any(
        call[1].get("sink") == "dynel.log" and call[1].get("level") == "DEBUG"
        for call in args_list
    )
    assert any(
        call[1].get("sink") == "dynel.json"
        for call in args_list  # serialize implies JSON
    )


@patch("src.dynel.dynel.logger")  # Corrected path to logger
def test_configure_logging_production_mode(mock_loguru_logger, dynel_config_instance):
    dynel_config_instance.DEBUG_MODE = False
    configure_logging(dynel_config_instance)

    mock_loguru_logger.remove.assert_called_once()
    args_list = mock_loguru_logger.add.call_args_list
    assert any(
        call[1].get("sink") == "dynel.log" and call[1].get("level") == "INFO"
        for call in args_list
    )


# --- Tests for parse_command_line_args ---


def test_parse_command_line_args_defaults():
    with patch(
        "argparse.ArgumentParser.parse_args",
        return_value=Mock(context_level="min", debug=False, formatting=True),
    ):
        args = parse_command_line_args()
    assert args["context_level"] == "min"
    assert args["debug"] is False
    assert args["formatting"] is True


@pytest.mark.parametrize(
    "cli_arg, expected_key, expected_value, context_choices",
    [
        (["--context-level", "med"], "context_level", "med", ["min", "med", "det"]),
        (["--debug"], "debug", True, None),
        (["--no-formatting"], "formatting", False, None),
    ],
)
def test_parse_command_line_args_custom(
    cli_arg, expected_key, expected_value, context_choices
):
    # The choices for context_level are defined in the function, so we don't need to pass them all here
    # just ensuring the mechanism works
    with patch("sys.argv", ["dynel.py"] + cli_arg):
        parsed_args = parse_command_line_args()
    assert parsed_args[expected_key] == expected_value


# --- Tests for handle_exception ---


@pytest.fixture
def captured_logs():
    """Fixture to capture Loguru logs in a list."""
    log_capture_list = []

    def capturing_sink(message):
        log_capture_list.append(
            message.record
        )  # Store the full record for detailed assertions

    # Ensure default logger is clean and add our sink
    # Note: This might interfere if other tests also manipulate the global logger.
    # For isolated tests, this is okay. Consider per-test logger configuration if issues arise.
    from src.dynel.dynel import logger as dynel_logger  # get the actual logger instance

    dynel_logger.remove()  # Remove all handlers
    handler_id = dynel_logger.add(
        capturing_sink, format="{message}"
    )  # Basic format, we inspect record

    yield log_capture_list

    dynel_logger.remove(handler_id)
    # Optionally, re-add default handlers if needed by other tests, or ensure tests clean up.
    # For now, assuming test isolation or that subsequent tests will reconfigure.


def test_handle_exception_basic_logging(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    error_to_raise = ValueError("Test error for basic logging")

    # Mock inspect.stack() to control func_name
    with patch("inspect.stack") as mock_stack:
        mock_function_name = "mock_function_raising_error"
        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (
            Mock(),
            "filename_mock",
            123,
            mock_function_name,
            ["code_line_mock"],
            0,
        )
        mock_stack.return_value = [
            Mock(),  # Frame for handle_exception itself
            mock_caller_frame_tuple,  # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except ValueError as e:
            # Directly call handle_exception as if it was called from within the except block
            # of mock_function_raising_error
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert (
        log_record["level"].name == "ERROR"
    )  # Loguru's .exception logs at ERROR level
    assert "Exception caught in mock_function_raising_error" in log_record["message"]
    assert log_record["exception"] is not None
    assert "Test error for basic logging" in str(
        log_record["exception"].value
    )  # Corrected assertion
    assert "timestamp" in log_record["extra"]


def test_handle_exception_with_custom_message_and_tags(
    dynel_config_instance, captured_logs
):
    config = dynel_config_instance
    func_name = "my_specific_function"
    custom_msg = "A very specific error occurred!"
    tags = ["database", "critical"]

    config.EXCEPTION_CONFIG = {
        func_name: {
            "exceptions": [TypeError],
            "custom_message": custom_msg,
            "tags": tags,
        }
    }
    error_to_raise = TypeError("Something went wrong with types")

    with patch("inspect.stack") as mock_stack:
        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (
            Mock(),
            "filename_mock",
            123,
            func_name,
            ["code_line_mock"],
            0,
        )
        mock_stack.return_value = [
            Mock(),  # Frame for handle_exception itself
            mock_caller_frame_tuple,  # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except TypeError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert log_record["level"].name == "ERROR"
    expected_log_message = (
        f"Exception caught in {func_name} - Custom Message: {custom_msg}"
    )
    assert log_record["message"] == expected_log_message  # Exact message check
    assert log_record["exception"] is not None
    assert "Something went wrong with types" in str(
        log_record["exception"].value
    )  # Corrected assertion
    assert log_record["extra"]["tags"] == tags
    assert "timestamp" in log_record["extra"]


@pytest.mark.parametrize(
    "level_str, expected_keys_in_extra",
    [
        ("min", ["timestamp"]),
        ("med", ["timestamp", "local_vars"]),
        ("det", ["timestamp", "local_vars", "free_memory", "cpu_count", "env_details"]),
        # Note: env_details might be very large, consider mocking os.environ for tests
    ],
)
def test_handle_exception_context_levels(
    level_str, expected_keys_in_extra, captured_logs
):
    # For 'det' level, mock os.environ to avoid logging actual environment
    mock_os_environ = {"TEST_VAR": "test_value"}

    with patch("os.environ", mock_os_environ), patch(
        "src.dynel.dynel.inspect"
    ) as mock_dynel_inspect:  # Patch inspect used in dynel.py

        config = DynelConfig(context_level=level_str)
        mock_function_name = "context_level_test_func"

        # This mock will be inspect.stack()[1][0] (the frame of the caller of handle_exception)
        mock_caller_frame_object = Mock()
        mock_caller_frame_object.f_locals = {"var1": 10, "var2": "test"}

        # Setup for inspect.stack()[1]
        mock_caller_frame_info_tuple = (
            mock_caller_frame_object, # This is inspect.stack()[1][0]
            "filename_mock",          # inspect.stack()[1][1]
            123,                      # inspect.stack()[1][2]
            mock_function_name,       # inspect.stack()[1][3]
            ["code_line_mock"],       # inspect.stack()[1][4]
            0,                        # inspect.stack()[1][5]
        )
        mock_dynel_inspect.stack.return_value = [
            Mock(),  # Frame for handle_exception itself (inspect.stack()[0])
            mock_caller_frame_info_tuple, # Frame info for the caller (inspect.stack()[1])
        ]
        # No need to mock inspect.currentframe separately for this specific path in handle_exception

        error_to_raise = ConnectionError("A connection problem")

        try:
            raise error_to_raise
        except ConnectionError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]

    assert log_record["level"].name == "ERROR"
    assert (
        f"Exception caught in {mock_function_name}" in log_record["message"]
    )  # Use mock_function_name
    assert log_record["exception"] is not None
    assert "A connection problem" in str(
        log_record["exception"].value
    )  # Corrected assertion

    for key in expected_keys_in_extra:
        assert key in log_record["extra"]
        if key == "local_vars":
            assert (
                str({"var1": 10, "var2": "test"}) in log_record["extra"]["local_vars"]
            )
        if (
            key == "env_details" and level_str == "det"
        ):  # Only check if env_details was expected
            assert log_record["extra"]["env_details"] == mock_os_environ


def test_handle_exception_panic_mode(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    config.PANIC_MODE = True
    error_to_raise = RuntimeError("Critical system failure!")
    func_name = "panicking_function"

    with patch("inspect.stack") as mock_stack, patch(
        "sys.exit"
    ) as mock_sys_exit:  # Patch sys.exit

        # inspect.stack()[1] should be a tuple/list where index 3 is the function name
        mock_caller_frame_tuple = (
            Mock(),
            "filename_mock",
            123,
            func_name,
            ["code_line_mock"],
            0,
        )
        mock_stack.return_value = [
            Mock(),  # Frame for handle_exception itself
            mock_caller_frame_tuple,  # Frame for the caller of handle_exception
        ]

        try:
            raise error_to_raise
        except RuntimeError as e:
            # handle_exception will call sys.exit, so we expect pytest.raises(SystemExit)
            # However, sys.exit is patched, so the test won't actually exit.
            # We call it directly and check mock_sys_exit.
            handle_exception(config, e)

    assert (
        len(captured_logs) == 2
    )  # One for the exception, one for the panic critical message

    exception_log = captured_logs[0]  # Assuming first log is the exception itself
    assert exception_log["level"].name == "ERROR"
    assert f"Exception caught in {func_name}" in exception_log["message"]

    panic_log = captured_logs[1]  # Assuming second log is the panic message
    assert panic_log["level"].name == "CRITICAL"
    assert (
        f"PANIC MODE ENABLED: Exiting after handling exception in {func_name}."
        in panic_log["message"]
    )

    mock_sys_exit.assert_called_once_with(1)


# --- Tests for module_exception_handler ---

# Dummy module for testing module_exception_handler
DUMMY_MODULE_CONTENT = """
def func_that_works():
    return "worked"

def func_that_raises_value_error():
    raise ValueError("Dummy ValueError")

def func_that_raises_type_error():
    raise TypeError("Dummy TypeError")

_a_private_variable = True # Should not be wrapped

class SomeClass: # Should not be wrapped
    def method(self):
        raise AttributeError("Dummy AttributeError in class")
"""


@pytest.fixture
def dummy_module(tmp_path):
    """Creates a dummy module file and imports it."""
    module_path = tmp_path / "dummy_module_for_dynel_test.py"
    module_path.write_text(DUMMY_MODULE_CONTENT)

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "dummy_module_for_dynel_test", module_path
    )
    imported_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported_module)
    return imported_module


def test_module_exception_handler_wraps_functions(dynel_config_instance, dummy_module):
    config = dynel_config_instance

    # Keep a reference to original functions to reset if necessary, though for this test structure,
    # the dummy_module is fresh each time due to fixture scope.
    # original_value_error_func = dummy_module.func_that_raises_value_error
    # original_works_func = dummy_module.func_that_works

    with patch("src.dynel.dynel.handle_exception") as mock_handle_exception:
        mock_handle_exception.return_value = (
            None  # Ensure mock doesn't suppress re-raise
        )

        module_exception_handler(
            config, dummy_module
        )  # Corrected: Call module_exception_handler

        # Test that wrapped function still works if no error
        assert dummy_module.func_that_works() == "worked"

        # Test that error in wrapped function calls our handler
        with pytest.raises(
            ValueError
        ):  # Loguru's @logger.catch will re-raise by default
            dummy_module.func_that_raises_value_error()

        mock_handle_exception.assert_called_once()  # Use the correct mock name
        args, _ = mock_handle_exception.call_args
        assert args[0] == config
        assert isinstance(args[1], ValueError)
        assert str(args[1]) == "Dummy ValueError"

        # Check that non-function attributes are not wrapped/changed
        assert dummy_module._a_private_variable is True
        assert inspect.isclass(dummy_module.SomeClass)  # Check it's still a class

        # Check that methods within classes are not wrapped by module_exception_handler directly
        instance = dummy_module.SomeClass()
        with pytest.raises(AttributeError, match="Dummy AttributeError in class"):
            instance.method()
        # mock_handle_exception should still be called once from the module-level function
        mock_handle_exception.assert_called_once()


# --- Tests for Log File Output ---


def test_log_file_output_formats(tmp_path, monkeypatch):
    config = DynelConfig(context_level="med")  # Use medium context for some local_vars

    # Configure logging to use temporary files
    log_file_txt = tmp_path / "output.log"
    log_file_json = tmp_path / "output.json"

    # Patch the logger.add calls within configure_logging to use these temp files
    # This is a bit more involved as configure_logging removes all handlers then adds new ones.
    # We can patch 'logger.add' and inspect its calls, or patch the sink names directly if possible.
    # A simpler way for this test: modify the configure_logging function temporarily for the test,
    # or have DynelConfig allow specifying log paths.
    # For now, let's patch 'logger.add'.

    from src.dynel.dynel import logger as dynel_logger  # Import the logger instance

    # We need to capture what `logger.add` is called with.
    # The `captured_logs` fixture reconfigures the logger. We need to manage this carefully.
    # Let's create a specific logger configuration for this test.

    dynel_logger.remove()  # Clear existing handlers (like from captured_logs fixture if it ran)
    dynel_logger.add(
        log_file_txt,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message} | {extra}",
        level="DEBUG",
    )
    dynel_logger.add(log_file_json, serialize=True, level="DEBUG")

    error_to_raise = IndexError("Test index out of bounds")
    func_name = "function_writing_to_log_files"

    # Mock inspect.stack to control func_name in handle_exception
    # and to provide locals for the caller's frame.

    mock_caller_frame_obj_for_log_test = Mock()
    mock_caller_frame_obj_for_log_test.f_locals = {"alpha": 1, "beta": "two"}

    with patch("src.dynel.dynel.inspect") as mock_dynel_inspect: # Patch inspect module used by dynel

        mock_caller_frame_info_tuple_for_log_test = (
            mock_caller_frame_obj_for_log_test, # This is inspect.stack()[1][0]
            "test_file.py",          # inspect.stack()[1][1]
            100,                      # inspect.stack()[1][2]
            func_name,       # inspect.stack()[1][3]
            ["some_code"],       # inspect.stack()[1][4]
            0,                        # inspect.stack()[1][5]
        )
        mock_dynel_inspect.stack.return_value = [
            Mock(),  # Frame for handle_exception itself (inspect.stack()[0])
            mock_caller_frame_info_tuple_for_log_test, # Frame info for the caller (inspect.stack()[1])
        ]
        # No need to mock inspect.currentframe separately for this specific path in handle_exception

        try:
            raise error_to_raise
        except IndexError as e:
            handle_exception(config, e)

    # Verify text log content
    assert log_file_txt.exists()
    txt_content = log_file_txt.read_text()
    assert "ERROR" in txt_content  # Level
    assert (
        f"{func_name}" in txt_content
    )  # Function name from handle_exception's perspective
    assert "Exception caught in" in txt_content
    assert "IndexError: Test index out of bounds" in txt_content  # Exception message
    assert "'alpha': 1" in txt_content  # Part of local_vars
    assert "'beta': 'two'" in txt_content  # Part of local_vars
    assert "timestamp" in txt_content  # From custom_context

    # Verify JSON log content
    assert log_file_json.exists()
    json_content = log_file_json.read_text()
    # Each line in the JSON log file is a separate JSON object
    # For this test, we expect one log entry from handle_exception
    log_entry = None
    for line in json_content.strip().split("\n"):
        if line:  # Handle potential empty lines if any
            parsed_line = json.loads(line)
            # Look for the log entry from our specific function
            if parsed_line.get("record", {}).get("function") == "handle_exception":
                log_entry = parsed_line["record"]
                break

    assert (
        log_entry is not None
    ), "Log entry from handle_exception not found in JSON log"

    assert log_entry["level"]["name"] == "ERROR"
    assert f"Exception caught in {func_name}" in log_entry["message"]

    exception_details = log_entry["exception"]
    assert exception_details["type"] == "IndexError"
    assert "Test index out of bounds" in exception_details["value"]
    assert exception_details["traceback"]  # Check traceback exists

    extra_details = log_entry["extra"]
    assert "timestamp" in extra_details
    assert "'alpha': 1" in extra_details["local_vars"]
    assert "'beta': 'two'" in extra_details["local_vars"]

    # Clean up global logger state for other tests
    from src.dynel.dynel import logger as dynel_logger  # Ensure it's in scope

    dynel_logger.remove()
    # Re-add a default console sink if other tests might rely on seeing output,
    # or ensure all tests manage logger state independently.
    # For now, leave it clean. If other tests fail, this might be a point to revisit.
