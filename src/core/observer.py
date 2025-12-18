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

    def _monitor_context(self):
        """Polls context every 0.1s to update status without blocking hooks."""
        last_state = None
        while True:
            try:
                self.is_photoshop_active = self.context_manager.is_target_active()
                if self.is_photoshop_active != last_state:
                # print(f"DEBUG: Context changed to {'PHOTOSHOP' if self.is_photoshop_active else 'OTHER'}")
                    print(f"DEBUG: Context changed to {'PHOTOSHOP' if self.is_photoshop_active else 'OTHER'}", flush=True)
                    last_state = self.is_photoshop_active
            except Exception as e:
                print(f"Error in context thread: {e}")
            time.sleep(0.05) # Faster polling

    def start(self):
        """Starts listening."""
        self.running = True
        self._context_thread.start()
        
        # Hook all events. 
        # self._hook = keyboard.hook(self._on_event, suppress=True)

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
        """
        Callback from LowLevelMouseHook.
        Returns True to Allow, False to Block (Suppress).
        """
        from core.mouse_hook import WM_MOUSEWHEEL, WM_MOUSEHWHEEL
        
        # print(f"DEBUG: Mouse Msg={event_info['msg']}")
        
        if event_info['msg'] == WM_MOUSEWHEEL or event_info['msg'] == WM_MOUSEHWHEEL:
            # Context Check (Cached)
            if not self.is_photoshop_active:
                # print("DEBUG: Mouse event ignored (Context not active)")
                return True # Allow
            
            # Check Modifiers using GetAsyncKeyState
            import ctypes
            user32 = ctypes.windll.user32
            
            # Check high-order bit for key down
            # VK_CONTROL=0x11, VK_LCONTROL=0xA2, VK_RCONTROL=0xA3
            ctrl_down = (user32.GetAsyncKeyState(0x11) & 0x8000) != 0
            l_ctrl = (user32.GetAsyncKeyState(0xA2) & 0x8000) != 0
            r_ctrl = (user32.GetAsyncKeyState(0xA3) & 0x8000) != 0
            
            # kb_ctrl = keyboard.is_pressed('ctrl') # Removing this as it causes false positives
            
            alt_down = (user32.GetAsyncKeyState(0x12) & 0x8000) != 0
            
            print(f"DEBUG: Wheel. Ctrl={ctrl_down} (L={l_ctrl}, R={r_ctrl}). Alt={alt_down}")
            
            # Use ANY valid detection
            is_ctrl = ctrl_down or l_ctrl or r_ctrl
            
            if is_ctrl and not alt_down:
                print("DEBUG: Blocking Ctrl+Wheel -> Injecting Zoom")
                threading.Thread(target=self._inject_zoom, args=(event_info['delta'],)).start()
                return False # Block

        return True # Allow everything else

    def _inject_zoom(self, delta):
        import mouse
        import ctypes
        user32 = ctypes.windll.user32
        
        # Back to basics: Use keyboard library which handles the virtual stack better
        # 1. Release Ctrl
        keyboard.release('ctrl')
        time.sleep(0.02)
        
        # 2. Press Alt
        keyboard.press('alt')
        time.sleep(0.02)
        
        # 3. Scroll
        steps = delta / 120.0
        mouse.wheel(steps)
        time.sleep(0.02)
        
        # 4. Release Alt
        keyboard.release('alt')
        time.sleep(0.02)
        
        # 5. Smart Restore Ctrl
        # Check Physical State (High bit)
        if (user32.GetAsyncKeyState(0x11) & 0x8000) != 0:
            # print("DEBUG: Restoring Ctrl")
            keyboard.press('ctrl')
        else:
             keyboard.release('ctrl') # Ensure clean state

    def _handle_hotkey(self, src, dst):
        print(f"DEBUG: Hotkey detected '{src}'")
        if self.is_photoshop_active:
            print(f"DEBUG: Translating {src} -> {dst}")
            self.injection_module.inject(dst)
        else:
            print(f"DEBUG: Context verification failed for hotkey '{src}' (is_active={self.is_photoshop_active})")
            keyboard.send(src)
