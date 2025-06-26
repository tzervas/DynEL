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
