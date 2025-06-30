import pytest
from unittest.mock import patch, Mock

# Importing from the new locations in src.dynel
from src.dynel.cli import parse_command_line_args

# --- Tests for parse_command_line_args ---

def test_parse_command_line_args_defaults():
    with patch("argparse.ArgumentParser.parse_args", return_value=Mock(context_level="min", debug=False, formatting=True)) as mock_parse_args:
        args = parse_command_line_args()
    mock_parse_args.assert_called_once()
    assert args["context_level"] == "min"
    assert args["debug"] is False
    assert args["formatting"] is True


@pytest.mark.parametrize(
    "cli_input_args, expected_key, expected_value",
    [
        (["--context-level", "med"], "context_level", "med"),
        (["--debug"], "debug", True),
        (["--no-formatting"], "formatting", False),
        (["--context-level", "detailed", "--debug"], "context_level", "detailed"),
        (["--context-level", "det", "--debug", "--no-formatting"], "formatting", False),
    ],
)
def test_parse_command_line_args_custom(cli_input_args, expected_key, expected_value):
    # Patch sys.argv for the duration of this test case
    with patch("sys.argv", ["script_name.py"] + cli_input_args):
        parsed_args = parse_command_line_args()
    assert parsed_args[expected_key] == expected_value

    # Also test other args if they are part of a combined test case
    if "--debug" in cli_input_args:
        assert parsed_args["debug"] is True
    elif expected_key != "debug": # if debug is not the primary key and not in args, it should be False
        assert parsed_args.get("debug", False) is False # Default for debug is False

    if "--no-formatting" in cli_input_args:
        assert parsed_args["formatting"] is False
    elif expected_key != "formatting": # if formatting is not primary and not in args, it should be True
        assert parsed_args.get("formatting", True) is True # Default for formatting is True

    if "--context-level" in cli_input_args:
        # Find the value after --context-level in cli_input_args
        try:
            idx = cli_input_args.index("--context-level")
            val = cli_input_args[idx+1]
            assert parsed_args["context_level"] == val
        except (ValueError, IndexError):
            pytest.fail("--context-level argument provided but value missing or index error.")
    elif expected_key != "context_level":
        assert parsed_args.get("context_level", "min") == "min" # Default is 'min'
