import keyboard
import time

class InjectionModule:
    def inject(self, command):
        """
        Injects the translated command.
        Args:
            command (str): The shortcut string (e.g. 'ctrl+j')
        """
        # Small delay to ensure original key release doesn't interfere?
        # <50ms constraint.
        # keyboard.send transmits both press and release.
        try:
            keyboard.send(command)
            print("inject command")
        except Exception as e:
            print(f"Injection Failed: {e}")
