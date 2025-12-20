import keyboard
import threading
import time
from core.web_listener import WebContextListener
from core.action_mapper import ActionMapper

class InputObserver:
    def __init__(self, context_manager, config_manager, injection_module):
        self.context_manager = context_manager
        self.config_manager = config_manager
        self.injection_module = injection_module
        self.action_mapper = ActionMapper(config_manager)
        
        self.running = False
        self._hook = None
        
        # Web Context Listener
        self.web_listener = WebContextListener()

        # Context Caching
        self.is_active_context = False
        self._context_thread = None
        self.active_app_name = None
        
        # Semantic Mapping State
        self.mapping_lookup = {} # trigger(str) -> output(str)
        self.active_context_lock = threading.Lock()
        
        # Debounce State
        self.last_trigger_times = {} # key -> timestamp
        self.debounce_interval = 0.25 # seconds

        # State tracking for Zoom continuity
        self.last_ctrl_wheel_time = 0
        self.zoom_lock = threading.Lock()
        self.zoom_buffer = 0
        self.zoom_active = False
        self.trigger_held = False # Track physical state
        
    def log_debug(self, msg):
        import time
        try:
            with open("babel_debug.log", "a") as f:
                f.write(f"{time.ctime()} [OBSERVER]: {msg}\n")
        except:
            pass

    def _monitor_context(self):
        """Polls context every 0.1s to update status without blocking hooks."""
        last_state = None
        last_app = None
        
        while self.running:
            try:
                # Semantic Targets are derived from system definitions (photoshop, figma, etc.)
                targets = self.config_manager.get_semantic_targets()
                
                # Check Web Context First
                web_app = self.web_listener.get_active_web_app()
                detected_app = None

                active = False
                if web_app:
                    # Check if the detected web app matches any of our targets
                    active = any(t.lower() in web_app.lower() for t in targets) or (web_app == "figma" and "figma" in targets)
                    if active:
                        detected_app = next((t for t in targets if t.lower() in web_app.lower()), web_app)
                else:
                    # Fallback to Desktop Window Check
                    active = self.context_manager.is_target_active(targets)
                    # We need to know WHICH app to ask ActionMapper.
                    # ContextManager needs to return the app name, but currently returns Bool.
                    # For now, we trust ActionMapper to handle generic "photoshop" if Active is True and process is photoshop.
                    # TODO: Update ContextManager to return the active app name.
                    # HACK for now: iterate targets and check.
                    if active:
                        # Find which one
                        for t in targets:
                            if self.context_manager.is_target_active([t]):
                                detected_app = t
                                break
                
                self.is_active_context = active
                self.active_app_name = detected_app

                # Update Mappings if Context Changed
                if active and detected_app and detected_app != last_app:
                     self._update_mappings_for_context(detected_app)
                     last_app = detected_app

                if self.is_active_context != last_state:
                    self.log_debug(f"Context changed to {'ACTIVE' if self.is_active_context else 'INACTIVE'} (App: {detected_app})")
                    last_state = self.is_active_context
                    
            except Exception as e:
                print(f"Error in context thread: {e}")
            time.sleep(0.05) # Faster polling 

    def _update_mappings_for_context(self, app_name):
        """
        Ask ActionMapper for new mappings and update lookup table.
        """
        raw_mappings = self.action_mapper.get_mappings_for_context(app_name)
        new_lookup = {}
        for rule in raw_mappings:
            # {input, output, type}
            trigger = rule['input'].lower()
            output = rule['output']
            new_lookup[trigger] = output
            
        with self.active_context_lock:
            self.mapping_lookup = new_lookup
        
        # print(f"DEBUG: Updated mappings for {app_name}: {new_lookup}")

    def start(self):
        """Starts listening."""
        if self.running:
            return

        self.running = True
        
        # Start Web Listener
        self.web_listener.start()
        
        # Register Hooks (One-time setup for all configured triggers)
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

    def register_hotkeys(self):
        """
        Registers hotkeys for ALL triggers defined in User Profile.
        The Action depends on the active context at runtime.
        """
        triggers = self.action_mapper.get_all_configured_triggers()
        self.registered_triggers = set(triggers.keys()) # Keep track of what we hooked
        
        need_mouse = False
        for trigger_key, meta in triggers.items():
            if 'wheel' in trigger_key:
                need_mouse = True
            else:
                self._register_single_hotkey(trigger_key)

        if need_mouse and not hasattr(self, '_mouse_hook'):
            from core.mouse_hook import LowLevelMouseHook
            self._mouse_hook = LowLevelMouseHook(self._on_low_level_mouse)
            self._mouse_hook.start()
            print("Mouse hook started.")

    def _register_single_hotkey(self, trigger_key):
        try:
             # Look up args=... carefully
             keyboard.add_hotkey(trigger_key, self._handle_dynamic_hotkey, args=[trigger_key], suppress=True, trigger_on_release=False)
        except Exception as e:
             print(f"Failed to register hotkey {trigger_key}: {e}")

    def _handle_dynamic_hotkey(self, trigger):
        """
        Runtime handler for keyboard hotkeys.
        """
        current_time = time.time()
        last_time = self.last_trigger_times.get(trigger, 0)
        
        if (current_time - last_time) < self.debounce_interval:
             # Ignore (Machine Gun Prevention)
             return
             
        self.last_trigger_times[trigger] = current_time

        # 1. Check if we are in an active context
        # If not active, we still need to pass it through if we suppressed it!
        if not self.is_active_context:
            self._safe_inject(trigger)
            return

        # 2. Look up the output for this trigger in the current context
        output = None
        with self.active_context_lock:
            output = self.mapping_lookup.get(trigger)
            
        target = output if output else trigger
        
        # 3. Inject
        self._safe_inject(target)

    def _safe_inject(self, target):
        """
        Injects the target command. 
        If target is one of our hooked triggers, we MUST unhook it temporarily 
        to avoid infinite loops (Hook -> Inject -> Hook).
        """
        is_hooked = target in self.registered_triggers
        
        if is_hooked:
            try:
                keyboard.remove_hotkey(target)
            except:
                pass
        
        # Inject
        try:
            self.injection_module.inject(target)
        except Exception as e:
            print(f"Injection error: {e}")
            
        # Re-hook if needed
        if is_hooked:
            # Short sleep to ensure OS processed the injection? 
            # inject() already has sleeps, so usually fine.
            self._register_single_hotkey(target)

    def _on_low_level_mouse(self, event_info):
        from core.mouse_hook import WM_MOUSEWHEEL, WM_MOUSEHWHEEL
        
        if event_info['msg'] != WM_MOUSEWHEEL and event_info['msg'] != WM_MOUSEHWHEEL:
             return True

        try:
            if not self.is_active_context:
                return True 
            
            # Identify active wheel rule from lookup
            wheel_rule_trigger = None
            wheel_rule_output = None
            
            with self.active_context_lock:
                # Find any trigger in lookup that contains 'wheel'
                # Optimization: Could cache the wheel rule separately
                for trig, out in self.mapping_lookup.items():
                    if 'wheel' in trig:
                        wheel_rule_trigger = trig
                        wheel_rule_output = out
                        break
            
            if not wheel_rule_trigger:
                return True

            # Parse rule: e.g. "ctrl+wheel" -> "alt+wheel"
            trigger_mod = wheel_rule_trigger.replace('+wheel', '').strip().lower()
            output_mod = wheel_rule_output.replace('+wheel', '').strip().lower()
            
            # ZOOM HYBRID LOGIC
            import ctypes
            user32 = ctypes.windll.user32
            
            def is_mod_pressed(mod_name):
                if mod_name == 'ctrl': return (user32.GetAsyncKeyState(0x11) & 0x8000) != 0
                if mod_name == 'alt': return (user32.GetAsyncKeyState(0x12) & 0x8000) != 0
                if mod_name == 'shift': return (user32.GetAsyncKeyState(0x10) & 0x8000) != 0
                return False

            trigger_pressed = is_mod_pressed(trigger_mod)
            output_pressed = is_mod_pressed(output_mod)
            
            current_time = time.time()
            is_sticky = (current_time - self.last_ctrl_wheel_time) < 1.0 

            if (trigger_pressed or is_sticky or self.zoom_active):
                self.last_ctrl_wheel_time = current_time
                
                if output_pressed:
                    return True
                else:
                    with self.zoom_lock:
                        self.zoom_buffer += event_info['delta']
                        self.zoom_active = True 
                        self.zoom_trigger_key = trigger_mod
                        self.zoom_output_key = output_mod
                    return False 
            
            return True 
            
        except Exception as e:
            print(f"CRITICAL ERROR IN MOUSE HOOK: {e}")
            return True

    def _zoom_worker(self):
        """
        Runs continuously. Checks for active zoom state.
        """
        import mouse
        import ctypes
        user32 = ctypes.windll.user32
        
        while self.running:
            if not self.zoom_active:
                time.sleep(0.01)
                continue
                
            trigger = getattr(self, 'zoom_trigger_key', 'ctrl')
            output = getattr(self, 'zoom_output_key', 'alt')
            
            keyboard.release(trigger)
            time.sleep(0.02)
            keyboard.press(output)
            time.sleep(0.02)
            
            trigger_vk = 0x11
            if trigger == 'alt': trigger_vk = 0x12
            if trigger == 'shift': trigger_vk = 0x10

            while self.running:
                delta_to_apply = 0
                with self.zoom_lock:
                    delta_to_apply = self.zoom_buffer
                    self.zoom_buffer = 0
                
                if delta_to_apply != 0:
                    steps = delta_to_apply / 120.0
                    mouse.wheel(steps) 
                
                if delta_to_apply == 0 and (time.time() - self.last_ctrl_wheel_time) > 1.0:
                    self.zoom_active = False
                    break
                
                time.sleep(0.005) 
            
            keyboard.release(output)
            time.sleep(0.02)
            
            if (user32.GetAsyncKeyState(trigger_vk) & 0x8000) != 0:
                keyboard.press(trigger)
            else:
                keyboard.release(trigger)
            
            with self.zoom_lock:
                self.zoom_buffer = 0
