"""
This file defines the UserPreferences class.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class UserPreferences:
    """Manages User Preferences with JSON storage in database folder"""

    def __init__(self, preferences_file: Optional[str] = None):
        cli_folder_path = Path(__file__).parent
        filename = preferences_file or "preferences.json"
        self.preferences_file = cli_folder_path / filename

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

    def update_credentials(self, name: str, password: str, email: Optional[str] = None) -> bool:
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
