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
    # Original was: "not enough values to unpack (expected 2, got 1)"
    # This happens if 'DoesNotExist' is treated as a direct name and __builtins__.get fails, then rsplit fails.
    # If it's "NameError: name 'DoesNotExist' is not defined" if __builtins__.get raises NameError.
    # Let's make the check more robust by looking for key parts of the warning.
    found_warning_builtin = False
    for call_args in mock_logger_warning.call_args_list:
        if "DoesNotExist" in call_args[0][0] and "FuncWithBuiltin" in call_args[0][0]:
            found_warning_builtin = True
            break
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
