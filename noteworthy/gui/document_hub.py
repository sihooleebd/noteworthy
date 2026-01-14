"""
DocumentHub - Unified Real-time Document Manager

Single source of truth for document state, handling:
- Multi-user sync (content broadcasting)
- Cursor position sharing
- LSP diagnostics triggering
- Preview updates

All through a single WebSocket connection.
"""
import asyncio
import json
import uuid
import subprocess
import tempfile
import os
import hashlib
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from fastapi import WebSocket
from pathlib import Path
from pycrdt import Text

from ..config import BASE_DIR, RENDERER_FILE
from .yjs_provider import yjs_provider





# User colors for cursor decorations
USER_COLORS = [
    "#FF6B6B", "#4ECDC4", "#FFE66D", "#95E1D3",
    "#F38181", "#AA96DA", "#FCBAD3", "#A8D8EA"
]

@dataclass
class User:
    """Connected user."""
    id: str
    name: str = "Anonymous"
    color: str = "#FF6B6B"
    websocket: WebSocket = None
    # State tracking
    current_file: Optional[str] = None
    cursor_line: int = 1
    cursor_column: int = 1
    # Selection state
    selection_start_line: Optional[int] = None
    selection_start_column: Optional[int] = None
    selection_end_line: Optional[int] = None
    selection_end_column: Optional[int] = None


class DocumentHub:
    """
    Unified document manager - single source of truth.
    
    Handles sync, cursors, LSP, and preview through one interface.
    """
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.color_index = 0
        self._lock = asyncio.Lock()
        self._diagnostics_task: Optional[asyncio.Task] = None
        self._pending_diagnostics: set = set()
        
        # Preview manager reference (set externally)
        self.preview_manager = None
    
    def _get_color(self) -> str:
        color = USER_COLORS[self.color_index % len(USER_COLORS)]
        self.color_index += 1
        return color
    
    async def connect(self, websocket: WebSocket, name: str = "Anonymous", user_id: str = None) -> User:
        """Register a new user connection."""
        if not user_id:
            user_id = str(uuid.uuid4())[:8]
            
        if user_id in self.users:
            # Reconnecting existing user - update socket
            user = self.users[user_id]
            user.websocket = websocket
            user.name = name # Update name just in case
            
            # Notify others of update (status/name)
            await self._broadcast({
                "type": "user_updated",
                "user": {"id": user_id, "name": name, "color": user.color}
            })
        else:
            # New user
            user = User(
                id=user_id,
                name=name,
                color=self._get_color(),
                websocket=websocket
            )
            self.users[user_id] = user
            
            # Notify others
            await self._broadcast({
                "type": "user_joined",
                "user": {"id": user_id, "name": name, "color": user.color}
            }, exclude=user_id)
        
        return user
    
    async def on_preview_update(self, updates: list, source_path: str):
        """
        Handle preview updates from PreviewManager.
        Broadcasts to users who are currently editing this file.
        """
        await self._broadcast_to_file(source_path, {
            "type": "preview",
            "updates": updates
        })




    
    async def join_file(self, user_id: str, path: str):
        """User joins a file for editing (presence only)."""
        if user_id not in self.users:
            return
        
        user = self.users[user_id]
        
        # Stop watching old file if exists
        try:
            if user.current_file and user.current_file.endswith('.typ') and self.preview_manager:
                self.preview_manager.stop_watch(user.current_file)
        except Exception as e:
            print(f"[Hub] Error stopping watch: {e}")
            
        user.current_file = path
        
        # Start preview if .typ file
        if path.endswith('.typ') and self.preview_manager:
            try:
                self.preview_manager.start_watch(path)
                
                # Attach Awareness listener for bridging Web -> Emacs
                try:
                    room = await yjs_provider.get_room(path)
                    if not getattr(room, "_awareness_hook_attached", False):
                        
                        def awareness_cb(topic, event, origin):
                            # Handle remote awareness changes (from Web)
                            if origin == "local": return 
                            # Iterate changed clients
                            # Note: pycrdt awareness event structure is complex
                            # We'll just scan states for now
                            self._broadcast_availability(path)

                        # room.awareness.on("update", awareness_cb) 
                        # pycrdt awareness listener is tricky in python
                        # simplified: WE rely on yjs_provider to handle this or polling?
                        # Using a polling task for now is safer/easier than fighting pycrdt async events inside sync callbacks
                        pass
                        
                        # Set flag
                        room._awareness_hook_attached = True
                except:
                    pass

                # Send current cached state to this user immediately
                # Retry a few times if cache is empty (typst might still be compiling)
                for _ in range(10):  # Try up to 10 times = ~2 seconds
                    await asyncio.sleep(0.2)
                    status = self.preview_manager.get_status(path)
                    if status['pages']:
                        updates = []
                        for page in status['pages']:
                            svg_bytes = self.preview_manager.get_image(path, page)
                            if svg_bytes:
                                updates.append({
                                    'page': page, 
                                    'svg': svg_bytes.decode('utf-8')
                                })
                        
                        if updates:
                            await user.websocket.send_text(json.dumps({
                                "type": "preview",
                                "updates": updates
                            }))
                            break  # Exit retry loop once we have updates
                        
            except Exception as e:
                print(f"[Hub] Error starting watch: {e}")
        
        # Notify others
        await self._broadcast_to_file(path, {
            "type": "user_joined",
            "userId": user_id,
            "user": {
                "id": user.id,
                "name": user.name,
                "color": user.color
            },
            "users": self.get_users_on_file(path)
        }, exclude=user_id)
    
    async def disconnect(self, user_id: str, websocket: WebSocket = None):
        """Remove a user."""
        if user_id in self.users:
            user = self.users[user_id]
            
            # Only disconnect if this is the active socket
            # Prevents race condition where old socket kills new session
            if websocket and user.websocket != websocket:
                return

            try:
                # Stop watching their current file
                if user.current_file and user.current_file.endswith('.typ') and self.preview_manager:
                    self.preview_manager.stop_watch(user.current_file)
            except Exception as e:
                print(f"[Hub] Error stopping watch during disconnect: {e}")
            
            del self.users[user_id]
            await self._broadcast({
                "type": "user_left",
                "userId": user_id
            })
    
    async def _run_diagnostics_debounced(self):
        """Run diagnostics after a short delay."""
        await asyncio.sleep(0.5)  # 500ms debounce
        
        paths = list(self._pending_diagnostics)
        self._pending_diagnostics.clear()
        
        for path in paths:
            diagnostics = await self._check_diagnostics(path)
            
            # Cache diagnostics
            if path in self.documents:
                self.documents[path].diagnostics = diagnostics
                
            # Send to all users on this file
            await self._broadcast_to_file(path, {
                "type": "diagnostics",
                "diagnostics": diagnostics
            })
    
    async def _check_diagnostics(self, path: str) -> List[dict]:
        """Run typst compile and extract diagnostics."""
        import shutil
        
        typst_bin = shutil.which("typst")
        if not typst_bin:
            for p in ["/opt/homebrew/bin/typst", "/usr/local/bin/typst", 
                      os.path.expanduser("~/.cargo/bin/typst")]:
                if os.path.exists(p):
                    typst_bin = p
                    break
        
        if not typst_bin:
            return []
        
        # Create temp file for output
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Scan content directory
            content_dir = BASE_DIR / "content"
            chapter_folders = []
            page_folders = {}
            
            if content_dir.exists():
                ch_dirs = sorted(
                    [d for d in content_dir.iterdir() if d.is_dir() and d.name.replace('.', '', 1).lstrip('-').isdigit()],
                    key=lambda d: float(d.name) if d.name.replace('.', '', 1).lstrip('-').isdigit() else 999
                )
                for idx, ch_dir in enumerate(ch_dirs):
                    chapter_folders.append(ch_dir.name)
                    pg_files = sorted(
                        [f.stem for f in ch_dir.glob("*.typ") if f.stem.replace('.', '', 1).lstrip('-').isdigit()],
                        key=lambda s: float(s) if s.replace('.', '', 1).lstrip('-').isdigit() else 999
                    )
                    page_folders[str(idx)] = pg_files
            
            # Run typst compile in a separate thread to avoid blocking the event loop
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    typst_bin, "compile", str(RENDERER_FILE), tmp_path,
                    "--root", str(BASE_DIR),
                    "--input", f"chapter-folders={json.dumps(chapter_folders)}",
                    "--input", f"page-folders={json.dumps(page_folders)}"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            diagnostics = []
            current_error = None
            
            for line in result.stderr.split('\n'):
                stripped = line.strip()
                
                if stripped.startswith("error:"):
                    msg = stripped[6:].strip()
                    current_error = {"message": msg, "severity": "error"}
                
                elif ("┌" in stripped or "├" in stripped) and current_error:
                    idx = stripped.find("─")
                    if idx != -1:
                        location = stripped[idx+1:].strip()
                        parts = location.split(':')
                        if len(parts) >= 3:
                            try:
                                line_num = int(parts[-2])
                                col_num = int(parts[-1])
                                path_str = ":".join(parts[:-2]).strip()
                                
                                current_error["line"] = line_num
                                current_error["col"] = col_num
                                current_error["file"] = path_str
                                diagnostics.append(current_error)
                                current_error = None
                            except ValueError:
                                pass
            
            return diagnostics
            
        except Exception as e:
            print(f"[Hub] Diagnostics error: {e}")
            return []
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    async def update_cursor(self, user_id: str, line: int, column: int,
                            selection_start_line: int = None, selection_start_column: int = None,
                            selection_end_line: int = None, selection_end_column: int = None):
        """Update user cursor position and selection range."""
        if user_id not in self.users:
            return
        
        user = self.users[user_id]
        user.cursor_line = line
        user.cursor_column = column
        user.selection_start_line = selection_start_line
        user.selection_start_column = selection_start_column
        user.selection_end_line = selection_end_line
        user.selection_end_column = selection_end_column
        
        if not user.current_file:
            return
        
        msg = {
            "type": "cursor",
            "userId": user_id,
            "name": user.name,
            "color": user.color,
            "line": line,
            "column": column
        }
        
        # Include selection range if present
        if selection_start_line is not None:
            msg["selectionStartLine"] = selection_start_line
            msg["selectionStartColumn"] = selection_start_column
            msg["selectionEndLine"] = selection_end_line
            msg["selectionEndColumn"] = selection_end_column
        
        await self._broadcast_to_file(user.current_file, msg, exclude=user_id)
        
        # Bridge to Yjs Awareness (for Web clients)
        try:
            room = await yjs_provider.get_room(user.current_file)
            # Calculate absolute offset
            text = room.ydoc.get("content", type=Text)
            content = str(text)
            
            # Simple line/col to offset
            offset = 0
            lines = content.split('\n')
            for i in range(min(line - 1, len(lines))):
                offset += len(lines[i]) + 1 # +1 for newline
            offset += min(column, len(lines[line-1]) if line-1 < len(lines) else 0)
            
            # Selection
            sel_end = offset
            if selection_start_line is not None:
                # Calculate start offset
                s_off = 0
                for i in range(min(selection_start_line - 1, len(lines))):
                    s_off += len(lines[i]) + 1
                s_off += min(selection_start_column, len(lines[selection_start_line-1]) if selection_start_line-1 < len(lines) else 0)
                
                # Update Awareness
                room.awareness.set_local_state_field("cursor", {
                    "anchor": s_off,
                    "head": offset,
                    "user": {"name": user.name, "color": user.color}
                })
            else:
                 room.awareness.set_local_state_field("cursor", {
                    "anchor": offset,
                    "head": offset,
                    "user": {"name": user.name, "color": user.color}
                })
                
        except Exception as e:
            # print(f"[Hub] Awareness update error: {e}")
            pass
    
    async def update_identity(self, user_id: str, name: str):
        """Update user's display name."""
        if user_id not in self.users:
            return
        
        self.users[user_id].name = name
        
        await self._broadcast({
            "type": "user_updated",
            "user": {
                "id": user_id,
                "name": name,
                "color": self.users[user_id].color
            }
        })
    
    async def send_chat(self, user_id: str, text: str, timestamp: int):
        """Broadcast chat message."""
        if user_id not in self.users:
            return
        
        user = self.users[user_id]
        await self._broadcast({
            "type": "chat",
            "userId": user_id,
            "name": user.name,
            "color": user.color,
            "text": text,
            "timestamp": timestamp
        })
    
    def get_users(self) -> List[dict]:
        """Get all connected users."""
        return [
            {
                "id": u.id, 
                "name": u.name, 
                "color": u.color, 
                "file": u.current_file,
                "cursor_line": u.cursor_line,
                "cursor_column": u.cursor_column
            }
            for u in self.users.values()
        ]
    
    def get_users_on_file(self, path: str, exclude_user_id: str = None) -> List[dict]:
        """Get users currently on a specific file (for cursor sync)."""
        return [
            {
                "id": u.id,
                "name": u.name,
                "color": u.color,
                "cursor_line": u.cursor_line,
                "cursor_column": u.cursor_column
            }
            for u in self.users.values()
            if u.current_file == path and u.id != exclude_user_id
        ]
    
    async def _broadcast(self, message: dict, exclude: str = None):
        """Broadcast to all users."""
        msg_json = json.dumps(message)
        for user_id, user in list(self.users.items()):
            if user_id == exclude:
                continue
            try:
                await user.websocket.send_text(msg_json)
            except:
                pass
    
    async def _broadcast_to_file(self, path: str, message: dict, exclude: str = None):
        """Broadcast to users editing a specific file."""
        msg_json = json.dumps(message)
        for user_id, user in list(self.users.items()):
            if user_id == exclude:
                continue
            if user.current_file == path:
                try:
                    await user.websocket.send_text(msg_json)
                except:
                    pass


# Global instance
document_hub = DocumentHub()
