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
        # keyboard.send transmits both press    def inject(self, command):
        try:
            if not command:
                return

            # Explicit Injection with Restoration
            modifiers, key = self._parse_combo(command)
            
            # 1. Force Press modifiers
            for mod in modifiers:
                keyboard.press(mod)
            time.sleep(0.02) 
            
            # 2. Key Click
            keyboard.press(key)
            time.sleep(0.02)
            keyboard.release(key)
            time.sleep(0.01)
                
            # 3. Release synthesized modifiers
            for mod in reversed(modifiers):
                keyboard.release(mod)
            time.sleep(0.01)

            # 4. ROBUST RESTORE
            import ctypes
            user32 = ctypes.windll.user32
            
            # Check and Restore Ctrl
            if (user32.GetAsyncKeyState(0x11) & 0x8000) != 0:
                ctypes.windll.user32.keybd_event(0x11, 0, 0, 0) # VK_CONTROL Down
            
            # Check and Restore Shift
            if (user32.GetAsyncKeyState(0x10) & 0x8000) != 0:
                ctypes.windll.user32.keybd_event(0x10, 0, 0, 0) # VK_SHIFT Down

            # Check and Restore Alt
            if (user32.GetAsyncKeyState(0x12) & 0x8000) != 0:
                ctypes.windll.user32.keybd_event(0x12, 0, 0, 0) # VK_MENU Down
                
            # print(f"DEBUG: Injected {command} and restored modifiers")
        except Exception as e:
            # Fallback
            print(f"Injection Failed: {e}")
            try:
                keyboard.send(command)
            except:
                pass

    def _parse_combo(self, command):
        """Simple splitter. 'ctrl+shift+z' -> (['ctrl', 'shift'], 'z')"""
        parts = command.split('+')
        return parts[:-1], parts[-1]
