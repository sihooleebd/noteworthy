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
import time
import difflib
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from fastapi import WebSocket
from pathlib import Path

from ..config import BASE_DIR, RENDERER_FILE
from .crdt_manager import crdt_manager


# User colors for cursor decorations
USER_COLORS = [
    "#FF6B6B", "#4ECDC4", "#FFE66D", "#95E1D3",
    "#F38181", "#AA96DA", "#FCBAD3", "#A8D8EA"
]


@dataclass
class User:
    """Connected user."""
    id: str
    name: str
    color: str
    websocket: WebSocket
    current_file: Optional[str] = None
    cursor_line: int = 1
    cursor_column: int = 1
    # Selection range (Google Docs-style highlighting)
    selection_start_line: Optional[int] = None
    selection_start_column: Optional[int] = None
    selection_end_line: Optional[int] = None
    selection_end_column: Optional[int] = None


@dataclass
class Document:
    """Document state."""
    path: str
    content: str
    version: int = 0
    diagnostics: List[dict] = field(default_factory=list)


class DocumentHub:
    """
    Unified document manager - single source of truth.
    
    Handles sync, cursors, LSP, and preview through one interface.
    """
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.documents: Dict[str, Document] = {}
        self.color_index = 0
        self._lock = asyncio.Lock()
        self._diagnostics_task: Optional[asyncio.Task] = None
        self._pending_diagnostics: set = set()
        self._crdt_observers: Dict[str, Callable] = {}  # path -> observer callback
        self._event_loop = None  # Set on first connect
        
        # Emacs clients reference (set by server.py)
        self.emacs_clients: Dict = {}  # user_id -> {"websocket": ws, "name": str, "color": str, "file": str}
        
        # Preview manager reference (set externally)
        self.preview_manager = None
    
    def _get_color(self) -> str:
        color = USER_COLORS[self.color_index % len(USER_COLORS)]
        self.color_index += 1
        return color
    
    async def connect(self, websocket: WebSocket, name: str = "Anonymous", user_id: str = None) -> User:
        """Register a new user connection."""
        # Store event loop for CRDT observer callbacks
        if self._event_loop is None:
            self._event_loop = asyncio.get_running_loop()
            
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
    
    async def update_content(self, user_id: str, path: str, content: str, skip_crdt: bool = False, ops: List[dict] = None):
        """
        User updated document content - SINGLE broadcast point for ALL clients.
        
        Args:
            skip_crdt: If True, skip CRDT update (used when called from Emacs path)
            ops: Optional list of Yjs operations (deltas). If provided (from Emacs), 
                 they are used for broadcasting. If not (Web), they are computed via diff.
        """
        broadcast_ops = ops or []
        
        if content is None and ops:
            # We need the current content to apply ops and get new content
            if path in self.documents:
                current_text = self.documents[path].content
            else:
                current_text = await crdt_manager.get_content(path)
            
            content = self._apply_ops_to_string(current_text, ops)
        
        if not skip_crdt:
            # Get current content from CRDT to compute delta
            current_content = await crdt_manager.get_content(path)
            
            # Compute diff-based delta to preserve concurrent edits where possible
            matcher = difflib.SequenceMatcher(None, current_content, content)
            computed_ops = []
            
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'equal':
                    # Retain unchanged characters
                    count = i2 - i1
                    if count > 0:
                        computed_ops.append({"retain": count})
                elif tag == 'replace':
                    # Delete old, insert new
                    count = i2 - i1
                    if count > 0:
                        computed_ops.append({"delete": count})
                    text = content[j1:j2]
                    if text:
                        computed_ops.append({"insert": text})
                elif tag == 'delete':
                    # Delete characters
                    count = i2 - i1
                    if count > 0:
                        computed_ops.append({"delete": count})
                elif tag == 'insert':
                    # Insert characters
                    text = content[j1:j2]
                    if text:
                        computed_ops.append({"insert": text})
            
            broadcast_ops = computed_ops
            
            # Apply to CRDT (this saves to disk)
            if broadcast_ops:
                await crdt_manager.apply_delta(path, broadcast_ops, source_user=user_id)
        
        # Update local cache
        if path not in self.documents:
            self.documents[path] = Document(path=path, content=content, version=0)
        
        doc = self.documents[path]
        doc.content = content
        doc.version += 1
        
        print(f"[Hub Debug] Broadcasting update for {path} from {user_id}. Version: {doc.version}")
        
        # 2a. Broadcast to WEB clients on this file
        await self._broadcast_to_file(path, {
            "type": "content",
            "content": content,
            "version": doc.version,
            "userId": user_id
        }, exclude=user_id)
        
        
        # 2b. Broadcast to EMACS clients on this file
        # Emacs expects "delta" messages for incremental updates
        if broadcast_ops:
            await self._broadcast_to_emacs_file(path, {
                "type": "delta",
                "file": path,
                "ops": broadcast_ops,
                "version": doc.version,
                "source": "hub",
                "userId": user_id
            }, exclude=user_id)
        else:
            # Fallback to sync if no ops (e.g. reload) or empty delta
            await self._broadcast_to_emacs_file(path, {
                "type": "sync",
                "file": path,
                "content": content,
                "version": doc.version,
                "source": "hub",
                "userId": user_id
            }, exclude=user_id)
        
        # 3. Schedule LSP diagnostics (debounced)
        if path.endswith('.typ'):
            self._pending_diagnostics.add(path)
            if self._diagnostics_task is None or self._diagnostics_task.done():
                self._diagnostics_task = asyncio.create_task(self._run_diagnostics_debounced())
        
        # 4. Preview - handled automatically by typst watch monitoring file changes
    
    async def on_preview_update(self, updates: list, source_path: str):
        """
        Handle preview updates from PreviewManager.
        Broadcasts to users who are currently editing this file.
        """
        await self._broadcast_to_file(source_path, {
            "type": "preview",
            "updates": updates
        })

    async def _load_document(self, path: str) -> Document:
        """Load document from CRDT (which loads from disk if needed)."""
        # Use CRDT as the source of truth
        content = await crdt_manager.get_content(path)
        
        if path not in self.documents:
            self.documents[path] = Document(path=path, content=content, version=0)
        else:
            # Refresh content from CRDT
            self.documents[path].content = content
        
        return self.documents[path]

    
    async def join_file(self, user_id: str, path: str) -> Document:
        """User joins a file for editing."""
        if user_id not in self.users:
            return None
        
        user = self.users[user_id]
        
        # Stop watching old file if exists
        try:
            if user.current_file and user.current_file.endswith('.typ') and self.preview_manager:
                self.preview_manager.stop_watch(user.current_file)
        except Exception as e:
            print(f"[Hub] Error stopping watch: {e}")
            
        user.current_file = path
        
        # Load document from CRDT
        doc = await self._load_document(path)
        
        
        # Start preview if .typ file
        if path.endswith('.typ') and self.preview_manager:
            try:
                self.preview_manager.start_watch(path)
                
                # Spawn background task to send initial preview so we don't block doc load
                async def send_initial_preview():
                    try:
                        # Retry a few times if cache is empty (typst might still be compiling)
                        for _ in range(10):  # Try up to 10 times = ~2 seconds
                            # Check immediately first, then sleep
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
                                    break
                            await asyncio.sleep(0.2)
                    except Exception as e:
                        print(f"[Hub] Background preview send failed: {e}")

                asyncio.create_task(send_initial_preview())
                        
            except Exception as e:
                print(f"[Hub] Error starting watch: {e}")
        
        # Send cached diagnostics to new user
        if doc.diagnostics:
            await user.websocket.send_text(json.dumps({
                "type": "diagnostics",
                "diagnostics": doc.diagnostics
            }))
            
        return doc
    
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
    
    async def broadcast_log(self, level: str, message: str):
        """Broadcast log message to all clients (Web + Emacs)."""
        await self._broadcast({
            "type": "log",
            "level": level,
            "message": message,
            "timestamp": int(time.time() * 1000)
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
        """Broadcast to web users editing a specific file."""
        msg_json = json.dumps(message)
        for user_id, user in list(self.users.items()):
            if user_id == exclude:
                continue
            
            if user.current_file == path:
                try:
                    await user.websocket.send_text(msg_json)
                except:
                    pass
    
    async def _broadcast_to_emacs_file(self, path: str, message: dict, exclude: str = None):
        """Broadcast to Emacs clients editing a specific file."""
        msg_json = json.dumps(message)
        for user_id, client in list(self.emacs_clients.items()):
            if user_id == exclude:
                continue
            if client.get("file") == path:
                try:
                    await client["websocket"].send_text(msg_json)
                except:
                    pass

    def _apply_ops_to_string(self, content: str, ops: List[dict]) -> str:
        """Apply a linear sequence of ops to a string with bounds checking."""
        new_content = []
        pos = 0
        content_len = len(content)
        
        for op in ops:
            if 'retain' in op:
                retain = op['retain']
                # Clamp retain to remaining content
                if pos + retain > content_len:
                    retain = content_len - pos
                if retain > 0:
                    new_content.append(content[pos:pos+retain])
                    pos += retain
            elif 'insert' in op:
                new_content.append(op['insert'])
            elif 'delete' in op:
                delete_count = op['delete']
                # Clamp delete to remaining content
                remaining = content_len - pos
                if delete_count > remaining:
                    delete_count = remaining
                pos += delete_count
        
        # Append remaining content (implicit trailing retain)
        if pos < content_len:
            new_content.append(content[pos:])
            
        return "".join(new_content)



# Global instance
document_hub = DocumentHub()
