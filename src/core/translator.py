import json
import keyboard
import os

class TranslationEngine:
    def __init__(self):
        self.mappings = [] # List of dicts: {'input_parts': {'modifiers': set, 'key': str}, 'output': str}

    def load_mapping(self, filepath):
        """
        Loads mappings from a JSON file.
        """
        if not os.path.exists(filepath):
            print(f"Warning: Mapping file not found: {filepath}")
            return
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            raw_mappings = data.get('mappings', [])
            self.mappings = []
            
            for rule in raw_mappings:
                input_str = rule['input'].lower()
                output_str = rule['output']
                
                # Parse input string into modifiers and key
                # Example: "ctrl+shift+z" -> modifiers={'ctrl', 'shift'}, key='z'
                parts = input_str.split('+')
                key = parts[-1]
                modifiers = set(parts[:-1])
                
                # Handling special cases for German layout if needed
                # e.g. 'ö' is just a key name in keyboard lib
                
                self.mappings.append({
                    'modifiers': modifiers,
                    'key': key,
                    'output': output_str,
                    'original': input_str
                })
            
            print(f"Loaded {len(self.mappings)} mappings from {filepath}")
            
        except Exception as e:
            print(f"Error loading mappings: {e}")

    def translate(self, event):
        """
        Checks if the event matches any rule.
        Returns the output string if matched, None otherwise.
        
        Args:
            event: keyboard.KeyboardEvent
        """
        if event.event_type != 'down':
            return None
            
        # Normalize event data
        event_key = event.name.lower()
        # event.modifiers is usually a list of strings like "ctrl", "alt"
        # Note: keyboard lib modifiers might be slightly different than our set.
        current_modifiers = set(event.modifiers) if event.modifiers else set()
        
        # We need to filter out 'shift' if the key itself implies shift? 
        # No, 'keyboard' separates them usually.
        
        for rule in self.mappings:
            if rule['key'] == event_key:
                print("rule = event key")
                # Check modifiers
                # We need exact match of modifiers?
                # Or at least the rule modifiers must be present.
                # If rule says "ctrl+d", and user presses "ctrl+shift+d", we probably shouldn't trigger "ctrl+d" action?
                # Usually exact match is safer.
                
                # Clean up "numpad" prefixes etc if necessary.
                
                if rule['modifiers'] == current_modifiers:
                    return rule['output']
                    
        return None
