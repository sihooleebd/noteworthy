"""
Yjs/CRDT WebSocket Provider for Noteworthy GUI

Uses pycrdt-websocket for collaborative editing with CRDT-based conflict resolution.
This runs alongside the existing document hub for presence/cursor sharing.
"""
import asyncio
from pathlib import Path
from typing import Dict, Optional
from pycrdt import Doc, Text
from pycrdt_websocket import WebsocketServer
from pycrdt_websocket.yroom import YRoom

from ..config import BASE_DIR


class NoteworthyRoom(YRoom):
    """
    Custom room that syncs with disk.
    Each file gets its own room identified by relative file path.
    """
    
    def __init__(self, room_name: str, *args, **kwargs):
        super().__init__(ready=False, *args, **kwargs)
        self.room_name = room_name
        self._file_path = BASE_DIR / room_name
        
    async def _init_from_disk(self):
        """Load initial content from disk into the CRDT document."""
        if self._file_path.exists():
            try:
                content = self._file_path.read_text(encoding='utf-8')
                # Get the Text type from the document
                text = self.ydoc.get("content", type=Text)
                # Only set if empty (first load)
                if len(text) == 0:
                    text += content
            except Exception as e:
                print(f"[YjsRoom] Error loading {self.room_name}: {e}")
        
        # Mark room as ready
        self._ready_event.set()
    
    async def started(self):
        """Called when room starts."""
        await super().started()
        await self._init_from_disk()
        
        # Set up change callback
        text = self.ydoc.get("content", type=Text)
        text.observe(self._on_change)
    
    def _on_change(self, event):
        """Persist changes to disk when document changes."""
        # Get current content
        text = self.ydoc.get("content", type=Text)
        content = str(text)
        
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text(content, encoding='utf-8')
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
    """
    from pycrdt_websocket import ASGIServer
    
    async def room_getter(name: str, create: bool = True):
        """Called by pycrdt-websocket to get/create rooms."""
        return yjs_provider.get_room(name)
    
    server = WebsocketServer(get_room=room_getter, auto_clean_rooms=False)
    return ASGIServer(server)
