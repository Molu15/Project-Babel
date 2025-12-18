import win32gui
import win32process
import psutil

class ContextManager:
    def __init__(self):
        # Target process names (executable names)
        self.target_apps = ["photoshop.exe"] 

    def is_target_active(self):
        """
        Checks if the currently active window belongs to a target process.
        Returns:
            bool: True if target is active, False otherwise.
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return False
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if not pid:
                return False

            process = psutil.Process(pid)
            process_name = process.name().lower()
            
            # Debug info (optional, helps finding the right process name)
            # print(f"DEBUG: Active Process='{process_name}'")
            
            if process_name in [app.lower() for app in self.target_apps]:
                # print(f"DEBUG: Context MATCH {process_name}")
                return True
                
            return False
            
        except Exception as e:
            # print(f"Context Error: {e}")
            return False
