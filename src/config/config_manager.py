import json
import os
from pathlib import Path

class ConfigManager:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.config_path = self.project_root / "config.json"
        self.mappings_dir = self.project_root / "src" / "config" / "mappings"
        
        self.config = {
            "active_profile": "figma_to_photoshop.json",
            "custom_overrides_enabled": True
        }
        self.active_profile_data = {}
        
        self.load_config()
        self.load_active_profile()

    def load_config(self):
        """Loads the main config.json file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error loading config.json: {e}. Using defaults.")
                self.save_config() # Save defaults if failed
        else:
            self.save_config()

    def save_config(self):
        """Saves the current configuration to config.json."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config.json: {e}")

    def load_active_profile(self):
        """Loads the profile JSON specified in config.json."""
        profile_name = self.config.get("active_profile", "figma_to_photoshop.json")
        profile_path = self.mappings_dir / profile_name
        
        if profile_path.exists():
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    self.active_profile_data = json.load(f)
                print(f"Loaded profile: {profile_name}")
            except Exception as e:
                print(f"Error loading profile {profile_name}: {e}")
                self.active_profile_data = {"mappings": [], "target_apps": []}
        else:
            print(f"Profile {profile_name} not found at {profile_path}")
            self.active_profile_data = {"mappings": [], "target_apps": []}

    def set_active_profile(self, profile_filename):
        """Sets a new active profile and reloads."""
        self.config["active_profile"] = profile_filename
        self.save_config()
        self.load_active_profile()

    def get_active_profile_targets(self):
        """Returns the list of target applications for the current profile."""
        return self.active_profile_data.get("target_apps", [])

    def get_active_mappings(self):
        """Returns the list of mappings for the current profile."""
        return self.active_profile_data.get("mappings", [])

    def is_rule_enabled(self, rule_id):
        """
        Checks if a specific rule is enabled.
        For now, since we are doing rigid profiles, if the rule exists in the active 
        profile mapping list, it is 'enabled'.
        Future: Add specific toggleable flags per rule if needed.
        """
        # This is a placeholder for more granular control if we add it later.
        # Currently, presence in the list implies enablement.
        return True
