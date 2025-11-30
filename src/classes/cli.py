"""
This file contains the command line interface (CLI) for the Artifact Miner application.
"""

import cmd
import re
import os
from src.app import start_miner
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.app import start_miner
from sqlalchemy import select, delete
from src.database.utils.database_modify import rename_user_report


def normalize_path(user_path: str) -> str:
    r"""
    Normalize a user-provided file path so it works cross-platform.
    - Expands ~ to home directory
    - Converts backslashes and slashes for consistency
    - Normalizes redundant separators and up-level references
    - On Windows, maps Mac-style /Users/<username>/ paths to C:\\Users\\<username>\\
    - On Mac, maps Windows-style C:\\Users\\<username>\\ paths to /Users/<username>/
    """
    if not user_path:
        return user_path
    # On Mac, map C:\Users\<username>\... or C:/Users/<username>/... to /Users/<username>/...
    if sys.platform == 'darwin':
        match = re.match(r'^[cC]:[\\/]+Users[\\/]+([^\\/]+)[\\/]+(.+)', user_path)
        if match:
            username, rest = match.groups()
            user_path = f"/Users/{username}/{rest}"
    # Expand ~ to home directory
    user_path = os.path.expanduser(user_path)
    # On Windows, map /Users/<username>/... to C:\Users\<username>\...
    if os.name == 'nt':
        match = re.match(r'^/Users/([^/\\]+)/(.+)', user_path)
        if match:
            username, rest = match.groups()
            user_path = f"C:\\Users\\{username}\\{rest}"
    # Convert all slashes to OS separator
    user_path = user_path.replace('\\', os.sep).replace('/', os.sep)
    # Normalize path (removes redundant .., . etc.)
    user_path = os.path.normpath(user_path)
    return user_path


class UserPreferences:
    """Manages User Preferences with JSON storage in database folder"""

    def __init__(self, preferences_file: str = None):
        src_folder_path = Path(__file__).parent.parent
        database_folder_path = src_folder_path / "database"
        filename = preferences_file or "preferences.json"
        self.preferences_file = database_folder_path / filename

        self.default_preferences = {
            "consent": False,
            "files_to_ignore": [],
            "file_start_time": None,
            "file_end_time": None,
            "last_updated": None,
            "project_filepath": "",
            "user_name": "",
            "user_password": "",
            "user_email": ""
        }

    def load_preferences(self) -> dict[str, Any]:
        """Load preferences from JSON file or create with defaults."""
        if not self.preferences_file.exists():
            self.save_preferences(self.default_preferences)
            return self.default_preferences.copy()

        try:
            with open(self.preferences_file, 'r') as f:
                preferences = json.load(f)
            # Ensure backwards compatibility
            for key, default_value in self.default_preferences.items():
                if key not in preferences:
                    preferences[key] = default_value
            return preferences
        except (json.JSONDecodeError, FileNotFoundError):
            return self.default_preferences.copy()

    def save_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Save preferences to JSON file."""
        try:
            self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
            preferences["last_updated"] = datetime.now().isoformat()
            with open(self.preferences_file, 'w') as f:
                json.dump(preferences, f, indent=4, default=str)
            return True
        except Exception:
            return False

    def update(self, key: str, value: Any) -> bool:
        """Update single preference."""
        preferences = self.load_preferences()
        preferences[key] = value
        return self.save_preferences(preferences)

    def get(self, key: str, default: Any = None) -> Any:
        """Get preference value."""
        return self.load_preferences().get(key, default)

    def update_credentials(self, name: str, password: str, email: str = None) -> bool:
        """Update user credentials."""
        preferences = self.load_preferences()
        preferences.update({
            "user_name": name,
            "user_password": password,
            "user_email": email if email is not None else preferences.get("user_email", "")
        })
        return self.save_preferences(preferences)

    def get_credentials(self) -> tuple[str, str, str]:
        """Get user credentials (name, password, email)."""
        prefs = self.load_preferences()
        return (prefs.get("user_name", ""), prefs.get("user_password", ""), prefs.get("user_email", ""))

    def reset(self) -> bool:
        """Reset to defaults."""
        return self.save_preferences(self.default_preferences.copy())

    def update_consent(self, consent: bool) -> bool:
        """ Update user consent preference. """
        return self.update("consent", consent)

    def get_project_filepath(self) -> str:
        """Get the stored project filepath."""
        return self.get("project_filepath", "")

    def update_project_filepath(self, filepath: str) -> bool:
        """Update the project filepath preference."""
        return self.update("project_filepath", filepath)

    def get_preferences_file_path(self) -> str:
        """Get the full path to the preferences file."""
        return str(self.preferences_file.absolute())

    def update_user_email(self, email: str) -> bool:
        """Update user email preference."""
        return self.update("user_email", email)

    def get_date_range(self) -> tuple[str, str]:
        """Get file date range (start_time, end_time)."""
        prefs = self.load_preferences()
        return (prefs.get("file_start_time", ""), prefs.get("file_end_time", ""))

    def update_date_range(self, start_time: str, end_time: str) -> bool:
        """Update file date range filtering."""
        preferences = self.load_preferences()
        preferences.update({
            "file_start_time": start_time if start_time else None,
            "file_end_time": end_time if end_time else None
        })
        return self.save_preferences(preferences)

    def get_date_range_display(self) -> str:
        """Get formatted date range string for display."""
        start_time, end_time = self.get_date_range()

        if start_time and end_time:
            return f"{start_time} to {end_time}"
        elif start_time and (end_time is None or end_time == 'null' or end_time == 'Null'):
            return f"All files after {start_time}"
        elif (start_time is None or start_time == 'null' or start_time == 'Null') and end_time:
            return f"All files before {end_time}"
        else:
            return "All dates"

    def get_files_to_ignore(self) -> List[str]:
        """Get list of file extensions to ignore."""
        return self.get("files_to_ignore", [])

    def update_files_to_ignore(self, extensions: List[str]) -> bool:
        """Update file extensions to ignore."""
        return self.update("files_to_ignore", extensions)

    def reset_to_defaults(self) -> bool:
        """Reset to defaults - alias for reset."""
        return self.reset()

def _is_valid_filepath_to_zip(filepath: str) -> int:
    """
    Helper function to validate the provided filepath.
    A valid filepath must exist and be a zipped file.

    Int code returns:
    0 - valid filepath to a zip file
    1 - invalid filepath
    2 - filepath does not point to a zip file
    3 - filepath does not exist
    """

    if not os.path.exists(filepath):
        return 3
    if not os.path.isfile(filepath):
        return 1
    valid_exts = ('.zip', '.tar.gz', '.gz', '.7z')
    if not any(filepath.endswith(ext) for ext in valid_exts):
        return 2
    return 0


class ArtifactMiner(cmd.Cmd):
    def __init__(self):
        super().__init__()

        # Default user consent to false, and empty pathfile
        self.user_consent = False
        self.project_filepath = ''

        # Initialize preferences system FIRST
        self.preferences = UserPreferences()

        # Config for CLI
        self.options = (
            "=== Artifact Miner Main Menu ===\n"
            "Choose one of the following options:\n"
            "(1) Permissions\n"
            "(2) Set filepath\n"
            "(3) Begin Artifact Miner\n"
            "(4) Configure Email for Git Stats\n"
            "(5) User Login (Name & Password)\n"
            "(6) Configure preferences\n"
            "(7) View current preferences\n"
            "(8) Delete a Portfolio\n"
            "(9) Retrieve a Portfolio\n"
            "Type 'back' or 'cancel' to return to this main menu\n"
            "Type help or ? to list commands\n"
        )
        self.prompt = '(PAF) '
        self.ruler = '-'  # overwrite default separator line ('=')
        self.cmd_history = []  # will store the user's previous 3 commands

        # Update user login
        self.user_name = ''
        self.user_password = ''

        # Update with user input
        self.project_filepath = ''  # Will be overwritten with user input
        self.user_consent = False  # Milestone #1- Requirement #1, #4
        self.user_email = ''  # will be user's Git-associated email

        # Load existing preferences after initializing preferences system
        self._load_existing_preferences()

        title = 'Project Artifact Miner'
        print(f'\n{title}')
        print(self.ruler * len(self.options.splitlines()[0]), "\n")
        print(self.options)

        # Show preferences file location
        print(
            f"Preferences stored in: {self.preferences.get_preferences_file_path()}")

    def _load_existing_preferences(self):
        """Load existing preferences and set instance variables."""
        prefs = self.preferences.load_preferences()

        # Set instance variables from preferences
        self.user_consent = prefs.get('consent', False)
        self.project_filepath = prefs.get('project_filepath', '')
        self.user_email = prefs.get('user_email', '')
        self.user_name = prefs.get('user_name', '')
        self.user_password = prefs.get('user_password', '')

        if self.preferences.preferences_file.exists():
            print(
                f"Loaded preferences from: {self.preferences.get_preferences_file_path()}")
        else:
            print(
                f"Created new preferences file at: {self.preferences.get_preferences_file_path()}")

    def do_perms(self, arg):
        '''
        Provides consent statement. User may enter Y/N to agree or disagree.
        '''
        self.update_history(self.cmd_history, "perms")
        # TODO: agreement doesn't print properly if the terminal isn't wide enough
        agreement = (
            "Do you consent to this program accessing all files and/or folders"
            "\nin the filepath you provide and (if applicable) permission to use"
            "\nthe files and/or folders in 3rd party software?\n"
            "(Y/N) or type 'back'/'cancel' to return to main menu: "
        )
        while True:
            answer = input(agreement).strip()

            # Check for cancel first
            # user entered 'back'/'cancel'
            if self._handle_cancel_input(answer, "main"):
                print("\n" + self.options)
                break

            # Handle exit/quit first
            if answer.lower() in ['exit', 'quit']:
                return self.do_exit(arg)

            answer = answer.upper()
            if answer == 'Y':  # user consents
                self.user_consent = True
                # Save consent to preferences
                success = self.preferences.update_consent(True)
                if success:
                    print("\nThank you for consenting. Consent saved to preferences.")
                else:
                    print("\nConsent recorded but failed to save to preferences file.")
                print("\n" + self.options)
                break

            elif answer == 'N':  # user doesn't consent
                self.user_consent = False
                self.preferences.update_consent(False)
                print("Consent not given. Exiting application...")
                return True  # tells cmdloop() to exit

            else:  # invalid input from user
                # Make sure this matches your actual error message
                print("Invalid response. Please enter 'Y', 'N', 'back', or 'cancel'.")

    def do_filepath(self, arg):
        '''User specifies the project's filepath'''
        self.update_history(self.cmd_history, "filepath")

        # Show current filepath if exists
        current_path = self.preferences.get_project_filepath()
        if current_path:
            print(f"Current filepath: {current_path}")

        while True:
            prompt = "Paste or type the full filepath to your zipped project folder: (or 'back'/'cancel' to return): "
            answer = input(prompt).strip()

            # Handle exit/quit first
            if answer.lower() in ['exit', 'quit']:
                return self.do_exit(arg)

            # Check if user wants to cancel
            if self._handle_cancel_input(answer, "main"):
                self.project_filepath = ''
                self.cmd_history.clear()
                print("\n" + self.options)
                return  # Return to main menu

            # Normalize the user input path
            normalized_path = normalize_path(answer)

            # Validate the normalized filepath
            error_code = _is_valid_filepath_to_zip(normalized_path)
            if error_code == 0:
                break  # Valid filepath found, exit the loop
            elif error_code == 1:
                print("\nError: The provided filepath is invalid. Please try again.\n")
            elif error_code == 2:
                print(
                    "\nError: The provided filepath does not point to a zip file. Please try again.\n")
            elif error_code == 3:
                print(
                    "\nError: The provided filepath does not exist. Please try again.\n")

        # Process the filepath
        self.project_filepath = normalized_path
        # Save filepath to preferences
        success = self.preferences.update_project_filepath(normalized_path)
        print("\nFilepath successfully received and saved to preferences")
        if not success:
            print("Warning: Failed to save filepath to preferences file.")
        print(self.project_filepath)
        print("\n" + self.options)

    def do_begin(self, arg):
        '''Begin the mining process. User must give consent and provide filepath prior.'''
        self.update_history(self.cmd_history, "begin")

        if not self.user_consent:
            print(
                "\nError: Missing consent. Type perms or 1 to read user permission agreement.")
            print("\n" + self.options)
            return

        # Use filepath from preferences if not set in instance variable
        if not self.project_filepath:
            self.project_filepath = self.preferences.get_project_filepath()

        if not self.project_filepath:
            print("\nError: No project filepath configured. Please set a filepath first.")
            print("\n" + self.options)
            return

        print(f"\nBeginning analysis of: {self.project_filepath}")

        # Show advanced configuration being used
        prefs = self.preferences.load_preferences()
        start_time, end_time = self.preferences.get_date_range()
        ignored_files = self.preferences.get_files_to_ignore()

        if start_time or end_time:
            print(f"Date filtering: {start_time or 'Any'} to {end_time or 'Any'}")
        if ignored_files:
            print(f"Ignoring file types: {', '.join(ignored_files)}")

        start_miner(self.project_filepath, self.user_email)
        self._prompt_portfolio_name()

        prompt = "\n Would you like to continue analyzing? (Y/N)"
        answer = input(prompt).strip()

        if answer in ['Y', 'y', 'Yes', 'yes']:
            print("\n" + self.options)
        else:
            return self.do_exit(arg)

    def _prompt_portfolio_name(self):
        """
        Prompt the user to optionally rename the most recently created portfolio.
        Keeps the existing name (zipped folder stem) if left blank.
        """
        if not self.project_filepath:
            return

        default_title = Path(self.project_filepath).stem
        prompt = f"Enter a name for your portfolio (leave blank to keep '{default_title}'): "
        new_title = input(prompt).strip()

        if new_title.lower() in ['exit', 'quit']:
            return self.do_exit("")

        if self._handle_cancel_input(new_title, "main"):
            print("\n" + self.options)
            return

        if not new_title:
            print(f"Keeping existing portfolio name '{default_title}'")
            # Track last portfolio title for retrieval
            if hasattr(self.preferences, "update") and callable(getattr(self.preferences, "update", None)):
                self.preferences.update("last_portfolio_title", default_title)
            return

        success, message = rename_user_report(default_title, new_title)
        print(message)
        if success and hasattr(self.preferences, "update") and callable(getattr(self.preferences, "update", None)):
            self.preferences.update("last_portfolio_title", new_title)


    def do_login(self, arg):
        '''Configure user login credentials'''
        self.update_history(self.cmd_history, "login")

        # Show current credentials if they exist
        current_name, current_password, current_email = self.preferences.get_credentials()
        if current_name:
            print(f"Current user: {current_name}")
            print("Password: [hidden]")

        print("\nEnter your login credentials:")

        # Get username with retry loop
        while True:
            name = input("Enter your name: (or 'back'/'cancel' to return): ").strip()
            if self._handle_cancel_input(name, "main"):
                print("\n" + self.options)
                return
            # Handle exit/quit first
            if name.lower() in ['exit', 'quit']:
                return self.do_exit(arg)
            if name:
                break
            print("Name cannot be empty. Please try again.")

        # Get password with retry loop
        while True:
            password = input("Enter your password: (or 'back'/'cancel' to return): ").strip()
            if self._handle_cancel_input(password, "main"):
                print("\n" + self.options)
                return
            # Handle exit/quit first
            if password.lower() in ['exit', 'quit']:
                return self.do_exit(arg)
            if password:
                break
            print("Password cannot be empty. Please try again.")

        # Save credentials
        self.user_name = name
        self.user_password = password
        success = self.preferences.update_credentials(
            name, password, self.user_email)

        if success:
            print(f"\nLogin credentials saved successfully!")
            print(f"User: {name}")
            print("Password: [hidden]")
        else:
            print("Warning: Failed to save credentials to preferences file.")

        print("\n" + self.options)

    def do_preferences(self, arg):
        '''Advanced preferences configuration submenu'''
        self.update_history(self.cmd_history, "preferences")

        while True:
            print("\n=== Preferences Configuration ===")
            print("(1) Configure Date Range Filtering")
            print("(2) Configure Files to Ignore")
            print("(3) Reset to Defaults")
            print("(4) Back to Main Menu")

            choice = input("\nSelect option (1-4), or 'exit'/'quit' to close app): ").strip()

            # User enters exit/quit
            if choice.lower() in ['exit', 'quit']:
                return self.do_exit(arg)

            if self._handle_cancel_input(choice, "main"):
                print("\n" + self.options)
                return

            if choice == "1":
                self._configure_date_range()
            elif choice == "2":
                self._configure_files_to_ignore()
            elif choice == "3":
                self._reset_preferences()
            elif choice == "4":
                print("\n" + self.options)
                return
            else:
                print("Invalid choice. Please select 1-4.")



    def do_view(self, arg):
        '''Display current preferences and configuration'''
        self.update_history(self.cmd_history, "view")

        while True:
            print("\n=== Current Configuration ===")
            prefs = self.preferences.load_preferences()

            print(f"User Consent: {'✓ Granted' if prefs.get('consent') else '✗ Not granted'}")
            print(f"Project Filepath: {prefs.get('project_filepath') or 'Not set'}")
            print(f"User Name: {prefs.get('user_name') or 'Not set'}")
            print(f"User Email: {prefs.get('user_email') or 'Not set'}")
            print(f"Date Range: {self.preferences.get_date_range_display()}")



            # Files to ignore
            ignored_files = prefs.get('files_to_ignore', [])
            if ignored_files:
                print(f"Ignored Extensions: {', '.join(ignored_files)}")
            else:
                print("Ignored Extensions: None")

            print(f"Last Updated: {prefs.get('last_updated', 'Never')}")
            print(f"Preferences File: {self.preferences.get_preferences_file_path()}")

            # Prompt user for next action
            prompt = "\nPress '6' to configure preferences, or 'back'/'cancel' to return to main menu: "
            user_input = input(prompt).strip()

            # Check if user wants to cancel
            if self._handle_cancel_input(user_input, "main"):
                print("\n" + self.options)
                break

            # Handle exit/quit
            if user_input.lower() in ['exit', 'quit']:
                return self.do_exit(arg)

            # Check if user wants to go to preferences
            if user_input == '6':
                return self.do_preferences(arg)

            # Invalid input
            print("Invalid input. Press '6' for preferences or 'back'/'cancel' to return.")

    def do_portfolio_delete(self, arg):
        '''Delete a previously generated portfolio/user report'''
        self.update_history(self.cmd_history, "delete")

        print("\n=== Delete Portfolio ===")
        print("You can delete a portfolio by:")
        print("  1. Select from list of existing portfolios")
        print("  2. Enter portfolio name (or press Enter to use preferences)")

        while True:
            user_input = input("\nEnter your choice (1-2) or portfolio name (or 'back'/'cancel' to return): ").strip()

            # Handle exit/quit FIRST
            if user_input.lower() in ['exit', 'quit']:
                return self.do_exit(arg)

            # Handle cancel
            if self._handle_cancel_input(user_input, "main"):
                print("\n" + self.options)
                return

            # Option 1: List existing portfolios
            if user_input == "1":
                selected_portfolio = self._list_and_select_portfolio()
                if selected_portfolio is None:
                    continue  # User cancelled or no portfolios found
                user_input = selected_portfolio
            # Option 2 or empty: use input as portfolio name or get from preferences
            elif user_input == "2" or not user_input:
                user_input = self.preferences.get_project_filepath()
                if not user_input:
                    print("No filepath in preferences. Please enter a portfolio name.")
                    continue
                # Extract portfolio name from filepath
                from pathlib import Path
                user_input = Path(user_input).stem
                print(f"Using portfolio from preferences: {user_input}")
            # Otherwise, user_input is the portfolio name

            # Get portfolio info before deleting
            from src.classes.report import UserReport
            found, info = UserReport.get_portfolio_info(user_input)

            if not found:
                print(f"\n✗ Portfolio '{user_input}' not found in database")
                retry = input("Try again? (Y/N): ").strip().lower()
                if retry != 'y':
                    break
                continue

            # Show what will be deleted
            print(f"\nFound portfolio: {info['title']}")
            print(f"Associated projects: {info['project_count']}")

            # Confirm deletion
            confirm = input("\nAre you sure you want to delete this portfolio? (Y/N): ").strip().lower()

            # Handle exit/quit during confirmation
            if confirm in ['exit', 'quit']:
                return self.do_exit(arg)

            if confirm != 'y':
                print("Deletion cancelled")
                print("\n" + self.options)
                return

            # Perform deletion using database_modify function
            success, message = UserReport.delete_portfolio(user_input)

            if success:
                print(f"\n✓ {message}")
            else:
                print(f"\n✗ {message}")
                retry = input("Try again? (Y/N): ").strip().lower()
                if retry != 'y':
                    break
                continue

            print("\n" + self.options)
            return

    def do_portfolio_retrieve(self, arg):
        '''Retrieve and display a stored portfolio'''
        self.update_history(self.cmd_history, "retrieve")

        print("\n=== Retrieve Portfolio ===")
        print("You can retrieve a portfolio by:")
        print("  1. Select from list of existing portfolios")
        print("  2. Enter portfolio name (or leave blank to use last analyzed)")

        while True:
            user_input = input(
                "\nEnter your choice (1-2), portfolio name, or leave blank for last analyzed (or 'back'/'cancel' to return): "
            ).strip()

            if user_input.lower() in ['exit', 'quit']:
                return self.do_exit(arg)

            if self._handle_cancel_input(user_input, "main"):
                print("\n" + self.options)
                return

            portfolio_name = user_input

            if user_input == "1":
                selected = self._list_and_select_portfolio()
                if selected is None:
                    continue
                portfolio_name = selected
            elif user_input == "2":
                portfolio_name = input("Enter portfolio name: ").strip()

                if portfolio_name.lower() in ['exit', 'quit']:
                    return self.do_exit(arg)

                if self._handle_cancel_input(portfolio_name, "main"):
                    print("\n" + self.options)
                    return

                if not portfolio_name:
                    # Fall back to last analyzed just like blank input
                    last_title = self.preferences.get("last_portfolio_title", "")
                    if last_title:
                        portfolio_name = last_title
                        print(f"Using last analyzed portfolio: {portfolio_name}")
                    else:
                        pref_path = self.preferences.get_project_filepath()
                        if not pref_path:
                            print("Portfolio name cannot be empty.")
                            continue
                        portfolio_name = Path(pref_path).stem
                        print(f"Using last analyzed portfolio: {portfolio_name}")
            elif user_input == "":
                # Try last stored portfolio title first (honors renames)
                last_title = self.preferences.get("last_portfolio_title", "")
                if last_title:
                    portfolio_name = last_title
                    print(f"Using last analyzed portfolio: {portfolio_name}")
                else:
                    pref_path = self.preferences.get_project_filepath()
                    if not pref_path:
                        print("No stored filepath in preferences. Please enter a portfolio name.")
                        continue
                    portfolio_name = Path(pref_path).stem
                    print(f"Using last analyzed portfolio: {portfolio_name}")

            try:
                from src.database.utils.database_access import get_user_report
                report = get_user_report(portfolio_name)
                print("\n-------- Portfolio --------\n")
                print(report.to_user_readable_string())
                print("\n-------------------------\n")
                print("\n" + self.options)
                return
            except Exception:
                print(f"\n✗ Portfolio '{portfolio_name}' not found in database")
                retry = input("Try again? (Y/N): ").strip().lower()
                if retry != 'y':
                    print("\n" + self.options)
                    return

    def _list_and_select_portfolio(self) -> Optional[str]:
        """
        List all existing portfolios and let user select one to delete.

        Returns:
            str: The title of selected portfolio, or None if cancelled
        """
        from src.classes.report import UserReport

        portfolios = UserReport.list_all_portfolios()

        if not portfolios:
            print("\nNo portfolios found in database.")
            return None

        # Display portfolios
        print("\n=== Existing Portfolios ===")
        for idx, portfolio in enumerate(portfolios, 1):
            print(f"({idx}) {portfolio['title']}")
            print(f"    Projects: {portfolio['project_count']}")
            print()

        # Let user select
        while True:
            choice = input(f"Select portfolio (1-{len(portfolios)}), 'back'/'cancel' to return, or 'exit'/'quit' to close app: ").strip()

            # Handle exit/quit FIRST
            if choice.lower() in ['exit', 'quit']:
                self.do_exit("")
                return None

            # Handle cancel
            if choice.lower() in ['back', 'cancel']:
                return None

            # Validate selection
            try:
                idx = int(choice)
                if 1 <= idx <= len(portfolios):
                    selected = portfolios[idx - 1]
                    return selected['title']
                else:
                    print(f"Please enter a number between 1 and {len(portfolios)}")
            except ValueError:
                print("Invalid input. Please enter a number, 'back', 'cancel', 'exit', or 'quit'.")

    def _configure_date_range(self):
        '''Configure date filtering for files'''
        print("\nConfigure date range for file filtering (YYYY-MM-DD format)")

        while True: # Outer loop to retry on invalid date ranges
            start_date = None
            end_date = None

            while True:
                start_input = input("Enter start date (or 'skip' for no limit): ").strip()

                # Handle exit/quit
                if start_input.lower() in ['exit', 'quit']:
                    return self.do_exit("")

                # User enters back / cancel
                if self._handle_cancel_input(start_input, "preferences"):
                    return

                if start_input.lower() == 'skip':
                    start_date = None
                    break

                if self._parse_date_input(start_input):
                    start_date = start_input
                    break
                print("Invalid date format. Use YYYY-MM-DD")

            while True:
                end_input = input("Enter end date (or 'skip' for no limit): ").strip()

                # Handle exit/quit
                if end_input.lower() in ['exit', 'quit']:
                    return self.do_exit("")

                # User enters back / cancel
                if self._handle_cancel_input(end_input, "preferences"):
                    return

                if end_input.lower() == 'skip':
                    end_date = None
                    break

                if self._parse_date_input(end_input):
                    end_date = end_input
                    break
                print("Invalid date format. Use YYYY-MM-DD")

            # Validate date range logic: start must be before end
            if start_date and end_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')

                # start_dt > end_dt and not start_dt >= end_dt  so that if user
                # only wants to analyze files for a single given date, they can.
                if start_dt > end_dt:
                    print("\n✗ Error: Start date must be earlier than end date.")
                    print(f"   Start: {start_date}")
                    print(f"   End: {end_date}")
                    print("   Please try again.\n")
                    continue  # Loop back to ask for dates again

            # If gotten here, dates are valid, save and exit
            success = self.preferences.update_date_range(start_date, end_date)
            if success:
                print("✓ Date range configuration saved")
                if start_date and end_date:
                    print(f"   Filtering files between {start_date} and {end_date}")
                elif start_date:
                    print(f"   Filtering files after {start_date}")
                elif end_date:
                    print(f"   Filtering files before {end_date}")
                else:
                    print("   No date filtering applied")
            else:
                print("✗ Failed to save date range configuration")

            break # Exit the outer loop after successful save


    def _configure_files_to_ignore(self):
        '''Configure file extensions to ignore'''
        print("\nConfigure file extensions to ignore during analysis")
        print("Enter extensions separated by commas (e.g., .log, .tmp, .cache)")

        current = self.preferences.get_files_to_ignore()
        if current:
            print(f"Current ignored extensions: {', '.join(current)}")

        extensions_input = input("Extensions to ignore (or 'clear' to remove all): ").strip()

        # User enters back / cancel
        if self._handle_cancel_input(extensions_input, "preferences"):
            return

        # Handle exit/quit
        if extensions_input.lower() in ['exit', 'quit']:
            self.do_exit("")
            return

        if extensions_input.lower() == 'clear':
            extensions = []
        else:
            extensions = [ext.strip() for ext in extensions_input.split(',') if ext.strip()]
            # Ensure extensions start with dot
            extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]

        success = self.preferences.update_files_to_ignore(extensions)
        if success:
            if extensions:
                print(f"✓ Now ignoring: {', '.join(extensions)}")
            else:
                print("✓ Cleared all ignored extensions")
        else:
            print("✗ Failed to save file ignore configuration")


    def _reset_preferences(self):
        '''Reset all preferences to defaults'''
        confirm = input("Reset ALL preferences to defaults? This cannot be undone. (Y/N): ").strip()

        # User enters back /cancel
        if self._handle_cancel_input(confirm, "preferences"):
            return

        # Handle exit/quit
        if confirm.lower() in ['exit', 'quit']:
            return self.do_exit("")

        if confirm.lower() == 'y':
            # User enters back /cancel
            if self._handle_cancel_input(confirm, "preferences"):
                return

            success = self.preferences.reset()
            if success:
                print("✓ All preferences reset to defaults")
                # Reload instance variables
                self._load_existing_preferences()
            else:
                print("✗ Failed to reset preferences")
        else:
            print("Reset cancelled")

    def _parse_date_input(self, date_str: str) -> bool:
        '''Validate date input format (YYYY-MM-DD)'''
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def update_history(self, cmd_history: list, cmd: str):
        '''
        We will track the user's history (entered commands) so that they can go back if they wish.
        This function updated the `cmd_history` list to do so.
        '''
        if len(cmd_history) == 3:  # only track their 3 most recent commands
            cmd_history.pop(0)  # remove the oldest item (first item)
        cmd_history.append(cmd)  # add new command to the end

        return cmd_history

    def do_back(self, arg):
        '''Return to the previous screen'''

        if len(self.cmd_history) > 1:  # Need at least 2 items to go back
            # Get the last command (the one we want to go back to)
            previous_cmd = self.cmd_history[-1]  # Get last command
            self.cmd_history.pop()  # Remove current command from history

            match previous_cmd:
                case "perms":
                    return self.do_perms(arg)
                case "filepath":
                    return self.do_filepath(arg)
                case "begin":
                    return self.do_begin(arg)
                case "email":
                    return self.do_email(arg)
                case "login":
                    return self.do_login(arg)
                case "preferences":
                    return self.do_preferences(arg)
                case "view":
                    return self.do_view(arg)
                case "delete":
                    return self.do_portfolio_delete(arg)
                case "retrieve":
                    return self.do_portfolio_retrieve(arg)
        else:
            print("\nNo previous command to return to.")
            print(self.options)


    def _handle_cancel_input(self, user_input, menu_location):
        '''
        Helper method to check if user wants to cancel and handle it.
        Returns True if cancel was triggered, False otherwise.
        '''
        if user_input.strip().lower() in ['back', 'cancel']:
          # Remove the current command from history since user is cancelling

            if len(self.cmd_history) > 0:
                cancelled_cmd = self.cmd_history.pop()
                print(f"\nCancelled '{cancelled_cmd}' operation.")
                print(f"Returning to {menu_location} menu.")
            else:
                print(f"\nReturning to {menu_location} menu.")
            return True

        return False

    def do_email(self, arg):
        '''
        Add an email to the user's configuration such that inidividual contributions can be measured in a Git-tracked project
        '''
        self.update_history(self.cmd_history, "email")

        prompt = "Enter the email you use for your Git/GitHub account: (or 'back' / 'cancel' to return): "
        answer = input(prompt).strip()

        # Check if user wants to cancel
        if self._handle_cancel_input(answer, "main"):
            print("\n" + self.options)
            return  # Return to main menu

        # Handle exit/quit first
        if answer.lower() in ['exit', 'quit']:
            return self.do_exit(arg)

        while (not self.is_valid_email(answer)):
            prompt = "Please enter a valid email: (or 'back' / 'cancel' to return): "
            answer = input(prompt).strip()

            # Check if user wants to cancel
            if self._handle_cancel_input(answer, "main"):
                print("\n" + self.options)
                return  # Return to main menu

        # Process the email
        self.user_email = answer
        # Save email to preferences
        success = self.preferences.update_user_email(answer)
        print("\nEmail successfully received and saved to preferences")
        print(self.user_email)
        if not success:
            print("Warning: Failed to save email to preferences file.")
        print("\n" + self.options)

    def is_valid_email(self, email: str) -> bool:
        """Email validation helper method."""
        EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(EMAIL_REGEX, email))

    def default(self, line):
        '''
        Overwrite the `default()` function so that our program
        accepts, for example, either '1' or 'perms' as input to
        call the `do_perms()` function.
        '''
        commands = {
            "1": self.do_perms,
            "2": self.do_filepath,
            "3": self.do_begin,
            "4": self.do_email,
            "5": self.do_login,
            "6": self.do_preferences,
            "7": self.do_view,
            "8": self.do_portfolio_delete,
            "9": self.do_portfolio_retrieve,
        }

        # Make commands case-insensitive
        func = commands.get(line.strip().lower())
        if func:
            return func("")
        else:
            print(f"Unknown command: {line}. Type 'help' or '?' for options.")

    def do_exit(self, arg):
        '''Exits the program.'''
        print("\nThank you for using Artifact Miner! Exiting the program...")
        sys.exit(0)
