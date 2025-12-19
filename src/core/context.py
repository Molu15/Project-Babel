import win32gui
import win32process
import psutil

class ContextManager:
    def __init__(self):
        # Target process names (executable names)
        self.target_apps = ["photoshop.exe"] 

    def is_target_active(self, target_list=None):
        """
        Checks if the currently active window matches any in the target list.
        Args:
            target_list (list): List of process names to check against.
        Returns:
            bool: True if target is active, False otherwise.
        """
        targets = target_list if target_list else self.target_apps

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
            
            if any(t.lower() in process_name for t in targets):
                # print(f"DEBUG: Context MATCH {process_name}")
                return True
                
            return False
            
        except Exception as e:
            # print(f"Context Error: {e}")
            return False
