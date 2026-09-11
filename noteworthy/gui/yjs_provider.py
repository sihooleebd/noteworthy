"""
Yjs/CRDT WebSocket Provider for Noteworthy GUI

Uses pycrdt-websocket for collaborative editing with CRDT-based conflict resolution.
This runs alongside the existing document hub for presence/cursor sharing.

Updated for pycrdt-websocket 0.16+ API.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Callable, Awaitable, Any
from pycrdt import Doc, Text
from pycrdt.websocket import WebsocketServer, ASGIServer
from pycrdt.websocket.yroom import YRoom

from ..config import BASE_DIR
log = logging.getLogger("noteworthy.gui")

_packet_logging_enabled = os.environ.get("NOTEWORTHY_PACKET_LOG", "").lower() in {"1", "true", "yes", "on"}


def set_packet_logging(enabled: bool):
    """Enable/disable low-level Yjs websocket packet logging."""
    global _packet_logging_enabled
    _packet_logging_enabled = bool(enabled)


CRDT_STATE_DIR = BASE_DIR / ".noteworthy-crdt"


def _state_path(room_name: str) -> Path:
    """Where this room's CRDT state blob lives, mirroring the content path."""
    return CRDT_STATE_DIR / (room_name + ".bin")


def _resolve_room_path(room_name: str) -> Path | None:
    """Resolve a websocket room name to a path inside BASE_DIR.

    Room names come straight from the /yjs websocket URL (untrusted client
    input) — mirrors the containment check server.py's HTTP API already
    does in `_resolve_in_project`. Returns None if the name would resolve
    outside the project root, so callers can refuse to create/serve a room
    for it instead of writing outside the project.
    """
    if not room_name:
        return None
    target = BASE_DIR / room_name
    try:
        target.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        return None
    return target


class NoteworthyRoom(YRoom):
    """
    Custom room that syncs with disk.
    Each file gets its own room identified by relative file path.
    """
    
    def __init__(self, room_name: str, *args, **kwargs):
        super().__init__(ready=True, *args, **kwargs)  # Start ready since we load sync
        self.room_name = room_name
        # Room names come straight off the websocket URL — refuse to build a
        # room that would read/write outside BASE_DIR (path traversal via
        # e.g. room_name="../../etc/passwd"). Raising here means the caller
        # never inserts this room into the registry, so it can't be created
        # or served.
        file_path = _resolve_room_path(room_name)
        if file_path is None:
            raise ValueError(f"Room name escapes project root: {room_name!r}")
        self._file_path = file_path
        self._initialized = False
        # CRITICAL: the Text wrapper and its Subscription must be kept alive
        # on the room. pycrdt subscriptions are RAII guards — if the wrapper
        # returned by ydoc.get() is garbage-collected, the observer is
        # silently dropped and changes are never persisted to disk.
        self._text: Text | None = None
        self._save_subscription = None
        self._save_handle: asyncio.TimerHandle | None = None
        self._save_delay = 0.25  # debounce window (seconds)
        
    def _file_is_newer(self, state: Path) -> bool:
        """True when the text file was written after the CRDT state was."""
        try:
            return self._file_path.stat().st_mtime > state.stat().st_mtime + 1
        except OSError:
            return False

    async def initialize(self):
        """Load initial content from disk into the CRDT document.

        Deliberately not short-circuited on `_initialized`.  A room opened
        before its file existed -- the structure editor creates the entry, the
        file arrives a moment later -- started empty and stayed empty, and
        being the authority it would then write that emptiness over the file
        the first time anyone touched it.  Filling an *empty* document is safe
        whenever it happens; one that already holds text is never touched, so
        this cannot clobber live content.
        """
        self._text = self.ydoc.get("content", type=Text)

        # Restore the document itself, not merely its text.
        #
        # Rebuilding a Doc by reading the file produces something that *looks*
        # identical to what connected clients hold but has a different identity
        # -- different client id, different insertion history.  Yjs merges by
        # identity, so on reconnect each side kept both copies and the file
        # doubled.  Once per restart, which is exactly how content/8/1.typ went
        # 7249 -> 14498 -> 21747 -> 28996 bytes.
        state = _state_path(self.room_name)
        restored = False
        if not self._initialized and state.exists():
            try:
                self.ydoc.apply_update(state.read_bytes())
                restored = True
                log.info(f"[YjsRoom] Restored {self.room_name} from CRDT state "
                         f"({len(self._text)} chars)")
            except Exception as e:
                log.error(f"[YjsRoom] Could not restore {self.room_name}: {e}")

        if self._file_path.exists():
            try:
                content = self._file_path.read_text(encoding='utf-8')
                if content and len(self._text) == 0:
                    # First load, or a room that opened before the file had
                    # anything in it.
                    self._text += content
                    log.info(f"[YjsRoom] Loaded {self.room_name}: {len(content)} chars")
                elif restored and content != str(self._text) and self._file_is_newer(state):
                    # The file was edited while we were not running -- a repair,
                    # a git checkout.  Let it win, but by rewriting this
                    # document's text rather than starting a new one, so the
                    # identity survives and clients converge instead of
                    # duplicating.
                    log.warning(f"[YjsRoom] {self.room_name} changed on disk while "
                                f"stopped; taking the file ({len(content)} chars)")
                    del self._text[:]
                    self._text += content
            except Exception as e:
                log.error(f"[YjsRoom] Error loading {self.room_name}: {e}")
        elif not self._initialized and not restored:
            log.info(f"[YjsRoom] File not found, starting empty: {self.room_name}")

        if self._initialized:
            return

        # Set up change callback for persistence (subscription kept on self —
        # see __init__ note; dropping it would unobserve).  Once only: a second
        # observer would save twice for every edit.
        self._save_subscription = self._text.observe(self._on_change)

        self._initialized = True
    
    async def save(self):
        """Save content to disk atomically (temp file + rename).

        Atomic replace prevents typst watch / tinymist from ever reading a
        partially written file.
        """
        text = self.ydoc.get("content", type=Text)
        content = str(text)

        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._file_path.with_name(f".{self._file_path.name}.nw-tmp")
            tmp_path.write_text(content, encoding='utf-8')
            os.replace(tmp_path, self._file_path)
            log.debug(f"[YjsRoom] Saved {self.room_name} ({len(content)} chars)")
        except Exception as e:
            log.error(f"[YjsRoom] Error saving {self.room_name}: {e}")

        # The text file is an export; this is the document.  Without it a
        # restart has to rebuild the Doc from the text, which gives a new
        # identity and makes every still-connected client duplicate its copy on
        # reconnect.  Written atomically for the same reason as the text.
        try:
            state = _state_path(self.room_name)
            state.parent.mkdir(parents=True, exist_ok=True)
            tmp_state = state.with_name(f".{state.name}.nw-tmp")
            tmp_state.write_bytes(self.ydoc.get_update())
            os.replace(tmp_state, state)
        except Exception as e:
            log.error(f"[YjsRoom] Error saving CRDT state for {self.room_name}: {e}")

    def _on_change(self, event):
        """Schedule a debounced save after document changes."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        if self._save_handle is not None:
            self._save_handle.cancel()
        self._save_handle = loop.call_later(
            self._save_delay, lambda: asyncio.ensure_future(self.save())
        )

    def rebind(self, new_room_name: str, new_file_path: Path):
        """Point this room at a new on-disk location after a rename/move.

        Clients keep talking to the same live CRDT document (no reconnect
        needed) — only the save target and lookup name change.
        """
        self.room_name = new_room_name
        self._file_path = new_file_path

    async def close(self):
        """Tear down this room: stop persisting and disconnect its clients.

        Called when the file behind this room is deleted, or moved out from
        under it without being rebound. Without this, the debounced save
        timer (or a future edit from a still-open client) would fire and
        write the in-memory content straight back to the old path —
        resurrecting a file the user just deleted.
        """
        if self._save_handle is not None:
            self._save_handle.cancel()
            self._save_handle = None
        if self._text is not None and self._save_subscription is not None:
            try:
                self._text.unobserve(self._save_subscription)
            except Exception as e:
                log.debug(f"[YjsRoom] unobserve failed for {self.room_name} (already gone?): {e}")
            self._save_subscription = None
        try:
            if self._task_group is not None:
                await self.stop()
        except Exception as e:
            log.error(f"[YjsRoom] Error stopping room {self.room_name}: {e}")


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
        self._room_locks: Dict[str, asyncio.Lock] = {}
    
    async def get_room(self, file_path: str) -> NoteworthyRoom:
        """Get or create a room for a file (async for pycrdt-websocket compatibility)."""
        log.debug(f"[YjsProvider] get_room called for: {file_path}")
        # Normalize path (remove /yjs/ prefix if present)
        original_path = file_path
        if file_path.startswith("/yjs/"):
            file_path = file_path[5:]
        elif file_path.startswith("/"):
            file_path = file_path[1:]
            
        log.debug(f"[YjsProvider] Normalized path: {original_path} -> {file_path}")

        # Serialize per-room setup. Two clients opening the same *cold* room at
        # once would otherwise race through create/initialize/start_room, and the
        # loser's websocket ends up on a room that never syncs it — the tab looks
        # connected (presence and chat work) but never receives document content.
        lock = self._room_locks.setdefault(file_path, asyncio.Lock())
        async with lock:
            return await self._get_room_locked(file_path)

    async def _get_room_locked(self, file_path: str) -> NoteworthyRoom:
        """Create/initialize/start the room. Callers must hold the room lock."""
        if file_path not in self.rooms:
            log.debug(f"[YjsProvider] Creating new NoteworthyRoom for {file_path}")
            room = NoteworthyRoom(room_name=file_path)
            self.rooms[file_path] = room
        else:
            log.debug(f"[YjsProvider] Found existing NoteworthyRoom for {file_path}")
            
        room = self.rooms[file_path]
        
        # Ensure it's in the server's room list too (critical for pycrdt-websocket)
        if self.server:
            # We map the room in the server so it knows about it
            if file_path not in self.server.rooms:
                log.debug(f"[YjsProvider] Registering room with WebsocketServer: {file_path}")
                self.server.rooms[file_path] = room
        
        # Initialize content from disk if needed
        await room.initialize()
        
        # Start the room (required by pycrdt-websocket)
        if self.server:
            # Check if already started or start it
            await self.server.start_room(room)
        
        return room
    
    async def close_room(self, file_path: str):
        """Close and forget the room at `file_path` (e.g. its file was deleted).

        No-op if no room is live for that path. Serialized on the same
        per-room lock as get_room to avoid racing a concurrent open.
        """
        lock = self._room_locks.setdefault(file_path, asyncio.Lock())
        async with lock:
            room = self.rooms.pop(file_path, None)
            if room is None:
                return
            if self.server is not None:
                self.server.rooms.pop(file_path, None)
            log.info(f"[YjsProvider] Closing room {file_path}")
            await room.close()
            # The file is going; its CRDT state would otherwise be restored
            # onto a path that no longer has one, and a file later recreated
            # there would come back with the old document's contents.
            try:
                _state_path(file_path).unlink(missing_ok=True)
            except OSError as e:
                log.error(f"[YjsProvider] Could not drop CRDT state for {file_path}: {e}")

    async def rename_room(self, old_path: str, new_path: str):
        """Rebind the room at `old_path` to `new_path` after a filesystem rename.

        No-op if no room is live for old_path — the rename happened purely
        on disk and there's nothing to resurrect. If a (stale) room already
        occupies new_path, it's closed rather than silently overwritten, so
        its save timer/clients don't leak.
        """
        new_file_path = _resolve_room_path(new_path)
        if new_file_path is None:
            log.error(f"[YjsProvider] Refusing to rebind room to unsafe path: {new_path!r}")
            await self.close_room(old_path)
            return

        lock = self._room_locks.setdefault(old_path, asyncio.Lock())
        async with lock:
            room = self.rooms.pop(old_path, None)
            if room is None:
                return
            if self.server is not None:
                self.server.rooms.pop(old_path, None)

            existing = self.rooms.pop(new_path, None)
            if existing is not None:
                if self.server is not None:
                    self.server.rooms.pop(new_path, None)
                await existing.close()

            room.rebind(new_path, new_file_path)
            self.rooms[new_path] = room
            if self.server is not None:
                self.server.rooms[new_path] = room
            log.info(f"[YjsProvider] Rebound room {old_path} -> {new_path}")

    def _rooms_under(self, path: str) -> list:
        """Room keys equal to `path`, or nested under it (directory ops)."""
        prefix = path.rstrip("/") + "/"
        return [name for name in self.rooms if name == path or name.startswith(prefix)]

    async def close_rooms_under(self, path: str):
        """Close every live room at or under `path` (file or directory delete)."""
        for name in self._rooms_under(path):
            await self.close_room(name)

    async def rename_rooms_under(self, old_path: str, new_path: str):
        """Rebind every live room at or under `old_path` (file or directory rename)."""
        for name in self._rooms_under(old_path):
            suffix = name[len(old_path):]  # '' for exact match, '/...' for nested
            await self.rename_room(name, new_path + suffix)

    def add_change_callback(self, callback):
        """Register callback for content changes (for diagnostics/preview triggers)."""
        self._callbacks.append(callback)
    
    async def notify_change(self, file_path: str, content: str):
        """Notify all callbacks of a content change."""
        for cb in self._callbacks:
            try:
                await cb(file_path, content)
            except Exception as e:
                log.error(f"[YjsProvider] Callback error: {e}")


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
        log.debug("[YjsProvider] Returning cached Yjs ASGI app")
        return _yjs_asgi_app
    
    # Create the custom websocket server
    server = NoteworthyWebsocketServer(
        provider=yjs_provider,
        rooms_ready=True, 
        auto_clean_rooms=False
    )
    yjs_provider.server = server
    
    # NOTE: We no longer monkey-patch server.get_room because we subclassed it.
    
    log.info("[YjsProvider] Initializing Yjs ASGI app structure...")
    yjs_asgi = ASGIServer(server)

    async def app_wrapper(scope, receive, send):
        if scope.get("type", "") == "websocket":
            log.debug(f"[YjsWrapper] Wrapper called with path: {scope.get('path')}")

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
                    log.info(f"[Yjs] <<< RECV {scope.get('path')} ({size}b){prefix}")
                    log.info(data)
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
                    log.info(f"[Yjs] >>> SEND {scope.get('path')} ({size}b){prefix}")
                    log.info(data)
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
            log.error(f"[YjsWrapper] Error in yjs_asgi: {e}")
            raise e

    _yjs_asgi_app = app_wrapper
    return _yjs_asgi_app
