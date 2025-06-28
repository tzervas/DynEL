import pytest
import inspect
from unittest.mock import patch, Mock, MagicMock
import importlib.util # For dummy_module fixture

# Importing from the new locations in src.dynel
from src.dynel.config import DynelConfig, ContextLevel
from src.dynel.exception_handling import handle_exception, module_exception_handler
# Import the actual logger instance for direct manipulation in tests if needed
from loguru import logger as dynel_logger_instance # Renamed


@pytest.fixture
def dynel_config_instance():
    """Returns a default DynelConfig instance."""
    return DynelConfig()

@pytest.fixture
def captured_logs():
    """Fixture to capture Loguru logs in a list."""
    log_capture_list = []

    def capturing_sink(message):
        log_capture_list.append(message.record)

    # Use the specific logger instance from the dynel package
    handler_id = dynel_logger_instance.add(capturing_sink, format="{message}")
    yield log_capture_list
    dynel_logger_instance.remove(handler_id)

# --- Tests for handle_exception ---

def test_handle_exception_basic_logging(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    error_to_raise = ValueError("Test error for basic logging")

    with patch("src.dynel.exception_handling.inspect.stack") as mock_stack: # Patch inspect in exception_handling
        mock_function_name = "mock_function_raising_error"
        mock_caller_frame_tuple = (Mock(), "filename_mock", 123, mock_function_name, ["code_line_mock"], 0)
        mock_stack.return_value = [Mock(), mock_caller_frame_tuple]

        try:
            raise error_to_raise
        except ValueError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]
    assert log_record["level"].name == "ERROR"
    assert "Exception caught in mock_function_raising_error" in log_record["message"]
    assert log_record["exception"] is not None
    assert "Test error for basic logging" in str(log_record["exception"].value)
    assert "timestamp" in log_record["extra"]


def test_handle_exception_with_custom_message_and_tags(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    func_name = "my_specific_function"
    custom_msg = "A very specific error occurred!"
    tags = ["database", "critical"]

    config.EXCEPTION_CONFIG = {
        func_name: {"exceptions": [TypeError], "custom_message": custom_msg, "tags": tags}
    }
    error_to_raise = TypeError("Something went wrong with types")

    with patch("src.dynel.exception_handling.inspect.stack") as mock_stack: # Patch inspect in exception_handling
        mock_caller_frame_tuple = (Mock(), "filename_mock", 123, func_name, ["code_line_mock"], 0)
        mock_stack.return_value = [Mock(), mock_caller_frame_tuple]

        try:
            raise error_to_raise
        except TypeError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]
    assert log_record["level"].name == "ERROR"
    expected_log_message = f"Exception caught in {func_name} - Custom Message: {custom_msg}"
    assert log_record["message"] == expected_log_message
    assert log_record["exception"] is not None
    assert "Something went wrong with types" in str(log_record["exception"].value)
    assert log_record["extra"]["tags"] == tags
    assert "timestamp" in log_record["extra"]


@pytest.mark.parametrize(
    "level_str, expected_keys_in_extra",
    [
        ("min", ["timestamp"]),
        ("med", ["timestamp", "local_vars"]),
        ("det", ["timestamp", "local_vars", "free_memory", "cpu_count", "env_details"]),
    ],
)
def test_handle_exception_context_levels(level_str, expected_keys_in_extra, captured_logs, monkeypatch): # Added monkeypatch
    mock_os_environ = {"TEST_VAR": "test_value"}
    # Patch os.environ where it's used: in src.dynel.exception_handling
    monkeypatch.setattr("src.dynel.exception_handling.os.environ", mock_os_environ)
    # Patch os.sysconf and os.cpu_count as well
    monkeypatch.setattr("src.dynel.exception_handling.os.sysconf", lambda name: 1024 if name == "SC_PAGE_SIZE" else 1000 if name == "SC_AVPHYS_PAGES" else 0) # Mock sysconf
    monkeypatch.setattr("src.dynel.exception_handling.os.cpu_count", lambda: 4) # Mock cpu_count


    with patch("src.dynel.exception_handling.inspect.stack") as mock_stack: # Patch inspect in exception_handling
        config = DynelConfig(context_level=level_str)
        mock_function_name = "context_level_test_func"
        mock_caller_frame_object = Mock()
        mock_caller_frame_object.f_locals = {"var1": 10, "var2": "test"}
        mock_caller_frame_info_tuple = (mock_caller_frame_object, "filename_mock", 123, mock_function_name, ["code_line_mock"], 0)
        mock_stack.return_value = [Mock(), mock_caller_frame_info_tuple]

        error_to_raise = ConnectionError("A connection problem")
        try:
            raise error_to_raise
        except ConnectionError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 1
    log_record = captured_logs[0]
    assert log_record["level"].name == "ERROR"
    assert f"Exception caught in {mock_function_name}" in log_record["message"]
    assert log_record["exception"] is not None
    assert "A connection problem" in str(log_record["exception"].value)

    for key in expected_keys_in_extra:
        assert key in log_record["extra"]

    if "local_vars" in expected_keys_in_extra:
        assert "'var1': 10" in log_record["extra"]["local_vars"]
        assert "'var2': 'test'" in log_record["extra"]["local_vars"]
    if "env_details" in expected_keys_in_extra:
        assert log_record["extra"]["env_details"] == mock_os_environ


def test_handle_exception_panic_mode(dynel_config_instance, captured_logs):
    config = dynel_config_instance
    config.PANIC_MODE = True
    error_to_raise = RuntimeError("Critical system failure!")
    func_name = "panicking_function"

    # Patch sys.exit within the exception_handling module
    with patch("src.dynel.exception_handling.inspect.stack") as mock_stack, \
         patch("src.dynel.exception_handling.sys.exit") as mock_sys_exit:
        mock_caller_frame_tuple = (Mock(), "filename_mock", 123, func_name, ["code_line_mock"], 0)
        mock_stack.return_value = [Mock(), mock_caller_frame_tuple]

        try:
            raise error_to_raise
        except RuntimeError as e:
            handle_exception(config, e)

    assert len(captured_logs) == 2 # Exception log + panic log
    exception_log = captured_logs[0]
    panic_log = captured_logs[1]

    assert exception_log["level"].name == "ERROR"
    assert f"Exception caught in {func_name}" in exception_log["message"]
    assert panic_log["level"].name == "CRITICAL"
    assert f"PANIC MODE ENABLED: Exiting after handling exception in {func_name}." in panic_log["message"]
    mock_sys_exit.assert_called_once_with(1)


# --- Tests for module_exception_handler ---

DUMMY_MODULE_CONTENT = """
def func_that_works():
    return "worked"

def func_that_raises_value_error():
    raise ValueError("Dummy ValueError")

_a_private_variable = True
class SomeClass:
    def method(self):
        raise AttributeError("Dummy AttributeError in class")
"""

@pytest.fixture
def dummy_module(tmp_path):
    module_path = tmp_path / "dummy_module_for_dynel_test.py"
    module_path.write_text(DUMMY_MODULE_CONTENT)
    spec = importlib.util.spec_from_file_location("dummy_module_for_dynel_test", module_path)
    imported_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported_module)
    return imported_module

def test_module_exception_handler_wraps_functions(dynel_config_instance, dummy_module, captured_logs):
    config = dynel_config_instance
    # Patch handle_exception where it's called by module_exception_handler's _onerror_handler
    # which is within src.dynel.exception_handling
    with patch("src.dynel.exception_handling.handle_exception") as mock_handle_exception:
        # Mock logger.debug as well if checking debug logs from module_exception_handler
        with patch("src.dynel.exception_handling.logger.debug") as mock_logger_debug:
            module_exception_handler(config, dummy_module)

            assert dummy_module.func_that_works() == "worked"
            with pytest.raises(ValueError, match="Dummy ValueError"):
                dummy_module.func_that_raises_value_error()

            mock_handle_exception.assert_called_once()
            args, _ = mock_handle_exception.call_args
            assert args[0] == config
            assert isinstance(args[1], ValueError)
            assert str(args[1]) == "Dummy ValueError"

            if config.DEBUG_MODE: # Only assert debug log if debug mode was on (it's off by default for fixture)
                 mock_logger_debug.assert_any_call("Wrapped function: %s in module %s", "func_that_works", "dummy_module_for_dynel_test")
                 mock_logger_debug.assert_any_call("Wrapped function: %s in module %s", "func_that_raises_value_error", "dummy_module_for_dynel_test")


    assert dummy_module._a_private_variable is True
    assert inspect.isclass(dummy_module.SomeClass)
    instance = dummy_module.SomeClass()
    with pytest.raises(AttributeError, match="Dummy AttributeError in class"):
        instance.method()
    # mock_handle_exception should still be called once from the module-level function that raised
    mock_handle_exception.assert_called_once()


def test_module_exception_handler_debug_logging(dynel_config_instance, dummy_module):
    config = dynel_config_instance
    config.DEBUG_MODE = True # Enable debug mode

    with patch("src.dynel.exception_handling.handle_exception"), \
         patch("src.dynel.exception_handling.logger.debug") as mock_logger_debug: # Patch logger in exception_handling

        module_exception_handler(config, dummy_module)

        # Check if logger.debug was called for the functions in dummy_module
        # Exact module name might vary based on how dummy_module is loaded.
        # The fixture uses "dummy_module_for_dynel_test"
        mock_logger_debug.assert_any_call("Wrapped function: %s in module %s", "func_that_works", "dummy_module_for_dynel_test")
        mock_logger_debug.assert_any_call("Wrapped function: %s in module %s", "func_that_raises_value_error", "dummy_module_for_dynel_test")
        # Ensure it wasn't called for non-functions
        for call_arg in mock_logger_debug.call_args_list:
            assert "_a_private_variable" not in call_arg[0][1]
            assert "SomeClass" not in call_arg[0][1]
