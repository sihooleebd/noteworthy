"""
Noteworthy GUI - Web-based interface for Noteworthy
Replaces the TUI with a modern web UI
"""
import webbrowser
import threading
import time
from pathlib import Path

def run_gui(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True):
    """Launch the Noteworthy GUI server."""
    try:
        import uvicorn
    except ImportError:
        print("Error: GUI requires uvicorn. Install with: pip install uvicorn fastapi")
        return
    
    print(f"Starting Noteworthy GUI at http://{host}:{port}")
    
    if open_browser:
        def open_delayed():
            time.sleep(1)
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=open_delayed, daemon=True).start()
    
    from .server import app
    uvicorn.run(app, host=host, port=port, log_level="warning")
