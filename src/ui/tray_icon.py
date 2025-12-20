import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import threading
import os

class TrayIcon:
    def __init__(self, config_manager, observer):
        self.config_manager = config_manager
        self.observer = observer
        self.icon = None
        self._setup_icon()

    def _create_image(self, width, height, color1, color2):
        # Generate an icon if none exists
        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle(
            (width // 2, 0, width, height // 2),
            fill=color2)
        dc.rectangle(
            (0, height // 2, width // 2, height),
            fill=color2)
        return image

    def _setup_icon(self):
        # Determine check state for menu items
        def is_checked(profile_name):
            return lambda item: self.config_manager.config.get("active_profile") == profile_name

        # Define Menu
        menu = pystray.Menu(
            item('Project Babel', lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item(
                'Figma -> Photoshop', 
                lambda: self._set_profile('figma_to_photoshop.json'),
                checked=is_checked('figma_to_photoshop.json'),
                radio=True
            ),
            item(
                'Photoshop -> Figma', 
                lambda: self._set_profile('photoshop_to_figma.json'),
                checked=is_checked('photoshop_to_figma.json'),
                radio=True
            ),
            item(
                'Custom', 
                lambda: self._set_profile('custom.json'),
                checked=is_checked('custom.json'),
                radio=True
            ),
            pystray.Menu.SEPARATOR,
            item('Edit Custom Config', self._open_editor),
            item('Reload Config', self._reload_config),
            item('Exit', self._exit_app)
        )
        
        
        
        # Load icon image
        try:
             # Try loading assets/icon.png
             icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'icon.png')
             icon_image = Image.open(icon_path)
        except Exception as e:
             print(f"Failed to load icon: {e}. generating default.")
             icon_image = self._create_image(64, 64, 'yellow', 'blue')
        
        self.icon = pystray.Icon("Project Babel", icon_image, "Project Babel", menu)


    def _open_editor(self):
        # Run the editor in a separate process to avoid Tkinter/PyStray conflicts
        import subprocess
        import sys
        
        # New: Target semantic_config.json
        semantic_path = self.config_manager.semantic_config_path
        
        # ALWAYS target custom.json for editing
        target_profile = "custom.json"
        
        # Script path: src/ui/editor_window.py
        script_path = os.path.join(os.path.dirname(__file__), 'editor_window.py')
        
        print(f"Tray: Spawning editor for {semantic_path} [{target_profile}]")
        
        def run_and_reload():
            try:
                # Use subprocess to run the script
                # Pass both FILE and PROFILE
                result = subprocess.run([sys.executable, script_path, str(semantic_path), target_profile])
                
                print(f"Tray: Editor process ended with code {result.returncode}")
                
                if result.returncode == 0:
                     print("Tray: Editor saved. Switching to Custom Profile...")
                     
                     # Reload changed config from disk
                     self.config_manager.load_semantic_config()

                     # Switch to Custom Profile (This reloads config and re-registers hotkeys)
                     self._set_profile('custom.json')
                     
                     # Force menu refresh if supported
                     if hasattr(self.icon, 'update_menu'):
                         self.icon.update_menu()

                else:
                     print("Tray: Editor cancelled (no changes).")
                
            except Exception as e:
                print(f"Error running editor process: {e}")

        # Run in a thread so we don't block the tray
        t = threading.Thread(target=run_and_reload, daemon=True)
        t.start()


    def _set_profile(self, profile_name):
        try:
            print(f"Tray: Switching to {profile_name}")
            self.config_manager.set_active_profile(profile_name)
            # Force re-registration of hotkeys in observer
            self.observer.stop()
            self.observer.register_hotkeys()
            self.observer.start()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error switching profile: {e}")

    def _reload_config(self):
        print("Tray: Reloading Config...")
        self.config_manager.load_config()
        self.config_manager.load_semantic_config()
        
        self.observer.stop()
        self.observer.register_hotkeys()
        self.observer.start()

    def _exit_app(self):
        print("Tray: Exiting...")
        self.observer.stop()
        self.icon.stop()
        os._exit(0) # Force exit ensuring threads kill

    def run(self):
        """Runs the tray icon. BLOCKING."""
        self.icon.run()

    def run_detached(self):
        """Runs the tray icon in a separate thread (if possible, but pystray prefers main thread often)"""
        # pystray on Windows usually requires to be on the main thread for menu handling.
        # We might need to invert main.py: Run tray on main, observer on thread.
        self.run()
