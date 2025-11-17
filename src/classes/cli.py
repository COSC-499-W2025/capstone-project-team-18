"""
This file contains the command line interface (CLI) for the Artifact Miner application.
"""

import cmd
import re
import os
from src.app import start_miner

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

    def load_preferences(self) -> Dict[str, Any]:
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
            "Choose one of the following options:\n"
            "(1) Permissions\n"
            "(2) Set filepath\n"
            "(3) Begin Artifact Miner\n"
            "(4) Configure Email for Git Stats\n"
            "(5) User Login\n"
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
        print(self.ruler * len(self.options.splitlines()[0]))
        print(self.options)

        # Show preferences file location
        print(f"Preferences stored in: {self.preferences.get_preferences_file_path()}")

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
            print(f"Loaded preferences from: {self.preferences.get_preferences_file_path()}")
        else:
            print(f"Created new preferences file at: {self.preferences.get_preferences_file_path()}")

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
            if self._handle_cancel_input(answer):
                print("\n" + self.options)
                break

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

            # Check if user wants to cancel
            if self._handle_cancel_input(answer):
                self.project_filepath = ''
                self.cmd_history.clear()
                print("\n" + self.options)
                return  # Return to main menu

            # Validate the filepath
            error_code = _is_valid_filepath_to_zip(answer)
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
        self.project_filepath = answer
        # Save filepath to preferences
        success = self.preferences.update_project_filepath(answer)
        print("\nFilepath successfully received and saved to preferences")
        if not success:
            print("Warning: Failed to save filepath to preferences file.")
        print(self.project_filepath)
        print("\n" + self.options)

    def do_begin(self, arg):
        '''Begin the mining process. User must give consent and provide filepath prior.'''
        self.update_history(self.cmd_history, "begin")

        if not self.user_consent:
            print("\nError: Missing consent. Type perms or 1 to read user permission agreement.")
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
        start_miner(self.project_filepath, self.user_email)

    def do_login(self, arg):
        '''Configure user login credentials'''
        self.update_history(self.cmd_history, "login")

        # Show current credentials if they exist
        current_name, current_password, current_email = self.preferences.get_user_credentials()
        if current_name:
            print(f"Current user: {current_name}")
            print("Password: [hidden]")

        print("\nEnter your login credentials:")

        # Get username with retry loop
        while True:
            name = input("Enter your name: (or 'back'/'cancel' to return): ").strip()
            if self._handle_cancel_input(name):
                print("\n" + self.options)
                return
            if name:
                break
            print("Name cannot be empty. Please try again.")

        # Get password with retry loop
        while True:
            password = input("Enter your password: (or 'back'/'cancel' to return): ").strip()
            if self._handle_cancel_input(password):
                print("\n" + self.options)
                return
            if password:
                break
            print("Password cannot be empty. Please try again.")

        # Save credentials
        self.user_name = name
        self.user_password = password
        success = self.preferences.update_credentials(name, password, self.user_email)

        if success:
            print(f"\nLogin credentials saved successfully!")
            print(f"User: {name}")
            print("Password: [hidden]")
        else:
            print("Warning: Failed to save credentials to preferences file.")

        print("\n" + self.options)

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
        else:
            print("\nNo previous command to return to.")
            print(self.options)

    def _handle_cancel_input(self, user_input):
        '''
        Helper method to check if user wants to cancel and handle it.
        Returns True if cancel was triggered, False otherwise.
        '''
        if user_input.strip().lower() in ['back', 'cancel']:
            # Remove the current command from history since user is cancelling
            if len(self.cmd_history) > 0:
                cancelled_cmd = self.cmd_history.pop()  # Now correctly removes from end
                print(f"\nCancelled '{cancelled_cmd}' operation.")
            else:
                print("\nReturning to main menu.")
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
        if self._handle_cancel_input(answer):
            print("\n" + self.options)
            return  # Return to main menu

        while (not self.is_valid_email(answer)):
            prompt = "Please enter a valid email: (or 'back' / 'cancel' to return): "
            answer = input(prompt).strip()

            # Check if user wants to cancel
            if self._handle_cancel_input(answer):
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
        }

        # Make commands case-insensitive
        func = commands.get(line.strip().lower())
        if func:
            return func("")
        else:
            print(f"Unknown command: {line}. Type 'help' or '?' for options.")

    def do_exit(self, arg):
        '''Exits the program.'''
        print('Exiting the program...')
        return True
