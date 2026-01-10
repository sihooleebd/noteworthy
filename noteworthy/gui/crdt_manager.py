"""
CRDT Manager for Noteworthy Real-time Collaboration.

ADAPTER LAYER:
This bridges the custom Emacs JSON delta protocol to the standard YjsProvider.
It no longer manages document persistence or ownership - that is delegated to YjsProvider.
"""
import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path

from pycrdt import Doc, Text
from .yjs_provider import yjs_provider, NoteworthyRoom


class CRDTManager:
    """
    Adapter that translates between Emacs Delta protocol and YjsProvider.
    """
    
    def __init__(self):
        self.observers: Dict[str, List[Callable]] = {}
        # We don't manage documents or loop anymore, YjsProvider does that.
    
    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """No-op in new architecture (handled by YjsProvider)."""
        pass
    
    async def get_or_create_room(self, file_path: str) -> NoteworthyRoom:
        """
        Get the Yjs room for a file.
        Ensures the room is initialized and loaded from disk.
        """
        room = yjs_provider.get_room(file_path)
        # Ensure content is loaded from disk
        await room.initialize()
        return room

    async def get_content(self, file_path: str) -> str:
        """Get current content of a document."""
        room = await self.get_or_create_room(file_path)
        text = room.ydoc.get("content", type=Text)
        return str(text)
    
    async def get_version(self, file_path: str) -> int:
        """
        Get 'version' of a document.
        Yjs doesn't have a simple integer version. 
        We'll use content length or a hash as a proxy, or 0.
        Emacs client uses this for sanity checks.
        """
        content = await self.get_content(file_path)
        return len(content)
    
    async def apply_delta(self, file_path: str, ops: List[dict], source_user: str = None) -> bool:
        """
        Apply delta operations from an Emacs client to the Yjs doc.
        """
        print(f"[CRDT] apply_delta called: file={file_path}, ops={ops}")
        
        try:
            room = await self.get_or_create_room(file_path)
            text = room.ydoc.get("content", type=Text)
            
            # We need to calculate current position based on character length
            # because pycrdt works on characters.
            pos = 0
            
            with room.ydoc.transaction():
                for op in ops:
                    if "retain" in op:
                        pos += op["retain"]
                    elif "insert" in op:
                        insert_text = op["insert"]
                        text.insert(pos, insert_text)
                        pos += len(insert_text)
                    elif "delete" in op:
                        delete_count = op["delete"]
                        del text[pos:pos + delete_count]
            
            return True
            
        except Exception as e:
            print(f"[CRDT] Error applying delta to {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def add_observer(self, file_path: str, callback: Callable[[str, List[dict], int], None]):
        """
        Add observer for document changes.
        """
        if file_path not in self.observers:
            self.observers[file_path] = []
            
            # If this is the first observer, we need to attach to the Yjs doc
            # But wait, we need async context to get the room usually.
            # This is tricky because add_observer is synchronous in the calling code.
            # We'll rely on the fact that the room should exist if we are adding an observer.
            
            # We'll attach a listener to the YjsProvider room if it exists.
            room = yjs_provider.get_room(file_path)
            
            # Define the Yjs observer wrapper
            def yjs_observer(event):
                 self._handle_yjs_change(file_path, event)
            
            # We need to store this wrapper to remove it later? 
            # For now, let's just add it.
            # Note: access to ydoc content needs to be safe.
            text = room.ydoc.get("content", type=Text)
            text.observe(yjs_observer)
            
            # Store the wrapper so we don't add it multiple times?
            # Simplified: we assume one observer setup per file for the transform layer
        
        self.observers[file_path].append(callback)
    
    def remove_observer(self, file_path: str, callback: Callable):
        """Remove an observer."""
        if file_path in self.observers:
            self.observers[file_path] = [
                cb for cb in self.observers[file_path] if cb != callback
            ]

    def _handle_yjs_change(self, file_path: str, event):
        """Handle Y.Text change events and notify Emacs observers."""
        if file_path not in self.observers:
            return
        
        # Convert Yjs event to Delta
        delta = []
        try:
            for change in event.delta:
                if hasattr(change, 'retain') and change.retain:
                    delta.append({"retain": change.retain})
                elif hasattr(change, 'insert') and change.insert:
                    delta.append({"insert": change.insert})
                elif hasattr(change, 'delete') and change.delete:
                    delta.append({"delete": change.delete})
        except Exception as e:
            print(f"[CRDT] Error converting event: {e}")
            return

        if delta:
            print(f"[CRDT] Yjs change detected on {file_path}: {delta}")
        else:
            # This happens for attribute changes or other non-text changes we don't care about
            return

        # Notify observers
        # Note: This runs in the thread/context of the Yjs update.
        # The observers in server.py are designed to be async wrappers.
        version = 0 # Dummy version
        for callback in self.observers[file_path]:
            try:
                callback(file_path, delta, version)
            except Exception as e:
                print(f"[CRDT] Observer error: {e}")

    # Legacy methods for compatibility
    def get_open_documents(self) -> List[str]:
        return list(yjs_provider.rooms.keys())

    def close_document(self, file_path: str):
        pass # Yjs provider manages lifecycle or keeps them open
        

# Global instance
crdt_manager = CRDTManager()

def init_crdt_manager(base_dir: Path, save_delay: float = 0.5) -> CRDTManager:
    return crdt_manager

def get_crdt_manager() -> Optional[CRDTManager]:
    return crdt_manager
