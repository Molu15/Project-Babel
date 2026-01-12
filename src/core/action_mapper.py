import json

class ActionMapper:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        # Cache for generated mappings to avoid re-computing every frame if context doesn't change
        self._current_context = None
        self._cached_mappings = []

    def get_mappings_for_context(self, context_app):
        """
        Generates a list of mappings for the given active application context.
        
        Args:
            context_app (str): The identifier of the active app (e.g., 'photoshop', 'figma').
                               Should match the keys in system_definitions.
                               
        Returns:
            list: A list of dicts [{'input': 'Trigger', 'output': 'Command'}]
        """
        # normalize context
        context = context_app.lower()
        if "photoshop" in context:
            context_key = "photoshop"
        elif "figma" in context:
            context_key = "figma"
        else:
            # If unknown context, return empty (or default)
            return []

        # Optimization: Return cached if context hasn't changed
        # (We might need more robust invalidation if config changes at runtime)
        if context_key == self._current_context and self._cached_mappings:
             return self._cached_mappings

        definitions = self.config_manager.get_system_definitions()
        user_profile = self.config_manager.get_user_profile()
        
        mappings = []
        
        actions = definitions.get("actions", {})
        user_settings = user_profile.get("settings", {})
        
        active_profile_name = self.config_manager.config.get("active_profile", "UNKNOWN")
        print(f"DEBUG: Generating mappings for Context='{context_key}' using Profile='{active_profile_name}'")

        for action_name, action_defs in actions.items():
            # 1. Target Command: What does the active app need?
            target_command = action_defs.get(context_key)
            if not target_command:
                # This action isn't defined for the current app
                continue
                
            # 2. User Trigger: What does the user want to press?
            preference = user_settings.get(action_name, "figma") # Default to figma if not set? Or skip?
            
            trigger_command = None
            
            if preference.startswith("custom:"):
                # "custom: f1" -> extract "f1"
                trigger_command = preference.split(":", 1)[1].strip()
            else:
                # Look up the preference in the definitions
                # e.g. preference="figma", look up actions[action_name]["figma"]
                trigger_command = action_defs.get(preference)
                
            if not trigger_command:
                 print(f"  Warning: No trigger found for action '{action_name}' with preference '{preference}'")
                 continue
                 
            # 3. Create Rule
            # Map even if input == output (Identity) to ensure explicit handling
            # if trigger_command.lower() != target_command.lower():
            
            print(f"  Rule: {action_name} | {trigger_command} -> {target_command}")
            mappings.append({
                "input": trigger_command,
                "output": target_command,
                "type": action_defs.get("type", "key") # e.g. 'gesture' for zoom
            })
                
        self._current_context = context_key
        self._cached_mappings = mappings
        return mappings

    def get_all_configured_triggers(self):
        """
        Returns a dictionary of all configured triggers as keys,
        and their associated action names/types as values.
        Used for initial hook registration.
        """
        definitions = self.config_manager.get_system_definitions()
        user_profile = self.config_manager.get_user_profile()
        actions = definitions.get("actions", {})
        user_settings = user_profile.get("settings", {})
        
        triggers = {} # trigger_key -> metadata
        
        for action_name, action_defs in actions.items():
            preference = user_settings.get(action_name, "figma")
            trigger_command = None
            
            if preference.startswith("custom:"):
                trigger_command = preference.split(":", 1)[1].strip()
            else:
                trigger_command = action_defs.get(preference)
            
            if trigger_command:
                # Store lower case key
                triggers[trigger_command.lower()] = {
                    "action": action_name,
                    "type": action_defs.get("type", "key")
                }
                
        return triggers

    def clear_cache(self):
        self._current_context = None
        self._cached_mappings = []
