"""
Yjs/CRDT WebSocket Provider for Noteworthy GUI

Uses pycrdt-websocket for collaborative editing with CRDT-based conflict resolution.
This runs alongside the existing document hub for presence/cursor sharing.

Updated for pycrdt-websocket 0.16+ API.
"""
import asyncio
from pathlib import Path
from typing import Dict, Optional, Callable, Awaitable, Any
from pycrdt import Doc, Text
from pycrdt.websocket import WebsocketServer, ASGIServer
from pycrdt.websocket.yroom import YRoom

from ..config import BASE_DIR


class NoteworthyRoom(YRoom):
    """
    Custom room that syncs with disk.
    Each file gets its own room identified by relative file path.
    """
    
    def __init__(self, room_name: str, *args, **kwargs):
        super().__init__(ready=True, *args, **kwargs)  # Start ready since we load sync
        self.room_name = room_name
        self._file_path = BASE_DIR / room_name
        self._initialized = False
        
    async def initialize(self):
        """Load initial content from disk into the CRDT document."""
        if self._initialized:
            return
        
        if self._file_path.exists():
            try:
                content = self._file_path.read_text(encoding='utf-8')
                # Get the Text type from the document
                text = self.ydoc.get("content", type=Text)
                # Only set if empty (first load)
                if len(text) == 0:
                    text += content
                print(f"[YjsRoom] Loaded {self.room_name}: {len(content)} chars")
            except Exception as e:
                print(f"[YjsRoom] Error loading {self.room_name}: {e}")
        else:
            print(f"[YjsRoom] File not found, starting empty: {self.room_name}")
        
        # Set up change callback for persistence
        text = self.ydoc.get("content", type=Text)
        text.observe(self._on_change)
        
        self._initialized = True
    
    def _on_change(self, event):
        """Persist changes to disk immediately (synchronous for macOS compatibility)."""
        print(f"[YjsRoom] Change detected in {self.room_name}")
        text = self.ydoc.get("content", type=Text)
        content = str(text)
        
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text(content, encoding='utf-8')
            print(f"[YjsRoom] Saved {self.room_name} ({len(content)} chars)")
        except Exception as e:
            print(f"[YjsRoom] Error saving {self.room_name}: {e}")


class YjsProvider:
    """
    Manages Yjs/CRDT document synchronization.
    
    Each document (file) gets its own "room" for collaborative editing.
    """
    
    def __init__(self):
        self.rooms: Dict[str, NoteworthyRoom] = {}
        self.server: Optional[WebsocketServer] = None
        self._callbacks = []
    
    def get_room(self, file_path: str) -> NoteworthyRoom:
        """Get or create a room for a file."""
        if file_path not in self.rooms:
            self.rooms[file_path] = NoteworthyRoom(room_name=file_path)
        return self.rooms[file_path]
    
    def add_change_callback(self, callback):
        """Register callback for content changes (for diagnostics/preview triggers)."""
        self._callbacks.append(callback)
    
    async def notify_change(self, file_path: str, content: str):
        """Notify all callbacks of a content change."""
        for cb in self._callbacks:
            try:
                await cb(file_path, content)
            except Exception as e:
                print(f"[YjsProvider] Callback error: {e}")


# Global instance
yjs_provider = YjsProvider()


def get_yjs_asgi_app():
    """
    Create the ASGI application for Yjs WebSocket handling.
    
    This is mounted at /yjs in the main FastAPI app.
    
    pycrdt-websocket 0.16+ uses a different pattern:
    - WebsocketServer is created first
    - ASGIServer wraps it
    - Room management is handled via on_connect callback
    """
    
    # Create the websocket server
    server = WebsocketServer(rooms_ready=True, auto_clean_rooms=False)
    yjs_provider.server = server
    
    async def on_connect(scope: dict, state: dict) -> bool:
        """
        Called when a client connects.
        The room name comes from the websocket path.
        """
        # Extract room name from path (e.g., /yjs/content/1/1.typ -> content/1/1.typ)
        path = scope.get("path", "")
        if path.startswith("/yjs/"):
            room_name = path[5:]  # Remove /yjs/ prefix
        elif path.startswith("/"):
            room_name = path[1:]
        else:
            room_name = path
        
        # Get or create the room
        room = yjs_provider.get_room(room_name)
        
        # Initialize from disk if needed
        await room.initialize()
        
        # Store room in state for the connection
        state["room"] = room
        
        return True  # Accept connection
    
    return ASGIServer(server, on_connect=on_connect)
