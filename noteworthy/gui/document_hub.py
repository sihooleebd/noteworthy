"""
DocumentHub - Real-time Hub for NON-YJS functionality.

Strict packet separation:
  /yjs  -> Document content sync + cursors  (handled entirely by yjs_provider + y-monaco)
  /ws/doc -> Chat, Preview, File Presence   (handled here)

This hub does NOT touch document content, cursors, or Yjs.
"""
import asyncio
import json
import uuid
import subprocess
import tempfile
import os
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from fastapi import WebSocket
from pathlib import Path

from ..config import BASE_DIR, RENDERER_FILE


# User colors for avatars
USER_COLORS = [
    "#FF6B6B", "#4ECDC4", "#FFE66D", "#95E1D3",
    "#F38181", "#AA96DA", "#FCBAD3", "#A8D8EA"
]

@dataclass
class User:
    """Connected user (doc-socket only)."""
    id: str
    name: str = "Anonymous"
    color: str = "#FF6B6B"
    websocket: WebSocket = None
    current_file: Optional[str] = None
    token: Optional[str] = None   # stable client token (from localStorage)


class DocumentHub:
    """
    Hub for Chat / Preview / File Presence.
    Does NOT manage document content or cursors (those are Yjs concerns).
    """

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.color_index = 0
        self._lock = asyncio.Lock()
        self.preview_manager = None

    def _get_color(self) -> str:
        color = USER_COLORS[self.color_index % len(USER_COLORS)]
        self.color_index += 1
        return color

    async def connect(self, websocket: WebSocket, name: str = "Anonymous", user_id: str = None, token: str = None) -> User:
        """Register a new user connection."""
        if not user_id:
            user_id = str(uuid.uuid4())[:8]
        elif user_id in self.users and self.users[user_id].websocket != websocket:
            # Guard against duplicated-tab/session ID collisions:
            # never let a new socket overwrite an existing user's connection.
            while user_id in self.users:
                user_id = str(uuid.uuid4())[:8]

        if user_id in self.users:
            user = self.users[user_id]
            user.websocket = websocket
            user.name = name
            if token:
                user.token = token
            await self._broadcast({
                "type": "user_updated",
                "user": {
                    "id": user_id,
                    "name": name,
                    "color": user.color,
                    "file": user.current_file,
                    "token": user.token
                }
            })
        else:
            user = User(
                id=user_id,
                name=name,
                color=self._get_color(),
                websocket=websocket,
                token=token,
            )
            self.users[user_id] = user
            await self._broadcast({
                "type": "user_joined",
                "user": {
                    "id": user_id,
                    "name": name,
                    "color": user.color,
                    "file": user.current_file,
                    "token": user.token
                }
            }, exclude=user_id)

        return user

    async def disconnect(self, user_id: str, websocket: WebSocket = None):
        """Remove a user."""
        if user_id not in self.users:
            return
        user = self.users[user_id]
        if websocket and user.websocket != websocket:
            return
        try:
            if user.current_file and user.current_file.endswith('.typ') and self.preview_manager:
                self.preview_manager.stop_watch(user.current_file)
        except Exception as e:
            print(f"[Hub] Error stopping watch during disconnect: {e}")

        del self.users[user_id]
        await self._broadcast({"type": "user_left", "userId": user_id})

    async def join_file(self, user_id: str, path: str):
        """User joins a file (for preview triggering)."""
        if user_id not in self.users:
            return

        user = self.users[user_id]

        try:
            if user.current_file and user.current_file.endswith('.typ') and self.preview_manager:
                self.preview_manager.stop_watch(user.current_file)
        except Exception as e:
            print(f"[Hub] Error stopping watch: {e}")

        user.current_file = path

        if path.endswith('.typ') and self.preview_manager:
            try:
                self.preview_manager.start_watch(path)
                # Send current cached preview state to joining user
                for _ in range(10):
                    await asyncio.sleep(0.2)
                    status = self.preview_manager.get_status(path)
                    if status['pages']:
                        updates = []
                        for page in status['pages']:
                            svg_bytes = self.preview_manager.get_image(path, page)
                            if svg_bytes:
                                updates.append({'page': page, 'svg': svg_bytes.decode('utf-8')})
                        if updates:
                            await user.websocket.send_text(json.dumps({
                                "type": "preview", "updates": updates
                            }))
                            break
            except Exception as e:
                print(f"[Hub] Error starting watch: {e}")

        # Broadcast the file change to ALL connected clients so their avatar
        # lists update immediately (not just users already on this file).
        await self._broadcast({
            "type": "user_updated",
            "user": {"id": user.id, "name": user.name, "color": user.color,
                     "file": path, "token": user.token},
        }, exclude=user_id)

    async def on_preview_update(self, updates: list, source_path: str):
        """Broadcast preview updates to users on this file."""
        await self._broadcast_to_file(source_path, {
            "type": "preview", "updates": updates
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
            "timestamp": timestamp,
        })

    async def update_identity(self, user_id: str, name: str):
        """Update user's display name."""
        if user_id not in self.users:
            return
        self.users[user_id].name = name
        u = self.users[user_id]
        await self._broadcast({
            "type": "user_updated",
            "user": {
                "id": user_id,
                "name": name,
                "color": u.color,
                "file": u.current_file,
                "token": u.token
            }
        })

    def get_users(self) -> List[dict]:
        return [
            {"id": u.id, "name": u.name, "color": u.color, "file": u.current_file, "token": u.token}
            for u in self.users.values()
        ]

    def get_users_on_file(self, path: str) -> List[dict]:
        return [
            {"id": u.id, "name": u.name, "color": u.color}
            for u in self.users.values()
            if u.current_file == path
        ]

    async def _broadcast(self, message: dict, exclude: str = None):
        msg_json = json.dumps(message)
        for user_id, user in list(self.users.items()):
            if user_id == exclude:
                continue
            try:
                await user.websocket.send_text(msg_json)
            except:
                pass

    async def _broadcast_to_file(self, path: str, message: dict, exclude: str = None):
        msg_json = json.dumps(message)
        for user_id, user in list(self.users.items()):
            if user_id == exclude or user.current_file != path:
                continue
            try:
                await user.websocket.send_text(msg_json)
            except:
                pass


# Global instance
document_hub = DocumentHub()
