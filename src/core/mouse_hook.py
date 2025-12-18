import ctypes
import ctypes.wintypes
from ctypes.wintypes import HINSTANCE, HHOOK, LPARAM, WPARAM, MSG
import atexit
import threading

# Windows Constants
WH_MOUSE_LL = 14
WM_MOUSEWHEEL = 0x020A
WM_MOUSEHWHEEL = 0x020E

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", ctypes.wintypes.POINT),
        ("mouseData", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)) # ULONG_PTR, usually pointer sized
    ]

# Callback signature: LRESULT (int, WPARAM, LPARAM)
# Windows callbacks use stdcall (WINFUNCTYPE)
CMPFUNC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, WPARAM, ctypes.POINTER(MSLLHOOKSTRUCT))

class LowLevelMouseHook:
    def __init__(self, callback):
        """
        callback: function(event_type, event_data) -> bool
        If callback returns True, the event is ALLOWED.
        If callback returns False, the event is BLOCKED.
        """
        self.callback = callback
        self.hook_id = None
        self.thread_id = None
        self.thread = None
        self.running = False
        self._hook_proc = CMPFUNC(self._hook_callback)

    def _hook_callback(self, nCode, wParam, lParam):
        try:
            if nCode >= 0:
                # Check if we should block
                # wParam is likely WM_MOUSEWHEEL
                struct = lParam.contents
                
                # Simple wrapper data
                event_info = {
                    'msg': wParam,
                    'delta': (ctypes.c_short(struct.mouseData >> 16).value),
                    'x': struct.pt.x,
                    'y': struct.pt.y
                }
                
                should_allow = self.callback(event_info)
                if not should_allow:
                     # To block, return non-zero. 
                     return 1 
        except Exception as e:
            print(f"Hook Callback Error: {e}")

        return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._msg_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0) # WM_QUIT
        self.thread.join(timeout=1)

    def _msg_loop(self):
        self.thread_id = kernel32.GetCurrentThreadId()
        # For WH_MOUSE_LL, hMod is usually NULL (0) if we aren't injecting a DLL? 
        # Actually docs say: "If the hook procedure is not in a DLL... hMod must be NULL." (Wait, no, LL hooks don't inject).
        # Common fix for Error 126 in Python: Pass 0.
        self.hook_id = user32.SetWindowsHookExA(WH_MOUSE_LL, self._hook_proc, 0, 0)
        
        if not self.hook_id:
            error = ctypes.GetLastError()
            print(f"CRITICAL: Failed to install mouse hook. Error Code: {error}")
            return
            
        print(f"DEBUG: Mouse Hook installed. ID={self.hook_id}")
        
        msg = MSG()
        
        msg = MSG()
        # Message pump
        # print("DEBUG: Mouse Hook Message Loop Started")
        try:
            while self.running:
                bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if bRet == 0 or bRet == -1:
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as e:
            print(f"CRITICAL: Mouse hook died: {e}")
        finally:
            # print("DEBUG: Mouse Hook Message Loop Ended")
            pass

        user32.UnhookWindowsHookEx(self.hook_id)
        self.hook_id = None
