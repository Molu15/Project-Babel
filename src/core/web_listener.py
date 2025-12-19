import asyncio
import websockets
import json
import threading
import time

class WebContextListener:
    def __init__(self, port=6789):
        self.port = port
        self.current_web_app = None
        self.last_update_time = 0
        self.running = False
        self._loop = None
        self._thread = None
        
    def start(self):
        """Starts the WebSocket server in a daemon thread."""
        if self.running:
            return
            
        self.running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        print(f"WebContextListener started on port {self.port}")

    def stop(self):
        """Stops the server."""
        self.running = False
        # In a real asyncio app we'd signal the loop to stop, 
        # but for daemon threads in this simple script, letting it die with the app is often acceptable.
        # Alternatively, we could run a coroutine to close the server.
        pass

    def get_active_web_app(self):
        """
        Returns the active web app (e.g., 'figma', 'photoshop') if valid.
        """
        # Removed timeout check because user might stay on page > 10s without updates.
        # State is managed by connection status and explicit messages.
        return self.current_web_app

    def _run_server(self):
        """Internal method to run the asyncio loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        start_server = websockets.serve(self._handler, "127.0.0.1", self.port)
        
        try:
            self._loop.run_until_complete(start_server)
            self._loop.run_forever()
        except Exception as e:
            print(f"WebContextListener Error: {e}")

    async def _handler(self, websocket):
        """Handles incoming WebSocket connections."""
        try:
            async for message in websocket:
                data = json.loads(message)
                
                if data.get("event") == "context_change":
                    app = data.get("app")
                    if app == "null":
                        self.current_web_app = None
                    else:
                        self.current_web_app = app
                    
                    self.last_update_time = time.time()
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"Web Handler Error: {e}")
        finally:
            # Reset state when connection drops (Extension unloaded/Browser closed)
            self.current_web_app = None
