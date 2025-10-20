"""
Comprehensive tests for the CLI functionality in app.py.
Tests user interaction flows, command handling, and navigation logic.
"""
import unittest
from unittest.mock import patch, mock_open
import sys
import os

# Add src directory to path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app import ArtifactMiner


class TestCLI(unittest.TestCase):
    """Comprehensive test cases for CLI functionality and user interactions."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        with patch('builtins.print'):  # Suppress initialization output
            self.cli = ArtifactMiner()

    # Initialization and Setup Tests
    def test_cli_initialization(self):
        """Test that CLI initializes with correct default values."""
        self.assertEqual(self.cli.project_filepath, '')
        self.assertFalse(self.cli.user_consent)
        self.assertEqual(self.cli.cmd_history, [])
        self.assertEqual(self.cli.prompt, '(PAF) ')
        self.assertEqual(self.cli.ruler, '-')
        self.assertIn("Choose one of the following options", self.cli.options)
        self.assertIn("Type 'back' or 'cancel'", self.cli.options)

    # Command History Management Tests
    def test_update_history_basic_functionality(self):
        """Test that command history is properly updated."""
        self.cli.update_history(self.cli.cmd_history, "perms")
        self.assertEqual(self.cli.cmd_history, ["perms"])

        self.cli.update_history(self.cli.cmd_history, "filepath")
        self.assertEqual(self.cli.cmd_history, ["filepath", "perms"])

    def test_update_history_maintains_max_three_commands(self):
        """Test that history only keeps the 3 most recent commands."""
        commands = ["first", "second", "third", "fourth"]
        for cmd in commands:
            self.cli.update_history(self.cli.cmd_history, cmd)

        self.assertEqual(len(self.cli.cmd_history), 3)
        self.assertEqual(self.cli.cmd_history, ["fourth", "third", "second"])

    # Cancel Input Handler Tests
    def test_handle_cancel_input_with_back(self):
        """Test cancel handler with 'back' command."""
        self.cli.cmd_history = ["perms"]

        with patch('builtins.print') as mock_print:
            result = self.cli._handle_cancel_input("back")
            self.assertTrue(result)
            mock_print.assert_called_with("\nCancelled 'perms' operation.")
            self.assertEqual(self.cli.cmd_history, [])

    def test_handle_cancel_input_with_cancel(self):
        """Test cancel handler with 'cancel' command."""
        self.cli.cmd_history = ["filepath"]

        with patch('builtins.print') as mock_print:
            result = self.cli._handle_cancel_input("CANCEL")  # Test case insensitive
            self.assertTrue(result)
            mock_print.assert_called_with("\nCancelled 'filepath' operation.")

    def test_handle_cancel_input_with_empty_history(self):
        """Test cancel handler with empty command history."""
        self.cli.cmd_history = []

        with patch('builtins.print') as mock_print:
            result = self.cli._handle_cancel_input("back")
            self.assertTrue(result)
            mock_print.assert_called_with("\nReturning to main menu.")

    def test_handle_cancel_input_with_non_cancel_commands(self):
        """Test that non-cancel inputs return False."""
        test_inputs = ["Y", "N", "1", "2", "3", "invalid", ""]
        for input_val in test_inputs:
            result = self.cli._handle_cancel_input(input_val)
            self.assertFalse(result)

    # Permissions Command Tests
    @patch('builtins.input', return_value='Y')
    @patch('builtins.print')
    def test_do_perms_user_consents(self, mock_print, mock_input):
        """Test permissions flow when user consents."""
        self.cli.do_perms("")

        self.assertTrue(self.cli.user_consent)
        self.assertEqual(self.cli.cmd_history[0], "perms")
        mock_print.assert_any_call("\nThank you for consenting. You may now continue.")

    @patch('builtins.input', return_value='N')
    @patch('builtins.print')
    def test_do_perms_user_declines(self, mock_print, mock_input):
        """Test permissions flow when user declines consent."""
        result = self.cli.do_perms("")

        self.assertFalse(self.cli.user_consent)
        self.assertTrue(result)  # Should return True to exit program
        mock_print.assert_any_call("Consent not given. Exiting application...")

    @patch('builtins.input', return_value='back')
    @patch('builtins.print')
    def test_do_perms_user_cancels(self, mock_print, mock_input):
        """Test permissions flow when user cancels with 'back'."""
        result = self.cli.do_perms("")

        self.assertFalse(self.cli.user_consent)
        self.assertIsNone(result)  # Should return None to go back to menu
        self.assertEqual(self.cli.cmd_history, [])  # History should be cleared

    @patch('builtins.input', side_effect=['invalid', 'another_invalid', 'Y'])
    @patch('builtins.print')
    def test_do_perms_handles_invalid_input(self, mock_print, mock_input):
        """Test that permissions handles invalid input correctly."""
        self.cli.do_perms("")

        # Should eventually succeed after invalid inputs
        self.assertTrue(self.cli.user_consent)

        # Check for the actual error message from your CLI code
        mock_print.assert_any_call("Invalid response. Please enter 'Y', 'N', 'back', or 'cancel'.")

    # Filepath Command Tests
    @patch('builtins.input', return_value='/path/to/project')
    @patch('builtins.print')
    def test_do_filepath_valid_path(self, mock_print, mock_input):
        """Test filepath command with valid input."""
        self.cli.do_filepath("")

        self.assertEqual(self.cli.project_filepath, '/path/to/project')
        self.assertEqual(self.cli.cmd_history[0], "filepath")
        mock_print.assert_any_call("\nFilepath successfully received")
        mock_print.assert_any_call('/path/to/project')

    @patch('builtins.input', return_value='cancel')
    @patch('builtins.print')
    def test_do_filepath_user_cancels(self, mock_print, mock_input):
        """Test filepath command when user cancels."""
        result = self.cli.do_filepath("")

        self.assertEqual(self.cli.project_filepath, '')  # Should remain empty
        self.assertIsNone(result)  # Should return None to go back to menu
        self.assertEqual(self.cli.cmd_history, [])  # History should be cleared

    # Begin Command Tests
    @patch('builtins.print')
    def test_do_begin_without_consent(self, mock_print):
        """Test begin command without user consent."""
        self.cli.do_begin("")

        mock_print.assert_any_call(
            "\nError: Missing consent. Type perms or 1 to read user permission agreement."
        )
        self.assertEqual(self.cli.cmd_history[0], "begin")

    @patch('builtins.open', side_effect=FileNotFoundError)
    @patch('builtins.print')
    def test_do_begin_with_invalid_filepath(self, mock_print, mock_open):
        """Test begin command with invalid file path."""
        self.cli.user_consent = True
        self.cli.project_filepath = '/invalid/path'

        with patch.object(self.cli, 'do_filepath') as mock_filepath:
            self.cli.do_begin("")

            mock_print.assert_any_call("Error: Invalid file. Please try again.")
            mock_filepath.assert_called_once_with("")

    # Command Routing Tests
    def test_default_command_routing_numeric(self):
        """Test that numeric commands route to correct functions."""
        test_cases = [
            ("1", "do_perms"),
            ("2", "do_filepath"),
            ("3", "do_begin")
        ]

        for command, expected_method in test_cases:
            with patch.object(self.cli, expected_method) as mock_method:
                self.cli.default(command)
                mock_method.assert_called_once_with("")

    def test_default_command_case_insensitive(self):
        """Test that commands work regardless of case."""
        with patch.object(self.cli, 'do_perms') as mock_perms:
            self.cli.default("1")
            self.cli.default("1".upper())
            self.assertEqual(mock_perms.call_count, 2)

    @patch('builtins.print')
    def test_default_handles_unknown_commands(self, mock_print):
        """Test handling of unknown commands."""
        unknown_commands = ["unknown", "4", "invalid", "help_me"]

        for command in unknown_commands:
            self.cli.default(command)
            mock_print.assert_any_call(f"Unknown command: {command}. Type 'help' or '?' for options.")

    # Exit Command Tests
    @patch('builtins.print')
    def test_do_exit_functionality(self, mock_print):
        """Test exit command."""
        result = self.cli.do_exit("")

        self.assertTrue(result)  # Should return True to exit cmdloop
        mock_print.assert_called_with('Exiting the program...')

    @patch('builtins.input', side_effect=['back', 'cancel'])
    @patch('builtins.print')
    def test_cancel_functionality_across_commands(self, mock_print, mock_input):
        """Test that cancel works consistently across all commands."""
        # Test cancel from permissions
        result1 = self.cli.do_perms("")
        self.assertIsNone(result1)
        self.assertEqual(self.cli.cmd_history, [])

        # Test cancel from filepath
        result2 = self.cli.do_filepath("")
        self.assertIsNone(result2)
        self.assertEqual(self.cli.cmd_history, [])

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


if __name__ == '__main__':
    # Run with verbose output to see individual test results
    unittest.main(verbosity=2)

