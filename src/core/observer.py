import keyboard
import threading
import time

class InputObserver:
    def __init__(self, context_manager, translation_engine, injection_module):
        self.context_manager = context_manager
        self.translation_engine = translation_engine
        self.injection_module = injection_module
        self.running = False
        self._hook = None
        
        # Context Caching
        self.is_photoshop_active = False
        self._context_thread = threading.Thread(target=self._monitor_context, daemon=True)
        
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
                self.is_photoshop_active = self.context_manager.is_target_active()
                if self.is_photoshop_active != last_state:
                    print(f"DEBUG: Context changed to {'PHOTOSHOP' if self.is_photoshop_active else 'OTHER'}", flush=True)
                    last_state = self.is_photoshop_active
            except Exception as e:
                print(f"Error in context thread: {e}")
            time.sleep(0.05) # Faster polling

    def start(self):
        """Starts listening."""
        self.running = True
        self._context_thread.start()
        # Worker thread (daemon) for processing zoom buffer
        threading.Thread(target=self._zoom_worker, daemon=True).start()

    def stop(self):
        """Stops listening."""
        self.running = False
        keyboard.unhook_all()

    def _on_event(self, event):
        """
        Callback for keyboard events.
        """
        # print("Event detected")
        if not self.running:
            return
        
        should_translate = False
        target_output = None
        
        if event.event_type == 'down':
             if self.is_photoshop_active:
                 target_output = self.translation_engine.translate(event)
                 if target_output:
                     should_translate = True
        
        if should_translate:
            # We actively matched a rule in the correct context.
            print("Event should be translated")
            print(f"Translating {event.name} -> {target_output}")
            self.injection_module.inject(target_output)
        else:
            # Pass through.
            pass
            
    def register_hotkeys(self):
        """
        Registers hotkeys based on the translation engine's loaded rules.
        Also sets up mouse hooks if needed.
        """
        mappings = self.translation_engine.mappings
        
        # Flag to verify if we need mouse hook
        need_mouse = False
        # print(f"DEBUG: Registering {len(mappings)} mappings...")
        for rule in mappings:
            src = rule['original']
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
        from core.mouse_hook import WM_MOUSEWHEEL, WM_MOUSEHWHEEL
        # print(f"DEBUG: Mouse Msg={event_info['msg']}")
        
        if event_info['msg'] == WM_MOUSEWHEEL or event_info['msg'] == WM_MOUSEHWHEEL:
            # Debugging Bluetooth Mouse
            print(f"DEBUG: Mouse Event {hex(event_info['msg'])} detected. Active={self.is_photoshop_active}", flush=True)

            if not self.is_photoshop_active:
                return True 
            
            import ctypes
            user32 = ctypes.windll.user32
            
            # Check Modifiers
            ctrl_down = (user32.GetAsyncKeyState(0x11) & 0x8000) != 0
            l_ctrl = (user32.GetAsyncKeyState(0xA2) & 0x8000) != 0
            r_ctrl = (user32.GetAsyncKeyState(0xA3) & 0x8000) != 0
            alt_down = (user32.GetAsyncKeyState(0x12) & 0x8000) != 0
            
            # Sticky/Physical Check
            # Using multiple methods to detect Ctrl ensures we catch it even if one method fails (common with Bluetooth devices)
            kb_ctrl = keyboard.is_pressed('ctrl')
            physical_ctrl = ctrl_down or l_ctrl or r_ctrl or kb_ctrl
            
            current_time = time.time()
            
            # Grace period logic
            is_sticky = (current_time - self.last_ctrl_wheel_time) < 0.5
            
            # Logic:
            # 1. If Ctrl is pressed (or Sticky), we want to ZOOM.
            # 2. If Alt is NOT down, it means we haven't switched yet. BLOCK -> Buffer -> Worker Switches.
            # 3. If Alt IS down, it means Worker is active. ALLOW -> Native Zoom (Smoother).
            
            if (physical_ctrl or is_sticky):
                # Keep mode alive!
                self.last_ctrl_wheel_time = current_time
                
                if not alt_down:
                    # Initial State: Block and start Worker
                    # print(f"DEBUG: START ZOOM (Delta={event_info['delta']})", flush=True)
                    with self.zoom_lock:
                        self.zoom_buffer += event_info['delta']
                        self.zoom_active = True 
                    return False # Block
                else:
                    # Persistent State: Worker is holding Alt. Let event pass for native smoothness.
                    # print(f"DEBUG: NATIVE ZOOM (Delta={event_info['delta']})", flush=True)
                    return True # Allow
            
            # Default: Not Zooming
            # print(f"DEBUG: PASS (Delta={event_info['delta']})", flush=True)

        return True # Allow everything else

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
            
            # 1. Release Ctrl / Press Alt
            keyboard.release('ctrl')
            time.sleep(0.02)
            keyboard.press('alt')
            time.sleep(0.02)
            
            # Loop while we have work OR we are holding Ctrl (Continuous Mode)
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
                    # Verify physical/sticky state again to exit mode if user released Ctrl
                    # But we suppressed Ctrl, so we rely on Cached Stickiness?
                    # Actually, GetAsyncKeyState might return 0 if we suppressed it?
                    # No, GetAsyncKeyState checks physical hardware state too (usually).
                    # But to be safe, we check our stickiness.
                    
                    if (time.time() - self.last_ctrl_wheel_time) > 0.5:
                        # User stopped scrolling or released key for > 500ms
                        self.zoom_active = False
                        break
                    time.sleep(0.01)
            
            # EXIT ZOOM MODE
            keyboard.release('alt')
            time.sleep(0.02)
            
            # Smart Restore Ctrl
            if (user32.GetAsyncKeyState(0x11) & 0x8000) != 0:
                keyboard.press('ctrl')
            else:
                keyboard.release('ctrl')
            
            # Reset buffer to be safe
            with self.zoom_lock:
                self.zoom_buffer = 0

    def _handle_hotkey(self, src, dst):
        print(f"DEBUG: Hotkey detected '{src}'")
        if self.is_photoshop_active:
            print(f"DEBUG: Translating {src} -> {dst}")
            self.injection_module.inject(dst)
        else:
            print(f"DEBUG: Context verification failed for hotkey '{src}' (is_active={self.is_photoshop_active})")
            keyboard.send(src)
