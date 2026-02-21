"""
Yjs/CRDT WebSocket Provider for Noteworthy GUI

Uses pycrdt-websocket for collaborative editing with CRDT-based conflict resolution.
This runs alongside the existing document hub for presence/cursor sharing.

Updated for pycrdt-websocket 0.16+ API.
"""
import asyncio
import os
from pathlib import Path
from typing import Dict, Optional, Callable, Awaitable, Any
from pycrdt import Doc, Text
from pycrdt.websocket import WebsocketServer, ASGIServer
from pycrdt.websocket.yroom import YRoom

from ..config import BASE_DIR

_packet_logging_enabled = os.environ.get("NOTEWORTHY_PACKET_LOG", "").lower() in {"1", "true", "yes", "on"}


def set_packet_logging(enabled: bool):
    """Enable/disable low-level Yjs websocket packet logging."""
    global _packet_logging_enabled
    _packet_logging_enabled = bool(enabled)


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
    
    async def save(self):
        """Save content to disk immediately."""
        print(f"[YjsRoom] Starting save for {self.room_name}")
        text = self.ydoc.get("content", type=Text)
        content = str(text)
        
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text(content, encoding='utf-8')
            print(f"[YjsRoom] Saved {self.room_name} ({len(content)} chars)")
        except Exception as e:
            print(f"[YjsRoom] Error saving {self.room_name}: {e}")

    def _on_change(self, event):
        """Persist changes to disk immediately."""
        print(f"[YjsRoom] Change detected in {self.room_name}")
        # Create save task immediately
        loop = asyncio.get_running_loop()
        loop.create_task(self.save())


class NoteworthyWebsocketServer(WebsocketServer):
    """Custom WebsocketServer that delegates room creation to YjsProvider."""
    
    def __init__(self, provider: 'YjsProvider', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.provider = provider
    
    async def get_room(self, name: str) -> NoteworthyRoom:
        """Override to use our custom room logic."""
        return await self.provider.get_room(name)


class YjsProvider:
    """
    Manages Yjs/CRDT document synchronization.
    
    Each document (file) gets its own "room" for collaborative editing.
    """
    
    def __init__(self):
        self.rooms: Dict[str, NoteworthyRoom] = {}
        self.server: Optional[NoteworthyWebsocketServer] = None
        self._callbacks = []
    
    async def get_room(self, file_path: str) -> NoteworthyRoom:
        """Get or create a room for a file (async for pycrdt-websocket compatibility)."""
        print(f"[YjsProvider] get_room called for: {file_path}")
        # Normalize path (remove /yjs/ prefix if present)
        original_path = file_path
        if file_path.startswith("/yjs/"):
            file_path = file_path[5:]
        elif file_path.startswith("/"):
            file_path = file_path[1:]
            
        print(f"[YjsProvider] Normalized path: {original_path} -> {file_path}")

        if file_path not in self.rooms:
            print(f"[YjsProvider] Creating new NoteworthyRoom for {file_path}")
            room = NoteworthyRoom(room_name=file_path)
            self.rooms[file_path] = room
        else:
            print(f"[YjsProvider] Found existing NoteworthyRoom for {file_path}")
            
        room = self.rooms[file_path]
        
        # Ensure it's in the server's room list too (critical for pycrdt-websocket)
        if self.server:
            # We map the room in the server so it knows about it
            if file_path not in self.server.rooms:
                print(f"[YjsProvider] Registering room with WebsocketServer: {file_path}")
                self.server.rooms[file_path] = room
        
        # Initialize content from disk if needed
        await room.initialize()
        
        # Start the room (required by pycrdt-websocket)
        if self.server:
            # Check if already started or start it
            await self.server.start_room(room)
        
        return room
    
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

# Cached ASGI app (singleton)
_yjs_asgi_app = None


def get_yjs_asgi_app():
    """
    Create the ASGI application for Yjs WebSocket handling.
    
    This is mounted at /yjs in the main FastAPI app.
    Returns a cached singleton to prevent multiple WebsocketServer instances.
    """
    global _yjs_asgi_app
    
    # Return cached app if already created
    if _yjs_asgi_app is not None:
        print("[YjsProvider] Returning cached Yjs ASGI app")
        return _yjs_asgi_app
    
    # Create the custom websocket server
    server = NoteworthyWebsocketServer(
        provider=yjs_provider,
        rooms_ready=True, 
        auto_clean_rooms=False
    )
    yjs_provider.server = server
    
    # NOTE: We no longer monkey-patch server.get_room because we subclassed it.
    
    print("[YjsProvider] Initializing Yjs ASGI app structure...")
    yjs_asgi = ASGIServer(server)

    async def app_wrapper(scope, receive, send):
        if scope.get("type", "") == "websocket":
            print(f"[YjsWrapper] Wrapper called with path: {scope.get('path')}")
            # Inject path into a custom key in case ASGIServer/FastAPI strips 'path' or creates a new scope
            scope["yjs_path_hack"] = scope.get("path")
            
        # Debug wrappers for packet logging
        async def logging_receive():
            msg = await receive()
            if _packet_logging_enabled and msg["type"] == "websocket.receive":
                data = msg.get("bytes") or msg.get("text")
                if data:
                    size = len(data)
                    prefix = ""
                    if isinstance(data, bytes) and size > 0:
                        # Log message type (0=Sync, 1=Awareness)
                        msg_type = data[0]
                        prefix = f" [Type={msg_type}]"
                    print(f"[Yjs] <<< RECV {scope.get('path')} ({size}b){prefix}")
                    print(data)
            return msg

        async def logging_send(msg):
            if _packet_logging_enabled and msg["type"] == "websocket.send":
                data = msg.get("bytes") or msg.get("text")
                if data:
                    size = len(data)
                    prefix = ""
                    if isinstance(data, bytes) and size > 0:
                        msg_type = data[0]
                        prefix = f" [Type={msg_type}]"
                    print(f"[Yjs] >>> SEND {scope.get('path')} ({size}b){prefix}")
                    print(data)
            await send(msg)
        # Lifespan events handled in main server.py
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
            
        try:
            return await yjs_asgi(scope, logging_receive, logging_send)
        except Exception as e:
            print(f"[YjsWrapper] Error in yjs_asgi: {e}")
            raise e

    _yjs_asgi_app = app_wrapper
    return _yjs_asgi_app
