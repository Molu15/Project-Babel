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
            item('Reload Config', self._reload_config),
            item('Exit', self._exit_app)
        )

        # Load icon image
        # High contrast colors: Yellow and Blue
        icon_image = self._create_image(64, 64, 'yellow', 'blue')
        
        self.icon = pystray.Icon("Project Babel", icon_image, "Project Babel", menu)

    def _set_profile(self, profile_name):
        print(f"Tray: Switching to {profile_name}")
        self.config_manager.set_active_profile(profile_name)
        # Force re-registration of hotkeys in observer
        self.observer.stop()
        self.observer.register_hotkeys()
        self.observer.start()
        
        # Update icon menu state (pystray might need invalidation, but menu is dynamic usually)
        # self.icon.update_menu() # Some versions require this

    def _reload_config(self):
        print("Tray: Reloading Config...")
        self.config_manager.load_config()
        self.config_manager.load_active_profile()
        
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
