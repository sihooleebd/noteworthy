"""
Real-time Collaboration Manager for Noteworthy GUI
Handles multi-user sessions, cursor positions, and edit synchronization.
"""
import asyncio
import json
import uuid
from typing import Dict, Set, Optional
from dataclasses import dataclass, field
from fastapi import WebSocket

# User colors for cursor decorations
USER_COLORS = [
    "#FF6B6B",  # Red
    "#4ECDC4",  # Teal
    "#FFE66D",  # Yellow
    "#95E1D3",  # Mint
    "#F38181",  # Coral
    "#AA96DA",  # Purple
    "#FCBAD3",  # Pink
    "#A8D8EA",  # Sky
]


@dataclass
class User:
    """Represents a connected user."""
    id: str
    name: str
    color: str
    websocket: WebSocket
    active_file: Optional[str] = None
    cursor_line: int = 1
    cursor_column: int = 1
    selection_start: Optional[dict] = None
    selection_end: Optional[dict] = None


class CollaborationManager:
    """Manages global collaboration state."""
    
    def __init__(self):
        self.users: Dict[str, User] = {}  # user_id -> User
        self.color_index: int = 0
        self._lock = asyncio.Lock()
    
    def get_next_color(self) -> str:
        color = USER_COLORS[self.color_index % len(USER_COLORS)]
        self.color_index += 1
        return color

    async def connect(self, websocket: WebSocket, user_name: str) -> User:
        """Register a new global connection."""
        async with self._lock:
            user_id = str(uuid.uuid4())[:8]
            color = self.get_next_color()
            
            user = User(
                id=user_id,
                name=user_name or f"User {len(self.users) + 1}",
                color=color,
                websocket=websocket
            )
            self.users[user_id] = user
            
            # Notify everyone about new user (global list update)
            await self.broadcast_global({
                "type": "user_joined",
                "user": {
                    "id": user_id,
                    "name": user.name,
                    "color": user.color
                }
            }, exclude=user_id)
            
            return user
    
    async def disconnect(self, user_id: str):
        """Remove a user."""
        async with self._lock:
            if user_id in self.users:
                user = self.users[user_id]
                del self.users[user_id]
                
                # Notify everyone
                await self.broadcast_global({
                    "type": "user_left",
                    "userId": user_id
                })

    async def set_active_file(self, user_id: str, file_path: str):
        """Update user's active file focus."""
        if user_id not in self.users:
            return
            
        user = self.users[user_id]
        user.active_file = file_path
        
        # We might want to notify others on this file that someone joined?
        # For now, we trust cursor updates to reveal presence, 
        # OR we could send a specific "file_focused" event if needed.
        # But global list is what's requested.

    async def update_cursor(self, user_id: str, 
                           line: int, column: int,
                           selection_start: dict = None,
                           selection_end: dict = None):
        """Update cursor and broadcast to users in SAME file."""
        if user_id not in self.users:
            return
        
        user = self.users[user_id]
        user.cursor_line = line
        user.cursor_column = column
        user.selection_start = selection_start
        user.selection_end = selection_end
        
        if not user.active_file:
            return

        # Broadcast only to users in same file
        await self.broadcast_file(user.active_file, {
            "type": "cursor",
            "userId": user_id,
            "name": user.name,
            "color": user.color,
            "line": line,
            "column": column,
            "selectionStart": selection_start,
            "selectionEnd": selection_end
        }, exclude=user_id)
    
    async def update_user(self, user_id: str, name: str):
        """Update identity globally."""
        if user_id not in self.users:
            return
            
        user = self.users[user_id]
        user.name = name
        
        await self.broadcast_global({
            "type": "user_updated",
            "user": {
                "id": user.id,
                "name": user.name,
                "color": user.color
            }
        })

    async def broadcast_edit(self, user_id: str, changes: list):
        if user_id not in self.users:
            return
            
        user = self.users[user_id]
        if not user.active_file:
            return

        await self.broadcast_file(user.active_file, {
            "type": "edit",
            "userId": user_id,
            "changes": changes
        }, exclude=user_id)
    
    def get_global_users(self) -> list:
        """Get all connected users."""
        return [
            {
                "id": u.id,
                "name": u.name,
                "color": u.color,
                "file": u.active_file
            }
            for u in self.users.values()
        ]
    
    async def broadcast_global(self, message: dict, exclude: str = None):
        """Broadcast to ALL users."""
        msg_json = json.dumps(message)
        disconnected = []
        
        for user_id, user in self.users.items():
            if user_id == exclude:
                continue
            try:
                await user.websocket.send_text(msg_json)
            except Exception:
                disconnected.append(user_id)
        
        # Cleanup is handled by disconnect() usually called by route handler,
        # but we track here just in case.
        
    async def broadcast_file(self, file_path: str, message: dict, exclude: str = None):
        """Broadcast only to users with active_file == file_path."""
        msg_json = json.dumps(message)
        
        for user_id, user in self.users.items():
            if user_id == exclude:
                continue
            if user.active_file == file_path:
                try:
                    await user.websocket.send_text(msg_json)
                except Exception:
                    pass


# Global instance
collab_manager = CollaborationManager()
