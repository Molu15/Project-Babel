import keyboard
import time
import ctypes
import sys
from core.observer import InputObserver
from core.context import ContextManager
from core.translator import TranslationEngine
from core.injector import InjectionModule

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    if not is_admin():
        print("Requesting administrator privileges...")
        try:
            # Re-run the program with admin rights
            # "runas" verb forces the UAC prompt
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit() # Exit this non-admin instance
        except Exception as e:
            print(f"Failed to elevate: {e}")
            print("Please confirm 'Yes' in the UAC dialog or run as Administrator manually.")
            return

    print("Starting Project Babel...")
    
    # Initialize components
    context_manager = ContextManager()
    translation_engine = TranslationEngine()
    injection_module = InjectionModule()
    
    # Load mappings
    translation_engine.load_mapping('src/config/mappings/figma_to_photoshop.json')
    
    # Start observer
    observer = InputObserver(context_manager, translation_engine, injection_module)
    # Using hotkey registration strategy for safety and specific targeting
    observer.register_hotkeys()
    observer.start() # Starts context monitoring thread

    
    print("Project Babel is running. Press Ctrl+C to exit.")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
            # Optional: Periodic status checks or heartbeat
    except KeyboardInterrupt:
        print("Stopping Project Babel...")
        observer.stop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nCRITICAL ERROR: {e}")
        input("Press Enter to exit...")
