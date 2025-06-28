import pytest
import json
from pathlib import Path
from unittest.mock import patch, Mock

# Importing from the new locations in src.dynel
from src.dynel.config import DynelConfig
from src.dynel.logging_utils import configure_logging
# For test_log_file_output_formats, we also need handle_exception
from src.dynel.exception_handling import handle_exception
# Import the actual logger instance for direct manipulation in tests if needed
from loguru import logger as dynel_logger_instance # Renamed to avoid clash
from typing import Optional # Added Optional


@pytest.fixture
def dynel_config_instance(): # Copied from test_config.py for standalone use here if needed
    """Returns a default DynelConfig instance."""
    return DynelConfig()

# --- Tests for configure_logging ---

@patch("src.dynel.logging_utils.logger") # Patch logger in logging_utils.py
def test_configure_logging_debug_mode(mock_loguru_logger, dynel_config_instance):
    dynel_config_instance.DEBUG_MODE = True
    configure_logging(dynel_config_instance)

    mock_loguru_logger.remove.assert_called_once()
    args_list = mock_loguru_logger.add.call_args_list
    assert any(
        call[1].get("sink") == "dynel.log" and call[1].get("level") == "DEBUG"
        for call in args_list
    )
    assert any(
        call[1].get("sink") == "dynel.json" and call[1].get("level") == "DEBUG" # also check level for json
        for call in args_list
    )


@patch("src.dynel.logging_utils.logger") # Patch logger in logging_utils.py
def test_configure_logging_production_mode(mock_loguru_logger, dynel_config_instance):
    dynel_config_instance.DEBUG_MODE = False
    configure_logging(dynel_config_instance)

    mock_loguru_logger.remove.assert_called_once()
    args_list = mock_loguru_logger.add.call_args_list
    assert any(
        call[1].get("sink") == "dynel.log" and call[1].get("level") == "INFO"
        for call in args_list
    )
    assert any(
        call[1].get("sink") == "dynel.json" and call[1].get("level") == "INFO" # also check level for json
        for call in args_list
    )

# --- Helper for log file tests ---
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
            # The structure might be {"record": ..., "text": ...} or just the record itself
            # based on how Loguru serializes. Assuming "record" key for now.
            # If direct serialization, then parsed_line is the record.
            record = parsed_line.get("record", parsed_line) # Adjust if structure differs
            if record.get("function") == function_name:
                return record
        except json.JSONDecodeError:
            continue
    return None


# --- Tests for Log File Output ---

def test_log_file_output_formats(tmp_path, monkeypatch):
    config = DynelConfig(context_level="med")

    log_file_txt = tmp_path / "output.log"
    log_file_json = tmp_path / "output.json"

    # Ensure the global logger instance (dynel_logger_instance) is clean and then configured
    dynel_logger_instance.remove()
    dynel_logger_instance.add(
        log_file_txt,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message} | {extra}",
        level="DEBUG",
    )
    dynel_logger_instance.add(log_file_json, serialize=True, level="DEBUG")


    error_to_raise = IndexError("Test index out of bounds")
    func_name = "function_writing_to_log_files"

    mock_caller_frame_obj_for_log_test = Mock()
    mock_caller_frame_obj_for_log_test.f_locals = {"alpha": 1, "beta": "two"}

    # Patch inspect within the exception_handling module
    with patch("src.dynel.exception_handling.inspect") as mock_dynel_inspect:
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

        try:
            raise error_to_raise
        except IndexError as e:
            handle_exception(config, e) # This uses the globally configured logger (dynel_logger_instance)

    # Verify text log content
    assert log_file_txt.exists()
    txt_content = log_file_txt.read_text()
    assert "ERROR" in txt_content
    assert f"{func_name}" in txt_content # func_name is from the perspective of handle_exception's caller
    assert "Exception caught in" in txt_content
    assert "IndexError: Test index out of bounds" in txt_content
    assert "'alpha': 1" in txt_content
    assert "'beta': 'two'" in txt_content
    assert "timestamp" in txt_content

    # Verify JSON log content
    assert log_file_json.exists()
    json_content = log_file_json.read_text()
    # The _find_log_record_by_function was designed for records nested under "record".
    # Loguru's direct JSON output might be different. Let's try parsing the first line.

    log_entry = None
    for line in json_content.strip().split("\n"):
        if line:
            parsed_line = json.loads(line)
            # Check if this is the record for handle_exception
            # The 'function' field in the record should be 'handle_exception'
            # The 'message' field will contain 'func_name'
            if parsed_line.get("record", {}).get("function") == "handle_exception" and \
               func_name in parsed_line.get("record", {}).get("message", ""):
                log_entry = parsed_line["record"]
                break
            # Fallback for simpler JSON structure (older Loguru or custom config)
            elif parsed_line.get("function") == "handle_exception" and \
                 func_name in parsed_line.get("message", ""):
                 log_entry = parsed_line
                 break

    assert log_entry is not None, f"Log entry from handle_exception (caller {func_name}) not found in JSON log"
    assert log_entry["level"]["name"] == "ERROR"
    assert f"Exception caught in {func_name}" in log_entry["message"]

    exception_details = log_entry["exception"]
    assert exception_details["type"] == "IndexError"
    assert "Test index out of bounds" in exception_details["value"]
    assert exception_details["traceback"]

    extra_details = log_entry["extra"]
    assert "timestamp" in extra_details
    assert "'alpha': 1" in extra_details["local_vars"]  # Stringified dict
    assert "'beta': 'two'" in extra_details["local_vars"]  # Stringified dict

    # Clean up global logger state
    dynel_logger_instance.remove()
