import pytest
import json
import yaml
import toml
from pathlib import Path
from unittest.mock import patch, MagicMock

# Importing from the new locations in src.dynel
from src.dynel.config import DynelConfig, ContextLevel # Corrected import path

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
def temp_config_file_generator():
    """
    Factory fixture to generate temporary config files (json, yaml, toml).
    The actual tmp_path should be passed by the test function.
    """
    def _create_temp_file(
        base_path: Path, filename_prefix: str, extension: str, data: dict
    ):
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
):
    config_data = VALID_CONFIG_DATA_DICT.copy()
    filename_prefix = "test_dynel_config"
    temp_config_file_generator(tmp_path, filename_prefix, ext, config_data)

    monkeypatch.chdir(tmp_path)
    # Assuming load_exception_config uses loguru.logger internally
    with patch('src.dynel.config.logger') as mock_logger: # Patch logger in src.dynel.config
        dynel_config_instance.load_exception_config(filename_prefix=filename_prefix)

    assert dynel_config_instance.DEBUG_MODE == config_data["debug_mode"]
    assert "MyFunction" in dynel_config_instance.EXCEPTION_CONFIG
    mf_config = dynel_config_instance.EXCEPTION_CONFIG["MyFunction"]
    assert mf_config["custom_message"] == config_data["MyFunction"]["custom_message"]
    assert set(mf_config["tags"]) == set(config_data["MyFunction"]["tags"])
    assert ValueError in mf_config["exceptions"]
    assert TypeError in mf_config["exceptions"]
    # Basic check behaviors are absent if not in config
    assert "behaviors" not in mf_config or not mf_config["behaviors"]


    assert "AnotherFunction" in dynel_config_instance.EXCEPTION_CONFIG
    af_config = dynel_config_instance.EXCEPTION_CONFIG["AnotherFunction"]
    assert KeyError in af_config["exceptions"]
    assert "behaviors" not in af_config or not af_config["behaviors"]


VALID_CONFIG_WITH_BEHAVIORS = {
    "debug_mode": False,
    "TestFuncWithBehaviors": {
        "exceptions": ["ValueError", "TypeError"],
        "custom_message": "Error with behaviors",
        "tags": ["behavior_test"],
        "behaviors": {
            "ValueError": {
                "add_metadata": {"code": "VE100", "severity": "High"},
                "log_to_specific_file": "value_errors.log"
            },
            "default": {
                "add_metadata": {"default_applied": True},
                "log_to_specific_file": "other_errors.log"
            }
        }
    },
    "TestFuncInvalidBehaviors": {
        "exceptions": ["AttributeError"],
        "behaviors": {
            "AttributeError": {
                "add_metadata": "not_a_dict", # Invalid
                "log_to_specific_file": 12345 # Invalid
            },
            "default": "not_a_dict_either" # Invalid behavior definition
        }
    }
}

@pytest.mark.parametrize("ext", ["json", "yaml", "toml"])
def test_load_exception_config_with_valid_behaviors(
    temp_config_file_generator, dynel_config_instance, ext, tmp_path, monkeypatch
):
    config_data = VALID_CONFIG_WITH_BEHAVIORS.copy()
    # Remove the invalid part for this valid test
    del config_data["TestFuncInvalidBehaviors"]
    filename_prefix = "test_config_valid_behaviors"
    temp_config_file_generator(tmp_path, filename_prefix, ext, config_data)

    monkeypatch.chdir(tmp_path)
    with patch('src.dynel.config.logger') as mock_logger:
        dynel_config_instance.load_exception_config(filename_prefix=filename_prefix)

    assert "TestFuncWithBehaviors" in dynel_config_instance.EXCEPTION_CONFIG
    func_config = dynel_config_instance.EXCEPTION_CONFIG["TestFuncWithBehaviors"]
    assert "behaviors" in func_config
    behaviors = func_config["behaviors"]

    assert "ValueError" in behaviors
    ve_behavior = behaviors["ValueError"]
    assert ve_behavior["add_metadata"] == {"code": "VE100", "severity": "High"}
    assert ve_behavior["log_to_specific_file"] == "value_errors.log"

    assert "default" in behaviors
    def_behavior = behaviors["default"]
    assert def_behavior["add_metadata"] == {"default_applied": True}
    assert def_behavior["log_to_specific_file"] == "other_errors.log"
    mock_logger.warning.assert_not_called() # No warnings for valid behaviors


@pytest.mark.parametrize("ext", ["json", "yaml", "toml"])
def test_load_exception_config_with_invalid_behaviors(
    temp_config_file_generator, dynel_config_instance, ext, tmp_path, monkeypatch
):
    config_data = VALID_CONFIG_WITH_BEHAVIORS.copy()
    # Keep only the invalid part for this test
    config_data = {"TestFuncInvalidBehaviors": config_data["TestFuncInvalidBehaviors"]}

    filename_prefix = "test_config_invalid_behaviors"
    temp_config_file_generator(tmp_path, filename_prefix, ext, config_data)

    monkeypatch.chdir(tmp_path)
    # We need to mock logger.warning as it's called by _parse_behaviors
    with patch('src.dynel.config.logger.warning') as mock_logger_warning:
        dynel_config_instance.load_exception_config(filename_prefix=filename_prefix)

    assert "TestFuncInvalidBehaviors" in dynel_config_instance.EXCEPTION_CONFIG
    func_config = dynel_config_instance.EXCEPTION_CONFIG["TestFuncInvalidBehaviors"]
    assert "behaviors" in func_config
    behaviors = func_config["behaviors"]

    # The "AttributeError" behavior key should exist, but its actions should be empty due to validation failures
    assert "AttributeError" in behaviors
    assert not behaviors["AttributeError"] # No valid actions parsed

    # The "default" behavior key itself was invalid (not a dict)
    assert "default" not in behaviors # Or it might be present but empty, depending on parsing logic for top-level behavior keys

    # Check that warnings were logged
    assert mock_logger_warning.call_count >= 3 # one for add_metadata, one for log_to_specific_file, one for default behavior_def

    # Example check for one of the expected warning messages
    mock_logger_warning.assert_any_call(
        "'add_metadata' for behavior 'AttributeError' under function 'TestFuncInvalidBehaviors' is not a dictionary. Skipping 'add_metadata'."
    )
    mock_logger_warning.assert_any_call(
        "'log_to_specific_file' for behavior 'AttributeError' under function 'TestFuncInvalidBehaviors' is not a valid string. Skipping 'log_to_specific_file'."
    )
    mock_logger_warning.assert_any_call(
        "Definition for behavior key 'default' under function 'TestFuncInvalidBehaviors' is not a dictionary. Skipping this behavior entry."
    )


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
        f.write("this is not valid {syntax,, for all formats")

    monkeypatch.chdir(tmp_path)
    with patch('src.dynel.config.logger') as mock_logger: # Patch logger in src.dynel.config
        with pytest.raises(expected_exception, match=expected_match):
            dynel_config_instance.load_exception_config(filename_prefix)


@pytest.mark.parametrize("ext", ["json", "yaml", "toml"])
def test_load_exception_config_safer_exception_loading(
    temp_config_file_generator, dynel_config_instance, ext, tmp_path, monkeypatch
):
    config_data = {
        "debug_mode": False,
        "FuncWithBuiltin": {"exceptions": ["ValueError", "DoesNotExist"]},
        "FuncWithImportable": {"exceptions": ["os.PathLike"]},
        "FuncWithNonException": {"exceptions": ["src.dynel.config.ContextLevel"]}, # Adjusted path
        "FuncWithUnresolvable": {"exceptions": ["nonexistent_module.NonExistentError"]},
    }
    filename_prefix = "test_exc_loading"
    temp_config_file_generator(tmp_path, filename_prefix, ext, config_data)

    mock_logger_warning = MagicMock()
    mock_logger_error = MagicMock() # For unexpected errors during loading

    monkeypatch.chdir(tmp_path)
    # Patching logger directly in the 'config' module where load_exception_config is defined
    with patch("src.dynel.config.logger.warning", mock_logger_warning), \
         patch("src.dynel.config.logger.error", mock_logger_error):
        dynel_config_instance.load_exception_config(filename_prefix)

    assert ValueError in dynel_config_instance.EXCEPTION_CONFIG["FuncWithBuiltin"]["exceptions"]
    assert not any(
        exc_type.__name__ == "DoesNotExist"
        for exc_type in dynel_config_instance.EXCEPTION_CONFIG["FuncWithBuiltin"]["exceptions"]
    )
    # Check that 'DoesNotExist' was warned about. The exact error message might vary slightly.
    found_warning_builtin = any(
        call_args and call_args[0] and "DoesNotExist" in call_args[0][0] and "FuncWithBuiltin" in call_args[0][0]
        for call_args in mock_logger_warning.call_args_list
    )
    assert found_warning_builtin, "Warning for 'DoesNotExist' not found or not as expected."


    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithImportable"]["exceptions"]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'os.PathLike' for 'FuncWithImportable': 'os.PathLike' is not an Exception subclass.. Skipping."
    )

    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithNonException"]["exceptions"]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'src.dynel.config.ContextLevel' for 'FuncWithNonException': 'src.dynel.config.ContextLevel' is not an Exception subclass.. Skipping."
    )

    assert not dynel_config_instance.EXCEPTION_CONFIG["FuncWithUnresolvable"]["exceptions"]
    mock_logger_warning.assert_any_call(
        "Could not load or validate exception 'nonexistent_module.NonExistentError' for 'FuncWithUnresolvable': No module named 'nonexistent_module'. Skipping."
    )
