import keyboard
import threading
import time
from core.web_listener import WebContextListener

class InputObserver:
    def __init__(self, context_manager, config_manager, injection_module):
        self.context_manager = context_manager
        self.config_manager = config_manager
        self.injection_module = injection_module
        self.running = False
        self._hook = None
        
        # Web Context Listener
        self.web_listener = WebContextListener()

        # Context Caching
        self.is_active_context = False
        self._context_thread = None

    def log_debug(self, msg):
        import time
        try:
            with open("babel_debug.log", "a") as f:
                f.write(f"{time.ctime()} [OBSERVER]: {msg}\n")
        except:
            pass

        
        # State tracking for Zoom continuity
        self.last_ctrl_wheel_time = 0
        self.zoom_lock = threading.Lock()
        self.zoom_buffer = 0
        self.zoom_active = False
        self.trigger_held = False # Track physical state
        
    def _monitor_context(self):
        """Polls context every 0.1s to update status without blocking hooks."""
        last_state = None
        while True:
            try:
                targets = self.config_manager.get_active_profile_targets()
                
                # PHASE 3: Check Web Context First
                web_app = self.web_listener.get_active_web_app()
                
                if web_app:
                    # Check if the detected web app matches any of our targets
                    # e.g. If active profile is "Figma to Photoshop", target might be "figma" (source-based) or "photoshop" (dest-based).
                    # Based on previous debugging, we treat `targets` as the context where remapping should happen.
                    self.is_active_context = any(t.lower() in web_app.lower() for t in targets) or (web_app == "figma" and "figma" in targets)
                else:
                    # Fallback to Desktop Window Check
                    self.is_active_context = self.context_manager.is_target_active(targets)

                if self.is_active_context != last_state:
                    self.log_debug(f"Context changed to {'ACTIVE' if self.is_active_context else 'INACTIVE'} (Web: {web_app}, Targets: {targets})")
                    last_state = self.is_active_context
            except Exception as e:
                print(f"Error in context thread: {e}")
            time.sleep(0.05) # Faster polling 

    def start(self):
        """Starts listening."""
        if self.running:
            return

        self.running = True
        
        # Start Web Listener
        self.web_listener.start()
        
        # Ensure we have initial hooks
        self.register_hotkeys()
        
        # Re-initialize threads here to allow restarts
        self._context_thread = threading.Thread(target=self._monitor_context, daemon=True)
        self._context_thread.start()
        
        # Worker thread (daemon) for processing zoom buffer
        threading.Thread(target=self._zoom_worker, daemon=True).start()

    def stop(self):
        """Stops listening."""
        self.running = False
        keyboard.unhook_all()
        if hasattr(self, '_mouse_hook'):
             self._mouse_hook.stop()
             del self._mouse_hook

    def _on_event(self, event):
        """
        Callback for keyboard events.
        """
        if not self.running:
            return
        
        # Logic moved to hotkeys, but if we need generic interception:
        pass
            
    def register_hotkeys(self):
        """
        Registers hotkeys based on the config manager's active profile mappings.
        Also sets up mouse hooks if needed.
        """
        mappings = self.config_manager.get_active_mappings()
        
        # Flag to verify if we need mouse hook
        need_mouse = False
        # print(f"DEBUG: Registering {len(mappings)} mappings...")
        for rule in mappings:
            src = rule['input'] # Using 'input' from new JSON schema
            
            # print(f"DEBUG: Processing rule '{src}'")
            if 'wheel' in src:
                need_mouse = True
                # print("DEBUG: Mouse rule detected.")
            else:
                 # Key mappings
                dst = rule['output']
                try:
                    keyboard.add_hotkey(src, self._handle_hotkey, args=[src, dst], suppress=True, trigger_on_release=False)
                except Exception as e:
                     print(f"Failed to register hotkey {src}: {e}")

        # print(f"DEBUG: Finished rules. Need mouse? {need_mouse}")
        if need_mouse and not hasattr(self, '_mouse_hook'):
            from core.mouse_hook import LowLevelMouseHook, WM_MOUSEWHEEL
            # print("DEBUG: Initializing Mouse Hook...")
            self._mouse_hook = LowLevelMouseHook(self._on_low_level_mouse)
            self._mouse_hook.start()
            print("Mouse hook started.")

    def _on_low_level_mouse(self, event_info):
        # Optimization: Local imports are slow. Moved key constants to top level or assumed.
        from core.mouse_hook import WM_MOUSEWHEEL, WM_MOUSEHWHEEL
        
        # FAST EXIT for common events (Moveers) to prevent freeze
        if event_info['msg'] != WM_MOUSEWHEEL and event_info['msg'] != WM_MOUSEHWHEEL:
             return True

        # Safety Wrap: If anything fails here, we MUST allow the event or mouse dies
        try:
            if not self.is_active_context:
                return True 
            
            # 1. Identify active wheel rule
            # WARNING: self.config_manager.get_active_mappings() must be fast (memory only)
            mappings = self.config_manager.get_active_mappings()
            
            # Optimization: Cache this rule? For now, list comp is okay if list is short.
            wheel_rule = next((r for r in mappings if 'wheel' in r['input']), None)
            
            if not wheel_rule:
                return True

            # Parse rule: e.g. "ctrl+wheel" -> "alt+wheel"
            trigger_mod = wheel_rule['input'].replace('+wheel', '').strip().lower()
            output_mod = wheel_rule['output'].replace('+wheel', '').strip().lower()
            
            # ZOOM HYBRID LOGIC (Restored Phase 1 Strategy)
            
            # 3. Standard Trigger Check
            import ctypes
            user32 = ctypes.windll.user32
            
            # Helper to check modifier state - STILL NEEDED to detect initial press
            def is_mod_pressed(mod_name):
                if mod_name == 'ctrl':
                     return (user32.GetAsyncKeyState(0x11) & 0x8000) != 0
                if mod_name == 'alt':
                     return (user32.GetAsyncKeyState(0x12) & 0x8000) != 0
                if mod_name == 'shift':
                     return (user32.GetAsyncKeyState(0x10) & 0x8000) != 0
                return False

            # Check both hardware AND our tracked state
            # We trust 'is_mod_pressed' (via API) for initial detection
            
            trigger_pressed = is_mod_pressed(trigger_mod)
            output_pressed = is_mod_pressed(output_mod)
            
            current_time = time.time()
            is_sticky = (current_time - self.last_ctrl_wheel_time) < 1.0 # Increased sticky for continuous

            # LOGIC UPDATE: Checking zoom_active ensures we don't drop the state if verified trigger is held
            if (trigger_pressed or is_sticky or self.zoom_active):
                self.last_ctrl_wheel_time = current_time
                
                if output_pressed:
                    # NATIVE SMOOTHNESS
                    # Worker is holding the key. Let the event pass to OS.
                    return True
                else:
                    # START NEW ZOOM SESSION
                    # Captures initial tokens to prevent leak
                    with self.zoom_lock:
                        self.zoom_buffer += event_info['delta']
                        self.zoom_active = True 
                        self.zoom_trigger_key = trigger_mod
                        self.zoom_output_key = output_mod
                    return False # Block
            
            return True # Allow everything else
            
        except Exception as e:
            print(f"CRITICAL ERROR IN MOUSE HOOK: {e}")
            return True # FAILSAVE: ALWAYS ALLOW IF ERROR

    def _zoom_worker(self):
        """
        Runs continuously. Checks for active zoom state.
        When active:
        1. Switches Modifiers (Release Ctrl, Press Alt).
        2. Drains buffer to scroll.
        3. Waits for timeout or physical release.
        4. Restores Modifiers.
        """
        import mouse
        import ctypes
        user32 = ctypes.windll.user32
        
        while self.running:
            # Sleep if no work
            if not self.zoom_active:
                time.sleep(0.01)
                continue
                
            # ENTER ZOOM MODE
            # buffer has data or we are in grace period.
            
            # 1. Release Trigger / Press Output
            trigger = getattr(self, 'zoom_trigger_key', 'ctrl')
            output = getattr(self, 'zoom_output_key', 'alt')
            
            keyboard.release(trigger)
            time.sleep(0.02)
            keyboard.press(output)
            time.sleep(0.02)
            
            # Helper for continuous check
            trigger_vk = 0x11
            if trigger == 'alt': trigger_vk = 0x12
            if trigger == 'shift': trigger_vk = 0x10

            # Loop while we have work OR we are holding Input (Continuous Mode)
            while self.running:
                # Check buffer
                delta_to_apply = 0
                with self.zoom_lock:
                    delta_to_apply = self.zoom_buffer
                    self.zoom_buffer = 0
                
                # Apply Scroll
                if delta_to_apply != 0:
                    steps = delta_to_apply / 120.0
                    mouse.wheel(steps) 
                
                # CHECK CONTINUOUS MODE:
                # We rely on specific activity timeout (Grace Period).
                # If the user pauses for > 1.0s, we assume they let go.
                if delta_to_apply == 0 and (time.time() - self.last_ctrl_wheel_time) > 1.0:
                    self.zoom_active = False
                    break
                
                time.sleep(0.005) # Idle wait
            
            # EXIT ZOOM MODE
            keyboard.release(output)
            time.sleep(0.02)
            
            # Smart Restore Trigger
            # If user is still physically holding it, press it back
            # Smart Restore Trigger
            # Check physical state to see if we should press it back
            # Since we removed hooks, we use GetAsyncKeyState
            if (user32.GetAsyncKeyState(trigger_vk) & 0x8000) != 0:
                keyboard.press(trigger)
            else:
                keyboard.release(trigger)
            
            # Reset buffer to be safe
            with self.zoom_lock:
                self.zoom_buffer = 0

    def _handle_hotkey(self, src, dst):
        if self.is_active_context:
            self.injection_module.inject(dst)
        else:
            keyboard.send(src)
