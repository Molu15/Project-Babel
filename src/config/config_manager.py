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
        
        # New Semantic Config
        self.semantic_config_path = self.project_root / "src" / "config" / "semantic_config.json"
        self.semantic_data = {
            "system_definitions": {},
            "user_profile": {}
        }
        
        self.load_config()
        self.load_semantic_config()
        # self.load_active_profile() # Legacy

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

    def load_semantic_config(self):
        """Loads the semantic_config.json file."""
        if self.semantic_config_path.exists():
            try:
                with open(self.semantic_config_path, 'r', encoding='utf-8') as f:
                    self.semantic_data = json.load(f)
                print("Loaded semantic_config.json")
            except Exception as e:
                print(f"Error loading semantic_config.json: {e}")
        else:
            print("Warning: semantic_config.json not found.")

    def get_system_definitions(self):
        return self.semantic_data.get("system_definitions", {})

    def get_user_profile(self):
        # 1. Get Active Profile Name from main config (e.g. "figma_to_photoshop.json")
        active_name = self.config.get("active_profile", "figma_to_photoshop.json")
        
        # 2. Look up in semantic profiles
        profiles = self.semantic_data.get("profiles", {})
        
        # 3. Return the settings for that profile
        if active_name in profiles:
             print(f"DEBUG: Using Profile '{active_name}'")
             return profiles[active_name]
        else:
             print(f"Warning: Profile '{active_name}' not found in semantic config. Falling back to first available.")
             return next(iter(profiles.values())) if profiles else {}

    def get_semantic_targets(self):
        """
        Derives list of supported apps from system definitions.
        """
        actions = self.get_system_definitions().get("actions", {})
        apps = set()
        for action in actions.values():
            # keys of action dict are app names (except 'type')
            for key in action.keys():
                if key != "type":
                    apps.add(key)
        return list(apps)

    def save_config(self):
        """Saves the current configuration to config.json."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config.json: {e}")

    def set_active_profile(self, profile_filename):
        """Sets a new active profile and reloads."""
        # Legacy support or maybe we switch user_profile presets here?
        self.config["active_profile"] = profile_filename
        self.save_config()

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
