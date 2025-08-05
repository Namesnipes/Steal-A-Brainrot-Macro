import json
import os
from Events import Events

class SettingsManager:
    """Manages loading and saving of application settings."""
    def __init__(self, filename="settings.json"):
        self.filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), filename))
        self.settings = self._load()

    def _get_default_settings(self):
        """Returns a dictionary of default settings."""
        return {
            "auto_collect_money": True,
            "collect_money_interval": 300,
            "auto_scan_npcs": True,
            "income_threshold": 1000,
            "min_rarity": "Rare",
            "im_poor": False,  # Flag for donation banner
        }

    def _load(self):
        """Loads settings from the file, or returns defaults if file doesn't exist/is invalid."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            Events().debug(f"Could not load settings file: {e}. Using defaults.")
        
        return self._get_default_settings()

    def save(self, settings_dict):
        """Saves the provided settings dictionary to the file."""
        self.settings = settings_dict
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            Events().debug(f"Error saving settings: {e}")

    def get_settings(self):
        """Returns the current settings."""
        return self.settings
