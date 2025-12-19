import keyboard
import threading
import time

class InputObserver:
    def __init__(self, context_manager, config_manager, injection_module):
        self.context_manager = context_manager
        self.config_manager = config_manager
        self.injection_module = injection_module
        self.running = False
        self._hook = None
        
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

    def _monitor_context(self):
        """Polls context every 0.1s to update status without blocking hooks."""
        last_state = None
        while True:
            try:
                targets = self.config_manager.get_active_profile_targets()
                self.is_active_context = self.context_manager.is_target_active(targets)
                if self.is_active_context != last_state:
                    self.log_debug(f"Context changed to {'ACTIVE' if self.is_active_context else 'INACTIVE'} (Targets: {targets})")
                    last_state = self.is_active_context
            except Exception as e:
                print(f"Error in context thread: {e}")
            time.sleep(0.05) # Faster polling

    def start(self):
        """Starts listening."""
        if self.running:
            return

        self.running = True
        
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
        # logging raw connection check
        if not hasattr(self, 'debug_event_count'):
            self.debug_event_count = 0
            
        if self.debug_event_count < 50:
             self.log_debug(f"RAW MOUSE EVENT msg={hex(event_info['msg'])}")
             self.debug_event_count += 1
             
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
            
            import ctypes
            user32 = ctypes.windll.user32
            
            # Helper to check modifier state
            def is_mod_pressed(mod_name):
                if mod_name == 'ctrl':
                     return (user32.GetAsyncKeyState(0x11) & 0x8000) != 0
                if mod_name == 'alt':
                     return (user32.GetAsyncKeyState(0x12) & 0x8000) != 0
                if mod_name == 'shift':
                     return (user32.GetAsyncKeyState(0x10) & 0x8000) != 0
                return False

            trigger_pressed = is_mod_pressed(trigger_mod)
            output_pressed = is_mod_pressed(output_mod)
            
            # self.log_debug(f"Wheel Event: Trigger({trigger_mod})={trigger_pressed}, Output({output_mod})={output_pressed}")

            current_time = time.time()
            is_sticky = (current_time - self.last_ctrl_wheel_time) < 0.5
            
            # ZOOM LOGIC GENERIC
            if (trigger_pressed or is_sticky):
                self.log_debug(f"Zoom Triggered! Sticky={is_sticky}")
                self.last_ctrl_wheel_time = current_time
                
                if not output_pressed:
                    # START ZOOM (Block native, inject output)
                    with self.zoom_lock:
                        self.zoom_buffer += event_info['delta']
                        self.zoom_active = True 
                        self.zoom_trigger_key = trigger_mod
                        self.zoom_output_key = output_mod
                    return False # Block
                else:
                    return True # Allow
            
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
                    # Don't sleep too long to support fast scroll
                    time.sleep(0.01) 
                else:
                    # No new scroll data.
                    # Should we exit? Only if timeout expired AND buffer empty.
                    
                    if (time.time() - self.last_ctrl_wheel_time) > 0.5:
                        # User stopped scrolling or released key for > 500ms
                        self.zoom_active = False
                        break
                    time.sleep(0.01)
            
            # EXIT ZOOM MODE
            keyboard.release(output)
            time.sleep(0.02)
            
            # Smart Restore Trigger
            # Check physical state of trigger key
            # Mapping simplified for common modifiers
            trigger_vk = 0x11 # Default Ctrl
            if trigger == 'alt': trigger_vk = 0x12
            if trigger == 'shift': trigger_vk = 0x10
            
            if (user32.GetAsyncKeyState(trigger_vk) & 0x8000) != 0:
                keyboard.press(trigger)
            else:
                keyboard.release(trigger)
            
            # Reset buffer to be safe
            with self.zoom_lock:
                self.zoom_buffer = 0

    def _handle_hotkey(self, src, dst):
        print(f"DEBUG: Hotkey detected '{src}'")
        if self.is_active_context:
            print(f"DEBUG: Translating {src} -> {dst}")
            self.injection_module.inject(dst)
        else:
            # print(f"DEBUG: Context verification failed for hotkey '{src}' (is_active={self.is_active_context})")
            keyboard.send(src)
