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
            assert "_a_private_variable" not in call_arg[0][1] # Corrected assertion for string check
            assert "SomeClass" not in call_arg[0][1] # Corrected assertion for string check


# --- Tests for New Behavior Implementations ---

@pytest.fixture
def config_with_behaviors(tmp_path):
    """
    Provides a DynelConfig instance with preloaded behavior configurations
    and sets up a temporary logs directory.
    """
    config = DynelConfig()
    # Create a temporary logs directory for specific file logging
    # This path needs to be accessible by the code being tested.
    # We assume for PoC that the log file paths in config are relative like "logs/error.log"
    # or absolute. For testing, we make them relative to tmp_path.
    log_dir = tmp_path / "logs"
    log_dir.mkdir(exist_ok=True)

    config.EXCEPTION_CONFIG = {
        "behavior_func": {
            "exceptions": [ValueError, TypeError, KeyError],
            "custom_message": "Behavior test error",
            "tags": ["behavior_test"],
            "behaviors": {
                "ValueError": {
                    "add_metadata": {"error_code": "VE001", "source": "validation"},
                    "log_to_specific_file": str(log_dir / "value_errors.log") # Use string path
                },
                "TypeError": {
                    "add_metadata": {"error_code": "TE001", "hint": "Check types"}
                    # No specific log file for TypeError, should go to main only
                },
                "default": { # For KeyError
                    "add_metadata": {"default_applied": True, "severity": "Low"},
                    "log_to_specific_file": str(log_dir / "default_behavior_errors.log")
                }
            }
        }
    }
    return config, log_dir


def test_handle_exception_add_metadata_behavior(config_with_behaviors, captured_logs):
    config, _ = config_with_behaviors
    error_to_raise = ValueError("Test VE with metadata")
    func_name = "behavior_func"

    with patch("src.dynel.exception_handling.inspect.stack") as mock_stack:
        mock_caller_frame_tuple = (Mock(), "filename_mock", 123, func_name, ["code_line_mock"], 0)
        mock_stack.return_value = [Mock(), mock_caller_frame_tuple]
        try:
            raise error_to_raise
        except ValueError as e:
            handle_exception(config, e)

    assert len(captured_logs) >= 1 # Main log
    main_log_record = captured_logs[0] # Assuming first is main if no specific file log for this one

    primary_error_log = next(
        (
            rec
            for rec in captured_logs
            if rec["level"].name == "ERROR"
            and "Exception caught in behavior_func" in rec["message"]
        ),
        None,
    )
    assert primary_error_log is not None, "Primary error log not found"

    assert "error_code" in primary_error_log["extra"]
    assert primary_error_log["extra"]["error_code"] == "VE001"
    assert "source" in primary_error_log["extra"]
    assert primary_error_log["extra"]["source"] == "validation"
    assert "tags" in primary_error_log["extra"] # Ensure tags are still there
    assert primary_error_log["extra"]["tags"] == ["behavior_test"]


def test_handle_exception_log_to_specific_file_behavior(config_with_behaviors, captured_logs, tmp_path):
    config, log_dir = config_with_behaviors
    error_to_raise = ValueError("Test VE for specific file")
    func_name = "behavior_func"
    specific_log_file = log_dir / "value_errors.log"

    # Ensure the specific log file does not exist before the test
    if specific_log_file.exists():
        specific_log_file.unlink()
    assert not specific_log_file.exists()

    with patch("src.dynel.exception_handling.inspect.stack") as mock_stack:
        mock_caller_frame_tuple = (Mock(), "filename_mock", 123, func_name, ["code_line_mock"], 0)
        mock_stack.return_value = [Mock(), mock_caller_frame_tuple]
        try:
            raise error_to_raise
        except ValueError as e:
            handle_exception(config, e)

    # Check main log
    assert any(rec["level"].name == "ERROR" and "Exception caught in behavior_func" in rec["message"] for rec in captured_logs)

    # Check specific log file
    assert specific_log_file.exists()
    with open(specific_log_file, 'r') as f:
        specific_log_content = f.read()

    import json # to parse JSON log lines
    lines = specific_log_content.strip().split('\n')
    assert len(lines) > 0
    specific_log_json = json.loads(lines[0]) # Assuming one log line for PoC

    assert "[Mirrored to " in specific_log_json["message"]
    assert "Test VE for specific file" in specific_log_json["exception"]["value"]
    assert specific_log_json["extra"]["error_code"] == "VE001" # Metadata should also be in specific log
    assert specific_log_json["extra"]["source"] == "validation"


def test_handle_exception_default_behavior_override(config_with_behaviors, captured_logs, tmp_path):
    config, log_dir = config_with_behaviors
    error_to_raise = KeyError("Test KeyError for default behavior")
    func_name = "behavior_func"
    default_log_file = log_dir / "default_behavior_errors.log"

    if default_log_file.exists(): default_log_file.unlink()

    with patch("src.dynel.exception_handling.inspect.stack") as mock_stack:
        mock_caller_frame_tuple = (Mock(), "filename_mock", 123, func_name, ["code_line_mock"], 0)
        mock_stack.return_value = [Mock(), mock_caller_frame_tuple]
        try:
            raise error_to_raise
        except KeyError as e:
            handle_exception(config, e)

    primary_error_log = next(
        (
            rec
            for rec in captured_logs
            if rec["level"].name == "ERROR"
            and "Exception caught in behavior_func" in rec["message"]
        ),
        None,
    )
    assert primary_error_log is not None
    assert primary_error_log["extra"]["default_applied"] is True
    assert primary_error_log["extra"]["severity"] == "Low"
    assert "error_code" not in primary_error_log["extra"] # Should not have VE001

    # Check default specific log file
    assert default_log_file.exists()
    with open(default_log_file, 'r') as f:
        default_log_content = f.read()

    import json
    lines = default_log_content.strip().split('\n')
    assert len(lines) > 0
    default_log_json = json.loads(lines[0])
    assert "[Mirrored to " in default_log_json["message"]
    assert "Test KeyError for default behavior" in default_log_json["exception"]["value"]
    assert default_log_json["extra"]["default_applied"] is True


def test_handle_exception_behavior_only_metadata_no_specific_log(config_with_behaviors, captured_logs, tmp_path):
    config, log_dir = config_with_behaviors
    error_to_raise = TypeError("Test TypeError for metadata only")
    func_name = "behavior_func"

    # Ensure other specific log files are not created by this test
    value_error_log = log_dir / "value_errors.log"
    default_error_log = log_dir / "default_behavior_errors.log"
    if value_error_log.exists(): value_error_log.unlink()
    if default_error_log.exists(): default_error_log.unlink()


    with patch("src.dynel.exception_handling.inspect.stack") as mock_stack:
        mock_caller_frame_tuple = (Mock(), "filename_mock", 123, func_name, ["code_line_mock"], 0)
        mock_stack.return_value = [Mock(), mock_caller_frame_tuple]
        try:
            raise error_to_raise
        except TypeError as e:
            handle_exception(config, e)

    primary_error_log = next(
        (
            rec
            for rec in captured_logs
            if rec["level"].name == "ERROR"
            and "Exception caught in behavior_func" in rec["message"]
        ),
        None,
    )
    assert primary_error_log is not None
    assert primary_error_log["extra"]["error_code"] == "TE001"
    assert primary_error_log["extra"]["hint"] == "Check types"
    assert "default_applied" not in primary_error_log["extra"] # Default metadata should not apply

    # Assert that no specific error log files were created for this TypeError
    assert not value_error_log.exists()
    assert not default_error_log.exists()


DUMMY_MODULE_WITH_CLASSES_CONTENT = """
def module_level_func_good():
    return "module_good"

def module_level_func_bad():
    raise EnvironmentError("Bad environment at module level")

class MyTestClass:
    def __init__(self, val=0):
        self.val = val

    def instance_method_good(self):
        return f"instance_good_{self.val}"

    def instance_method_bad(self):
        if self.val < 0:
            raise ValueError("Negative value in instance_method_bad")
        return "instance_ok_positive_val"

    @staticmethod
    def static_method_good():
        return "static_good"

    @staticmethod
    def static_method_bad():
        raise TypeError("Bad type in static_method_bad")

    @classmethod
    def class_method_good(cls):
        return f"class_good_{cls.__name__}"

    @classmethod
    def class_method_bad(cls):
        raise AttributeError(f"Bad attribute in class_method_bad for {cls.__name__}")

class AnotherClass: # To ensure we iterate over multiple classes
    def another_method_bad(self):
        raise ZeroDivisionError("Dividing by zero in AnotherClass")

_module_private_var = 123
"""

@pytest.fixture
def dummy_module_with_classes(tmp_path):
    module_path = tmp_path / "dummy_module_with_classes_for_dynel_test.py"
    module_path.write_text(DUMMY_MODULE_WITH_CLASSES_CONTENT)
    spec = importlib.util.spec_from_file_location("dummy_module_with_classes_for_dynel_test", module_path)
    imported_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported_module)
    return imported_module


def test_module_exception_handler_wraps_class_methods(dynel_config_instance, dummy_module_with_classes, captured_logs):
    config = dynel_config_instance
    # For this test, we only care that handle_exception is called, not its specific behavior here.
    with patch("src.dynel.exception_handling.handle_exception") as mock_handle_exception:
        module_exception_handler(config, dummy_module_with_classes)

        # Test module-level functions
        assert dummy_module_with_classes.module_level_func_good() == "module_good"
        with pytest.raises(EnvironmentError, match="Bad environment at module level"):
            dummy_module_with_classes.module_level_func_bad()
        mock_handle_exception.assert_any_call(config, pytest.approx(EnvironmentError("Bad environment at module level"), abs=lambda x,y: type(x)==type(y) and x.args==y.args))

        call_count_after_module = mock_handle_exception.call_count

        # Test instance methods
        instance = dummy_module_with_classes.MyTestClass(val=10)
        assert instance.instance_method_good() == "instance_good_10"

        instance_bad = dummy_module_with_classes.MyTestClass(val=-5)
        with pytest.raises(ValueError, match="Negative value in instance_method_bad"):
            instance_bad.instance_method_bad()
        mock_handle_exception.assert_any_call(config, pytest.approx(ValueError("Negative value in instance_method_bad"), abs=lambda x,y: type(x)==type(y) and x.args==y.args))

        call_count_after_instance = mock_handle_exception.call_count
        assert call_count_after_instance > call_count_after_module

        # Test static methods
        assert dummy_module_with_classes.MyTestClass.static_method_good() == "static_good"
        with pytest.raises(TypeError, match="Bad type in static_method_bad"):
            dummy_module_with_classes.MyTestClass.static_method_bad()
        mock_handle_exception.assert_any_call(config, pytest.approx(TypeError("Bad type in static_method_bad"), abs=lambda x,y: type(x)==type(y) and x.args==y.args))

        call_count_after_static = mock_handle_exception.call_count
        assert call_count_after_static > call_count_after_instance

        # Test class methods
        assert dummy_module_with_classes.MyTestClass.class_method_good() == "class_good_MyTestClass"
        with pytest.raises(AttributeError, match="Bad attribute in class_method_bad for MyTestClass"):
            dummy_module_with_classes.MyTestClass.class_method_bad()
        mock_handle_exception.assert_any_call(config, pytest.approx(AttributeError("Bad attribute in class_method_bad for MyTestClass"), abs=lambda x,y: type(x)==type(y) and x.args==y.args))

        call_count_after_class = mock_handle_exception.call_count
        assert call_count_after_class > call_count_after_static

        # Test another class
        another_instance = dummy_module_with_classes.AnotherClass()
        with pytest.raises(ZeroDivisionError, match="Dividing by zero in AnotherClass"):
            another_instance.another_method_bad()
        mock_handle_exception.assert_any_call(config, pytest.approx(ZeroDivisionError("Dividing by zero in AnotherClass"), abs=lambda x,y: type(x)==type(y) and x.args==y.args))

        assert mock_handle_exception.call_count > call_count_after_class

        # Ensure private module variables are not touched
        assert dummy_module_with_classes._module_private_var == 123

        # Ensure config.DEBUG_MODE = True would log wrapping details (visual check or more complex mock)
        config.DEBUG_MODE = True
        mock_logger_debug = MagicMock()
        with patch("src.dynel.exception_handling.logger.debug", mock_logger_debug):
             module_exception_handler(config, dummy_module_with_classes) # re-run with debug on

        mock_logger_debug.assert_any_call("Wrapped function/staticmethod: %s in module %s", "module_level_func_good", "dummy_module_with_classes_for_dynel_test")
        mock_logger_debug.assert_any_call("Wrapped method: %s.%s in module %s", "MyTestClass", "instance_method_good", "dummy_module_with_classes_for_dynel_test")
        mock_logger_debug.assert_any_call("Wrapped method: %s.%s in module %s", "MyTestClass", "static_method_good", "dummy_module_with_classes_for_dynel_test")
        mock_logger_debug.assert_any_call("Wrapped method: %s.%s in module %s", "MyTestClass", "class_method_good", "dummy_module_with_classes_for_dynel_test")
        mock_logger_debug.assert_any_call("Wrapped method: %s.%s in module %s", "AnotherClass", "another_method_bad", "dummy_module_with_classes_for_dynel_test")
