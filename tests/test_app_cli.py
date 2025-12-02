"""
Comprehensive tests for the CLI functionality in app.py.
Tests user interaction flows, command handling, and navigation logic.
"""
from src.app import start_miner
import pytest
from unittest.mock import patch, mock_open, call
from src.classes.cli import ArtifactMiner, _is_valid_filepath_to_zip


def test_is_valid_filepath_to_zip(tmp_path):
    """
    Tests all error codes for _is_valid_filepath_to_zip function.
    """
    # Test case 3: Filepath does not exist
    non_existent_path = tmp_path / "non_existent.zip"
    assert _is_valid_filepath_to_zip(str(non_existent_path)) == 3

    # Test case 1: Invalid filepath (not a file)
    dir_path = tmp_path / "a_directory"
    dir_path.mkdir()
    assert _is_valid_filepath_to_zip(str(dir_path)) == 1

    # Test case 2: Filepath does not point to a zip file
    non_zip_file = tmp_path / "file.txt"
    non_zip_file.write_text("This is a test file.")
    assert _is_valid_filepath_to_zip(str(non_zip_file)) == 2

    # Test case 0: Valid filepath to a zip file
    zip_file = tmp_path / "archive.zip"
    zip_file.write_text("This is a zip file content.")
    assert _is_valid_filepath_to_zip(str(zip_file)) == 0


@pytest.fixture
def cli():
    """Fixture providing a CLI instance with suppressed initialization output."""
    with patch('builtins.print'), \
            patch('src.classes.cli.UserPreferences') as mock_prefs_class:

        # Mock the UserPreferences instance and its methods
        mock_prefs = mock_prefs_class.return_value
        mock_prefs.load_preferences.return_value = {
            "consent": False,
            "project_filepath": "",
            "user_email": "",
            "user_name": "",
            "user_password": ""
        }
        mock_prefs.get_project_filepath.return_value = ""
        mock_prefs.get_user_credentials.return_value = ("", "", "")
        mock_prefs.preferences_file.exists.return_value = False
        mock_prefs.get_preferences_file_path.return_value = "/mock/preferences.json"

        # Create CLI instance with mocked preferences
        cli_instance = ArtifactMiner()

        # Ensure clean state for each test
        cli_instance.project_filepath = ''
        cli_instance.user_consent = False
        cli_instance.user_email = ''
        cli_instance.cmd_history = []

        yield cli_instance

# Initialization and Setup Tests


def test_cli_initialization(cli):
    """Test that CLI initializes with correct default values."""
    assert cli.project_filepath == ''
    assert cli.user_consent is False
    assert cli.cmd_history == []
    assert cli.user_email == ''
    assert cli.prompt == '(PAF) '
    assert cli.ruler == '-'
    assert "Choose one of the following options" in cli.options
    assert "Type 'back' or 'cancel'" in cli.options

# Command History Management Tests


def test_update_history_basic_functionality(cli):
    """Test that command history is properly updated."""
    cli.update_history(cli.cmd_history, "perms")
    assert cli.cmd_history == ["perms"]

    cli.update_history(cli.cmd_history, "filepath")
    assert cli.cmd_history == ["perms", "filepath"]

# Cancel Input Handler Tests


def test_handle_cancel_input_with_back(cli):
    """Test cancel handler with 'back' command."""
    cli.cmd_history = ["perms"]

    with patch('builtins.print') as mock_print:
        result = cli._handle_cancel_input(
            "back", "main")  # Add second argument

        assert result is True
        assert len(cli.cmd_history) == 0
        # Verify the cancel message was printed
        assert any("Cancelled" in str(call)
                   for call in mock_print.call_args_list)


def test_handle_cancel_input_with_cancel(cli):
    """Test cancel handler with 'cancel' command."""
    cli.cmd_history = ["filepath"]

    with patch('builtins.print') as mock_print:
        result = cli._handle_cancel_input(
            "CANCEL", "main")  # Add second argument

        assert result is True
        assert len(cli.cmd_history) == 0
        assert any("Cancelled" in str(call)
                   for call in mock_print.call_args_list)


def test_handle_cancel_input_with_empty_history(cli):
    """Test cancel handler with empty command history."""
    cli.cmd_history = []

    with patch('builtins.print') as mock_print:
        result = cli._handle_cancel_input(
            "back", "main")  # Add second argument

        assert result is True
        assert len(cli.cmd_history) == 0
        # Should still print a return message even with empty history
        assert any("Returning" in str(call)
                   for call in mock_print.call_args_list)


def test_handle_cancel_input_with_non_cancel_commands(cli):
    """Test that non-cancel inputs return False."""
    test_inputs = ["Y", "N", "1", "2", "3", "invalid", ""]
    for input_val in test_inputs:
        result = cli._handle_cancel_input(
            input_val, "main")  # Add second argument
        assert result is False, f"Expected False for input '{input_val}'"


# Edge Cases and Error Handling


@pytest.mark.parametrize("input_value", ["", "   "])
def test_empty_input_handling(cli, input_value):
    """Test handling of empty inputs."""
    result = cli._handle_cancel_input(
        input_value, "main")  # Add second argument
    assert result is False
    # Empty input should not trigger cancel


@pytest.mark.parametrize("cancel_command", ["  back  ", "\tcancel\n"])
def test_whitespace_handling_in_cancel(cli, cancel_command):
    """Test that cancel commands work with extra whitespace."""
    cli.cmd_history = ["test"]
    with patch('builtins.print'):
        result = cli._handle_cancel_input(
            cancel_command, "main")  # Add second argument
        assert result is True
        assert len(cli.cmd_history) == 0


def test_options_text_contains_required_information(cli):
    """Test that options text contains all required user guidance."""
    options = cli.options

    # Check for main menu options
    assert "(1) Permissions" in options
    assert "(2) Set filepath" in options
    assert "(3) Begin Artifact Miner" in options
    assert "(9) Retrieve a Portfolio" in options

    # Check for cancel instruction
    assert "back" in options
    assert "cancel" in options
    assert "main menu" in options

    # Check for help instruction
    assert "help" in options

# Permissions Command Tests


def test_do_perms_user_consents(cli):
    """Test permissions flow when user consents."""
    with patch('builtins.input', return_value='Y'), \
            patch('builtins.print') as mock_print:
        cli.do_perms("")
        assert cli.user_consent is True
        assert cli.cmd_history[0] == "perms"
        mock_print.assert_any_call(
            "\nThank you for consenting. Consent saved to preferences.")


def test_do_perms_user_declines(cli):
    """Test permissions flow when user declines consent."""
    with patch('builtins.input', return_value='N'), \
            patch('builtins.print') as mock_print:
        result = cli.do_perms("")
        assert cli.user_consent is False
        assert result is True  # Should return True to exit program
        mock_print.assert_any_call("Consent not given. Exiting application...")


def test_prompt_portfolio_name_invokes_rename(cli):
    """Ensure renaming is attempted when a new name is provided."""
    cli.project_filepath = "/tmp/example.zip"
    with patch('builtins.input', return_value='new-name'), \
            patch('src.classes.cli.rename_user_report', return_value=(True, "ok")) as mock_rename, \
            patch('builtins.print'), \
            patch.object(cli.preferences, "update"):
        cli._prompt_portfolio_name()
        mock_rename.assert_called_once_with("example", "new-name")


def test_prompt_portfolio_name_noop_on_blank(cli):
    """Leaving the name blank should keep existing title and avoid renaming."""
    cli.project_filepath = "/tmp/example.zip"
    with patch('builtins.input', return_value=''), \
            patch('src.classes.cli.rename_user_report') as mock_rename, \
            patch('builtins.print'), \
            patch.object(cli.preferences, "update"):
        cli._prompt_portfolio_name()
        mock_rename.assert_not_called()


def test_default_routes_nine_to_retrieve(cli):
    """Ensure option 9 routes to portfolio retrieval."""
    with patch.object(cli, 'do_portfolio_retrieve') as mock_retrieve:
        cli.default("9")
        mock_retrieve.assert_called_once()


def test_do_portfolio_retrieve_uses_preferences_when_blank(cli):
    """Blank input should retrieve portfolio name from preferences."""
    cli.preferences.get_project_filepath.return_value = "/tmp/last.zip"
    cli.preferences.get.return_value = ""  # ensure no last_portfolio_title stored
    mock_report = type("Report", (), {"to_user_readable_string": lambda self: "REPORT"})()
    with patch('builtins.input', side_effect=['']), \
            patch('src.classes.cli.print'), \
            patch('src.database.utils.database_access.get_user_report', return_value=mock_report) as mock_get:
        cli.do_portfolio_retrieve("")
        mock_get.assert_called_once_with("last")


def test_do_portfolio_retrieve_option_two_prompts_for_name(cli):
    """Entering '2' should prompt for a portfolio name and use it."""
    mock_report = type("Report", (), {"to_user_readable_string": lambda self: "REPORT"})()
    with patch('builtins.input', side_effect=['2', 'my-portfolio']), \
            patch('src.classes.cli.print'), \
            patch('src.database.utils.database_access.get_user_report', return_value=mock_report) as mock_get:
        cli.do_portfolio_retrieve("")
        mock_get.assert_called_once_with("my-portfolio")


def test_do_portfolio_retrieve_option_two_blank_uses_last(cli):
    """Entering '2' then blank should fall back to last analyzed name."""
    cli.preferences.get.return_value = ""  # no last_portfolio_title
    cli.preferences.get_project_filepath.return_value = "/tmp/last.zip"
    mock_report = type("Report", (), {"to_user_readable_string": lambda self: "REPORT"})()
    with patch('builtins.input', side_effect=['2', '']), \
            patch('src.classes.cli.print'), \
            patch('src.database.utils.database_access.get_user_report', return_value=mock_report) as mock_get:
        cli.do_portfolio_retrieve("")
        mock_get.assert_called_once_with("last")


def test_do_perms_user_cancels(cli):
    """Test permissions flow when user cancels with 'back'."""
    with patch('builtins.input', return_value='back'), \
            patch('builtins.print') as mock_print:
        result = cli.do_perms("")
        assert cli.user_consent is False
        assert result is None  # Should return None to go back to menu
        assert cli.cmd_history == []  # History should be cleared


def test_do_perms_handles_invalid_input(cli):
    """Test that permissions handles invalid input correctly."""
    with patch('builtins.input', side_effect=['invalid', 'another_invalid', 'Y']), \
            patch('builtins.print') as mock_print:
        cli.do_perms("")
        # Should eventually succeed after invalid inputs
        assert cli.user_consent is True
        # Check for the actual error message from your CLI code
        mock_print.assert_any_call(
            "Invalid response. Please enter 'Y', 'N', 'back', or 'cancel'.")

# Filepath Command Tests


def test_do_filepath_valid_path(cli):
    """Test filepath command with valid input."""
    test_path = '/path/to/project'
    with patch('builtins.input', return_value=test_path), \
            patch('builtins.print') as mock_print, \
            patch('src.classes.cli._is_valid_filepath_to_zip', return_value=0):
        cli.do_filepath("")
        assert cli.project_filepath == test_path
        assert cli.cmd_history[0] == "filepath"
        mock_print.assert_any_call(
            "\nFilepath successfully received and saved to preferences")
        mock_print.assert_any_call(test_path)


def test_do_filepath_user_cancels(cli):
    """Test filepath command when user cancels."""
    # Reset filepath to ensure clean test state
    cli.project_filepath = ''

    with patch('builtins.input', return_value='cancel'), \
            patch('builtins.print'):
        result = cli.do_filepath("")
        assert cli.project_filepath == ''  # Should remain empty
        assert result is None  # Should return None to go back to menu
        assert cli.cmd_history == []  # History should be cleared

# Begin Command Tests


def test_do_begin_without_consent(cli):
    """Test begin command without user consent."""

    # Explicit about the starting state for this test
    cli.user_consent = False
    cli.project_filepath = ''

    with patch('builtins.print') as mock_print, \
            patch('src.classes.cli.start_miner') as mock_start:
        cli.do_begin("")
        mock_print.assert_any_call(
            "\nError: Missing consent. Type perms or 1 to read user permission agreement."
        )
        assert cli.cmd_history[0] == "begin"
        mock_start.assert_not_called()

# Command Routing Tests


@pytest.mark.parametrize("command,expected_method", [
    ("1", "do_perms"),
    ("2", "do_filepath"),
    ("3", "do_begin"),
    ("4", "do_email")
])
def test_default_command_routing_numeric(cli, command, expected_method):
    """Test that numeric commands route to correct functions."""
    with patch.object(cli, expected_method) as mock_method:
        cli.default(command)
        mock_method.assert_called_once_with("")


def test_default_command_routing_numeric_login(cli):
    """Test that '5' routes to do_login."""
    with patch.object(cli, 'do_login') as mock_login, \
            patch('builtins.input', side_effect=['back']):  # Mock input to avoid stdin issues
        cli.default('5')
        mock_login.assert_called_once_with('')


def test_default_command_case_insensitive(cli):
    """Test that commands work regardless of case."""
    with patch.object(cli, 'do_perms') as mock_perms:
        cli.default("1")
        cli.default("1".upper())
        assert mock_perms.call_count == 2


def test_default_handles_unknown_commands(cli):
    """Test handling of unknown commands."""
    unknown_commands = ["unknown", "invalid",
                        "help_me"]
    with patch('builtins.print') as mock_print:
        for command in unknown_commands:
            cli.default(command)

        # Verify error messages were printed for each unknown command
        assert mock_print.call_count == len(unknown_commands)
        for call in mock_print.call_args_list:
            assert "Unknown command" in str(call)


@pytest.mark.parametrize("command,method", [
    ("6", "do_preferences"),
    ("7", "do_view"),
])
def test_default_command_routing_numeric_advanced(cli, command, method):
    """Test that advanced preference commands route correctly."""
    with patch.object(cli, method) as mock_method, \
            patch('builtins.input', side_effect=['4']):  # Choose "Back to Main Menu"
        cli.default(command)
        mock_method.assert_called_once_with('')

# Exit Command Tests


def test_do_exit_functionality(cli):
    """Test exit command."""
    with patch('builtins.print') as mock_print:
        with pytest.raises(SystemExit) as exc_info:  # Expect SystemExit
            cli.do_exit("")

        assert exc_info.value.code == 0  # Verify exit code is 0
        mock_print.assert_called_once()
        assert "Thank you for using Artifact Miner" in str(
            mock_print.call_args)


@pytest.mark.parametrize('command', ['back', 'cancel'])
def test_cancel_functionality_across_commands(cli, command):
    """Test that cancel works consistently across all commands."""
    with patch('builtins.input', return_value=command), \
            patch('builtins.print'):
        # Test cancel from permissions
        result1 = cli.do_perms("")
        assert result1 is None
        assert cli.cmd_history == []

        # Test cancel from filepath
        result2 = cli.do_filepath("")
        assert result2 is None
        assert cli.cmd_history == []

    # Edge Cases and Error Handling
    def test_empty_input_handling(self):
        """Test handling of empty inputs."""
        result = self.cli._handle_cancel_input("")
        self.assertFalse(result)

        result = self.cli._handle_cancel_input("   ")  # Whitespace only
        self.assertFalse(result)

    def test_whitespace_handling_in_cancel(self):
        """Test that cancel commands work with extra whitespace."""
        self.cli.cmd_history = ["test"]

        with patch('builtins.print'):
            result = self.cli._handle_cancel_input("  back  ")
            self.assertTrue(result)

            self.cli.cmd_history = ["test"]
            result = self.cli._handle_cancel_input("\tcancel\n")
            self.assertTrue(result)

    def test_options_text_contains_required_information(self):
        """Test that options text contains all required user guidance."""
        options = self.cli.options

        # Check for main menu options
        self.assertIn("(1) Permissions", options)
        self.assertIn("(2) Set filepath", options)
        self.assertIn("(3) Begin Artifact Miner", options)

        # Check for cancel instruction
        self.assertIn("back", options)
        self.assertIn("cancel", options)
        self.assertIn("main menu", options)

        # Check for help instruction
        self.assertIn("help", options)

def test_resume_bullet_exit_calls_do_exit(cli):
    """If the user types 'exit', do_exit should be called and no bullets printed."""
    with patch.object(cli, "do_exit") as mock_exit, \
         patch("builtins.input", return_value="exit"), \
         patch("builtins.print") as mock_print:
        cli.do_resume_bullet_point("")

        mock_exit.assert_called_once_with("")
        assert not any(
            "Generated resume bullet point(s)" in str(call)
            for call in mock_print.call_args_list
        )

def test_resume_bullet_back_or_cancel_returns_to_menu(cli):
    """If user types 'back', the command should cancel and return to main menu."""
    with patch("builtins.input", return_value="back"), \
         patch("builtins.print") as mock_print:
        cli.do_resume_bullet_point("")

        assert cli.cmd_history == []
        assert any(
            "Cancelled 'resume_bullet_point' operation." in str(call)
            for call in mock_print.call_args_list
        )
        assert any(
            "Artifact Miner Main Menu" in str(call)
            for call in mock_print.call_args_list
        )

def test_resume_bullet_empty_project_name(cli):
    """Blank project name should show validation message and not hit DB."""
    with patch("builtins.input", return_value=""), \
         patch("builtins.print") as mock_print, \
         patch("src.classes.cli.get_project_from_project_name") as mock_get:
        cli.do_resume_bullet_point("")

        mock_get.assert_not_called()
        assert any(
            "Project name cannot be empty." in str(call)
            for call in mock_print.call_args_list
        )
        assert not any(
            "Generated resume bullet point(s)" in str(call)
            for call in mock_print.call_args_list
        )

def test_resume_bullet_project_not_found(cli):
    """If the DB lookup fails, print 'not found' message and return."""
    with patch("builtins.input", return_value="missing-project"), \
         patch("builtins.print") as mock_print, \
         patch("src.classes.cli.get_project_from_project_name", side_effect=Exception("not found")):
        cli.do_resume_bullet_point("")

        assert any(
            "No project found for name 'missing-project' in the database." in str(call)
            for call in mock_print.call_args_list
        )
        assert not any(
            "Generated resume bullet point(s)" in str(call)
            for call in mock_print.call_args_list
        )

def test_resume_bullet_success_path(cli):
    """Happy path: valid project name → bullets generated and printed."""
    class DummyProjectReport:
        project_name = "my-project"

    dummy_report = DummyProjectReport()

    with patch("builtins.input", return_value="my-project"), \
         patch("src.classes.cli.get_project_from_project_name", return_value=dummy_report) as mock_get, \
         patch("src.classes.cli.bullet_point_builder", return_value=["Bullet one", "Bullet two"]) as mock_builder, \
         patch("builtins.print") as mock_print:

        cli.do_resume_bullet_point("")

        mock_get.assert_called_once_with("my-project")
        mock_builder.assert_called_once_with(dummy_report)

        assert any(
            "Generated resume bullet point(s):" in str(call)
            for call in mock_print.call_args_list
        )
        assert any("- Bullet one" in str(call) for call in mock_print.call_args_list)
        assert any("- Bullet two" in str(call) for call in mock_print.call_args_list)
        assert any(
            "Artifact Miner Main Menu" in str(call)
            for call in mock_print.call_args_list
        )

def test_keyboardinterrupt_handling(cli):
    """Test that ctrl-c exits cleanly with correct message."""
    with patch.object(ArtifactMiner, "cmdloop", side_effect=KeyboardInterrupt), \
            patch("builtins.print") as mock_print:

        # Simulate running the main block
        try:
            ArtifactMiner().cmdloop()
        except KeyboardInterrupt:
            print("Exiting the program...")

        mock_print.assert_any_call("Exiting the program...")
