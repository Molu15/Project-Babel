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

def log_debug(msg):
    with open("babel_debug.log", "a") as f:
        f.write(f"{time.ctime()}: {msg}\n")
    print(msg)

def main():
    log_debug("Starting Main...")
    if not is_admin():
        log_debug("Not admin, requesting elevation...")
        try:
            # Re-run the program with admin rights
            # "runas" verb forces the UAC prompt
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit() # Exit this non-admin instance
        except Exception as e:
            log_debug(f"Failed to elevate: {e}")
            print("Please confirm 'Yes' in the UAC dialog or run as Administrator manually.")
            return
            
    try:
        log_debug("In Admin Mode. Importing components...")
        
        # Initialize components
        from config.config_manager import ConfigManager
        config_manager = ConfigManager(".") # Root is current dir
        
        context_manager = ContextManager()
        injection_module = InjectionModule()
        
        log_debug("Components initialized. Starting Observer...")
        
        # Start observer
        observer = InputObserver(context_manager, config_manager, injection_module)
        observer.register_hotkeys()
        observer.start() 
        
        log_debug("Observer Started. Initializing Tray...")

        # Initialize UI
        from ui.tray_icon import TrayIcon
        tray = TrayIcon(config_manager, observer)
        
        log_debug("Tray Initialized. Entering Main Loop...")
        print("\n" + "="*50)
        print("CHECK YOUR SYSTEM TRAY (BOTTOM RIGHT)")
        print("Look for the Project Babel Icon (Green Tower)!")
        print("Use the icon to Switch Modes or Exit.")
        print("="*50 + "\n")
        
        # Run Tray (Blocking)
        tray.run()
        log_debug("Tray.run() returned (Exiting).")
        
    except KeyboardInterrupt:
        log_debug("User interrupted (Ctrl+C). Exiting...")
        try:
             observer.stop()
             tray.icon.stop()
        except:
             pass
        sys.exit(0)
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        log_debug(f"CRITICAL ERROR: {err}")
        print(f"CRITICAL ERROR: {e}")
        input("Press Enter to crash exit...") # Keep window open

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
