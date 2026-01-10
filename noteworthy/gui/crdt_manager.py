"""
CRDT Manager for Noteworthy Real-time Collaboration.

Uses pycrdt (Yjs-compatible) for conflict-free document synchronization.
Provides a simple JSON-based delta protocol for Emacs clients.
"""
import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
from dataclasses import dataclass, field

try:
    from pycrdt import Doc, Text
    PYCRDT_AVAILABLE = True
except ImportError:
    PYCRDT_AVAILABLE = False
    print("[CRDT] Warning: pycrdt not installed. Install with: pip install pycrdt")


@dataclass
class DocumentState:
    """State for a single document."""
    doc: Any  # pycrdt.Doc
    version: int = 0
    observers: List[Callable] = field(default_factory=list)
    save_task: Optional[asyncio.Task] = None


class CRDTManager:
    """
    Manages CRDT documents for real-time collaboration.
    
    Each file gets a Y.Doc with a Y.Text for content.
    Converts between pycrdt events and simple delta operations for Emacs.
    """
    
    def __init__(self, base_dir: Path, save_delay: float = 0.5):
        """
        Initialize CRDT manager.
        
        Args:
            base_dir: Project root directory for file operations
            save_delay: Seconds to debounce before saving to disk
        """
        self.base_dir = base_dir
        self.save_delay = save_delay
        self.documents: Dict[str, DocumentState] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the event loop for async operations."""
        self._loop = loop
    
    def get_or_create(self, file_path: str) -> DocumentState:
        """
        Get or create a document state for a file.
        
        Args:
            file_path: Relative path from base_dir (e.g., "content/1/5.typ")
            
        Returns:
            DocumentState for the file
        """
        if not PYCRDT_AVAILABLE:
            raise RuntimeError("pycrdt is required for CRDT support")
        
        if file_path not in self.documents:
            # Load initial content from disk
            full_path = self.base_dir / file_path
            if full_path.exists():
                try:
                    initial_content = full_path.read_text(encoding='utf-8')
                except Exception as e:
                    print(f"[CRDT] Error reading {file_path}: {e}")
                    initial_content = ""
            else:
                initial_content = ""
            
            # Create Y.Doc with Y.Text
            doc = Doc()
            text = Text(initial_content)
            doc["content"] = text
            
            state = DocumentState(doc=doc, version=0)
            self.documents[file_path] = state
            
            # Setup change observer
            def on_change(event):
                self._handle_change(file_path, event)
            
            text.observe(on_change)
            print(f"[CRDT] Created document: {file_path} ({len(initial_content)} chars)")
        
        return self.documents[file_path]
    
    def get_content(self, file_path: str) -> str:
        """Get current content of a document."""
        if file_path not in self.documents:
            return ""
        return str(self.documents[file_path].doc["content"])
    
    def get_version(self, file_path: str) -> int:
        """Get current version of a document."""
        if file_path not in self.documents:
            return 0
        return self.documents[file_path].version
    
    def apply_delta(self, file_path: str, ops: List[dict], source_user: str = None) -> bool:
        """
        Apply delta operations from a client.
        
        Delta format (Quill-style):
        - {"retain": n} - Skip n characters
        - {"insert": "text"} - Insert text at current position
        - {"delete": n} - Delete n characters
        
        Args:
            file_path: Document path
            ops: List of delta operations
            source_user: User ID who made the change (for filtering echoes)
            
        Returns:
            True if applied successfully
        """
        print(f"[CRDT] apply_delta called: file={file_path}, ops={ops}, user={source_user}")
        
        if file_path not in self.documents:
            print(f"[CRDT] Document not found: {file_path}")
            print(f"[CRDT] Available docs: {list(self.documents.keys())}")
            return False
        
        state = self.documents[file_path]
        text = state.doc["content"]
        current_len = len(str(text))
        print(f"[CRDT] Current doc length: {current_len}")
        
        try:
            pos = 0
            with state.doc.transaction():
                for op in ops:
                    print(f"[CRDT]   Applying op: {op} at pos={pos}")
                    if "retain" in op:
                        pos += op["retain"]
                    elif "insert" in op:
                        insert_text = op["insert"]
                        text.insert(pos, insert_text)
                        pos += len(insert_text)
                    elif "delete" in op:
                        delete_count = op["delete"]
                        # pycrdt uses slice deletion, not a delete method
                        del text[pos:pos + delete_count]
            
            state.version += 1
            new_len = len(str(text))
            print(f"[CRDT] Delta applied. New length: {new_len}, version: {state.version}")
            
            # Explicitly schedule save (observer may not fire for local changes)
            self._schedule_save(file_path)
            
            return True
            
        except Exception as e:
            print(f"[CRDT] Error applying delta to {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _handle_change(self, file_path: str, event):
        """Handle Y.Text change events."""
        if file_path not in self.documents:
            return
        
        state = self.documents[file_path]
        
        # Convert event to delta operations
        delta = self._event_to_delta(event)
        
        # Notify observers
        for callback in state.observers:
            try:
                callback(file_path, delta, state.version)
            except Exception as e:
                print(f"[CRDT] Observer error: {e}")
        
        # Schedule debounced save
        self._schedule_save(file_path)
    
    def _event_to_delta(self, event) -> List[dict]:
        """Convert pycrdt event to delta operations."""
        ops = []
        try:
            for change in event.delta:
                if hasattr(change, 'retain') and change.retain:
                    ops.append({"retain": change.retain})
                elif hasattr(change, 'insert') and change.insert:
                    ops.append({"insert": change.insert})
                elif hasattr(change, 'delete') and change.delete:
                    ops.append({"delete": change.delete})
        except Exception as e:
            print(f"[CRDT] Error converting event to delta: {e}")
        return ops
    
    def add_observer(self, file_path: str, callback: Callable[[str, List[dict], int], None]):
        """
        Add observer for document changes.
        
        Callback receives: (file_path, delta_ops, version)
        """
        if file_path in self.documents:
            self.documents[file_path].observers.append(callback)
    
    def remove_observer(self, file_path: str, callback: Callable):
        """Remove an observer."""
        if file_path in self.documents:
            observers = self.documents[file_path].observers
            self.documents[file_path].observers = [
                cb for cb in observers if cb != callback
            ]
    
    def _schedule_save(self, file_path: str):
        """Schedule a debounced save to disk."""
        print(f"[CRDT] _schedule_save called: {file_path}")
        
        if not self._loop:
            print(f"[CRDT] ERROR: No event loop, cannot schedule save for {file_path}")
            return
        
        if file_path not in self.documents:
            print(f"[CRDT] ERROR: Document not in self.documents for save: {file_path}")
            return
        
        state = self.documents[file_path]
        
        # Cancel existing save task
        if state.save_task and not state.save_task.done():
            print(f"[CRDT] Cancelling previous save task for {file_path}")
            state.save_task.cancel()
        
        # Schedule new save
        async def do_save():
            print(f"[CRDT] Save task starting for {file_path} (delay={self.save_delay}s)")
            await asyncio.sleep(self.save_delay)
            print(f"[CRDT] Save task executing for {file_path}")
            await self._save_to_disk(file_path)
        
        state.save_task = self._loop.create_task(do_save())
        print(f"[CRDT] Save task scheduled for {file_path}")
    
    async def _save_to_disk(self, file_path: str):
        """Save document content to disk."""
        if file_path not in self.documents:
            return
        
        content = self.get_content(file_path)
        full_path = self.base_dir / file_path
        
        try:
            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            full_path.write_text(content, encoding='utf-8')
            
            version = self.documents[file_path].version
            print(f"[CRDT] Saved {file_path} (v{version}, {len(content)} chars)")
            
            # Notify observers about save
            for callback in self.documents[file_path].observers:
                try:
                    # Send special "saved" notification
                    callback(file_path, [{"saved": True}], version)
                except:
                    pass
                    
        except Exception as e:
            print(f"[CRDT] Error saving {file_path}: {e}")
    
    async def force_save(self, file_path: str):
        """Force immediate save of a document."""
        if file_path in self.documents:
            state = self.documents[file_path]
            if state.save_task and not state.save_task.done():
                state.save_task.cancel()
            await self._save_to_disk(file_path)
    
    async def save_all(self):
        """Save all documents to disk."""
        for file_path in list(self.documents.keys()):
            await self.force_save(file_path)
    
    def close_document(self, file_path: str):
        """Close a document (remove from memory)."""
        if file_path in self.documents:
            state = self.documents[file_path]
            
            # Cancel pending save
            if state.save_task and not state.save_task.done():
                state.save_task.cancel()
            
            # Force synchronous save before closing
            if self._loop:
                try:
                    self._loop.create_task(self._save_to_disk(file_path))
                except:
                    pass
            
            del self.documents[file_path]
            print(f"[CRDT] Closed document: {file_path}")
    
    def get_open_documents(self) -> List[str]:
        """Get list of currently open document paths."""
        return list(self.documents.keys())


# Global instance (initialized by server)
crdt_manager: Optional[CRDTManager] = None


def init_crdt_manager(base_dir: Path, save_delay: float = 0.5) -> CRDTManager:
    """Initialize the global CRDT manager."""
    global crdt_manager
    crdt_manager = CRDTManager(base_dir, save_delay)
    return crdt_manager


def get_crdt_manager() -> Optional[CRDTManager]:
    """Get the global CRDT manager instance."""
    return crdt_manager
