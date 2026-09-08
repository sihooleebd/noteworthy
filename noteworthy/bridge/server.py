"""
Noteworthy Emacs Bridge Server
==============================
A standalone FastAPI service that provides the legacy /ws/emacs WebSocket endpoint
for Emacs clients (noteworthy-collab.el), while routing:

  - Document content (delta/sync) -> Main server /yjs (via pycrdt-websocket)
  - Chat/preview/presence         -> Main server /ws/doc

The bridge is transparent: Emacs needs zero changes.

Run with:
    uv run uvicorn noteworthy.bridge.server:app --port 8001

Configure in Emacs:
    (setq noteworthy-collab-server-url "ws://localhost:8001/ws/emacs")

Architecture:
                         ┌──────────────────────┐
  Emacs ──/ws/emacs──►   │  Bridge (port 8001)  │
                         │                      │──/yjs──► Main server (8000)
                         │  Translates legacy   │
                         │  delta ↔ Yjs text    │──/ws/doc► Main server (8000)
                         └──────────────────────┘
"""
import asyncio
import json
import logging
import os
import uuid
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pycrdt import (
    Doc,
    Text,
    YMessageType,
    create_sync_message,
    create_update_message,
    handle_sync_message,
)

# ----------------------------------------------------------------- #
# Configuration                                                       #
# ----------------------------------------------------------------- #
# Override when Studio does not live on localhost:8000 (e.g. an SSH tunnel on
# another port, or a bridge running beside a remote Studio).
MAIN_WS_BASE = os.environ.get("NOTEWORTHY_MAIN_WS", "ws://localhost:8000")
YJS_URL = f"{MAIN_WS_BASE}/yjs"
DOC_URL = f"{MAIN_WS_BASE}/ws/doc"
MAIN_HTTP_BASE = MAIN_WS_BASE.replace("ws://", "http://", 1).replace("wss://", "https://", 1)

LOG = logging.getLogger("bridge")
logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

app = FastAPI(title="Noteworthy Emacs Bridge")

# ----------------------------------------------------------------- #
# Per-Emacs-session handler                                           #
# ----------------------------------------------------------------- #

class EmacsSession:
    """
    One session per Emacs WebSocket connection.

    Lifecycle:
      1. Emacs connects  ->  EmacsSession created.
      2. Bridge connects to /ws/doc (for chat + presence).
      3. On 'join(file)': Bridge connects a per-file Yjs tunnel.
      4. Yjs changes arrive as binary frames -> translate to delta -> send to Emacs.
      5. Emacs delta/cursor -> apply to Yjs + forward cursor to /ws/doc.
    """

    def __init__(self, emacs_ws: WebSocket, user_name: str):
        self.emacs_ws = emacs_ws
        self.user_name = user_name
        self.user_id = str(uuid.uuid4())[:8]
        self.color = "#4ECDC4"   # will be overwritten by server welcome

        # Current file the Emacs client is editing
        self.current_file: Optional[str] = None

        # Connection to main /ws/doc
        self._doc_ws: Optional[websockets.WebSocketClientProtocol] = None
        self._doc_task: Optional[asyncio.Task] = None

        # Connection to main /yjs for current file
        self._yjs_ws: Optional[websockets.WebSocketClientProtocol] = None
        self._yjs_task: Optional[asyncio.Task] = None

        # Local Y.Doc mirror for delta ↔ Yjs translation
        self._ydoc: Optional[Doc] = None

        # Incremental updates produced by our own edits, captured from the
        # doc's observer.  Forwarding these instead of Doc.get_update() keeps a
        # keystroke at tens of bytes rather than a full copy of the document.
        self._update_sub = None
        self._pending_updates: list = []
        self._applying_remote = False

        # Set once the freshly attached doc holds the server's state.  Until
        # then its text is empty, and an edit applied against an empty mirror
        # has every retain clamped to 0 and every delete dropped -- which put
        # the text at position 0 instead of the cursor, or silently lost it.
        # That is why corruption always followed the *first* edit after a
        # buffer appeared: attaching is async, applying was not.
        self._yjs_synced = asyncio.Event()

        # Two receive loops share the Emacs socket; Starlette WebSockets are
        # not safe for concurrent sends.
        self._send_lock = asyncio.Lock()

        # Set once the client goes away, so supervisors stop reconnecting.
        self._closing = False

    # ------------------------------------------------------------------
    # Startup / teardown
    # ------------------------------------------------------------------

    async def start(self):
        """Supervise the connection to main /ws/doc."""
        self._doc_task = asyncio.create_task(self._doc_supervisor())

    async def _doc_supervisor(self):
        """Keep /ws/doc connected for as long as the Emacs client is around.

        Without this a single hiccup silently killed chat, presence and cursors
        for the rest of the session: the socket object stayed non-None, so every
        `if self._doc_ws:` guard kept passing and every send went nowhere.
        """
        delay = 1.0
        while not self._closing:
            doc_url = f"{DOC_URL}?name={self.user_name}&id={self.user_id}"
            try:
                self._doc_ws = await websockets.connect(doc_url)
                LOG.info("Bridge doc-socket connected for %s", self.user_name)
                delay = 1.0
                # Re-announce the file we are on, so presence survives a reconnect.
                if self.current_file:
                    await self._doc_send({"type": "join", "path": self.current_file})
                await self._doc_receive_loop()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                LOG.error("Doc socket connect failed: %s", e)
            finally:
                self._doc_ws = None

            if self._closing:
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, 15.0)

    async def _doc_send(self, payload: dict) -> bool:
        """Send to /ws/doc, reporting whether it actually went out."""
        if not self._doc_ws:
            return False
        try:
            await self._doc_ws.send(json.dumps(payload))
            return True
        except Exception as e:
            LOG.warning("Doc send failed (%s): %s", payload.get("type"), e)
            return False

    async def stop(self):
        self._closing = True
        for task in (self._doc_task, self._yjs_task):
            if task and not task.done():
                task.cancel()
        self._update_sub = None
        for ws in (self._doc_ws, self._yjs_ws):
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Emacs → Bridge message handler
    # ------------------------------------------------------------------

    async def handle_emacs_message(self, raw: str):
        try:
            msg = json.loads(raw)
        except Exception:
            LOG.warning("Bad JSON from Emacs: %s", raw)
            return

        mtype = msg.get("type", "")

        if mtype == "join":
            await self._handle_join(msg)

        elif mtype == "leave":
            await self._detach_yjs()
            # Without this, a cursor packet arriving before the next join is
            # attributed to the file we just left.
            self.current_file = None
            await self._doc_send({"type": "leave", "file": msg.get("file", "")})

        elif mtype == "delta":
            await self._handle_delta(msg)

        elif mtype == "cursor":
            await self._handle_cursor(msg)

        elif mtype == "chat":
            # The hub broadcasts chat under "text"; accept either name from
            # Emacs and send both upstream so old and new clients agree.
            body = msg.get("text") or msg.get("message") or ""
            sent = await self._doc_send({
                "type": "chat",
                "text": body,
                "message": body,
                "timestamp": msg.get("timestamp", 0),
            })
            if not sent:
                await self._send_emacs({
                    "type": "log", "level": "warn",
                    "message": "Chat not delivered: doc socket is down",
                })

        elif mtype == "identity":
            self.user_name = msg.get("name", self.user_name)
            await self._doc_send({"type": "identity", "name": self.user_name})

        else:
            LOG.debug("Unhandled Emacs message type: %s", mtype)

    # ------------------------------------------------------------------
    # File join: connect a Yjs tunnel for this file
    # ------------------------------------------------------------------

    async def _handle_join(self, msg: dict):
        path = msg.get("file", "")
        if not path:
            LOG.warning("join with empty path")
            return

        self.current_file = path

        # Tell /ws/doc about presence
        await self._doc_send({"type": "join", "path": path})

        # Connect a Yjs tunnel for this file
        await self._attach_yjs(path)

    async def _attach_yjs(self, path: str):
        """Open a WebSocket to /yjs/<path> and mirror the Y.Doc locally."""
        await self._detach_yjs()
        self._yjs_synced.clear()

        # pycrdt-websocket uses the room name in the URL path
        import urllib.parse
        room = urllib.parse.quote(path, safe="")
        url = f"{YJS_URL}/{room}"

        try:
            self._yjs_ws = await websockets.connect(url)
            self._ydoc = Doc()
            # Keep the subscription alive on the session: pycrdt subscriptions
            # are RAII guards, and a dropped one stops observing silently.
            self._update_sub = self._ydoc.observe(self._on_doc_update)
            self._pending_updates.clear()
            # The server opens with its own SYNC_STEP1; _handle_yjs_frame()
            # answers it with SYNC_STEP2.
            self._yjs_task = asyncio.create_task(self._yjs_receive_loop())
            # Send our OWN sync step-1. The server opens with its step-1, but
            # answering that only pushes our (empty) state back — it never
            # delivers theirs. Without this the mirror stays blank, so no sync
            # reaches Emacs and every delta lands as an independent insertion
            # instead of at the intended offset.
            await self._yjs_send_sync_step1()
            LOG.info("Bridge Yjs tunnel connected for %s", path)
        except Exception as e:
            LOG.error("Failed to connect to /yjs: %s", e)

    async def _reattach_yjs_later(self, path: str, delay: float = 1.0):
        """Rebuild a dropped Yjs tunnel without waiting for a local edit."""
        await asyncio.sleep(delay)
        if self._closing or self.current_file != path or self._yjs_ws:
            return
        LOG.info("Reattaching Yjs tunnel for %s", path)
        await self._attach_yjs(path)

    def _on_doc_update(self, event):
        """Collect updates this session originates, for forwarding to /yjs.

        Updates produced while applying a frame *from* /yjs are skipped -- echoing
        those back would be a loop.
        """
        if self._applying_remote:
            return
        try:
            self._pending_updates.append(bytes(event.update))
        except Exception as e:
            LOG.debug("Could not capture doc update: %s", e)

    async def _detach_yjs(self):
        if self._yjs_task and not self._yjs_task.done():
            self._yjs_task.cancel()
            try:
                await self._yjs_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        self._yjs_task = None
        if self._yjs_ws:
            try:
                await self._yjs_ws.close()
            except Exception:
                pass
            self._yjs_ws = None
        self._update_sub = None
        self._pending_updates.clear()
        self._ydoc = None

    # ------------------------------------------------------------------
    # Yjs WebSocket tunnel
    # ------------------------------------------------------------------

    async def _yjs_send_sync_step1(self):
        """Send Yjs sync step 1 message (request server state)."""
        if not self._yjs_ws or not self._ydoc:
            return
        try:
            # Use the canonical pycrdt Yjs sync-step1 framing.
            msg = create_sync_message(self._ydoc)
            await self._yjs_ws.send(msg)
        except Exception as e:
            LOG.error("Failed to send Yjs sync step 1: %s", e)

    async def _yjs_receive_loop(self):
        """Receive Yjs binary frames and translate to Emacs delta/sync messages."""
        if not self._yjs_ws:
            return
        ws = self._yjs_ws
        file_for_ws = self.current_file
        try:
            async for message in ws:
                if isinstance(message, bytes):
                    await self._handle_yjs_frame(message)
        except asyncio.CancelledError:
            pass
        except websockets.ConnectionClosed as e:
            if ws is self._yjs_ws:
                LOG.info(
                    "Yjs tunnel closed for %s (code=%s, reason=%s)",
                    file_for_ws, e.code, e.reason
                )
            else:
                LOG.debug(
                    "Yjs tunnel rotated for %s (code=%s, reason=%s)",
                    file_for_ws, e.code, e.reason
                )
        except Exception as e:
            LOG.error("Yjs receive error: %s", e)
        finally:
            if ws is self._yjs_ws:
                self._yjs_ws = None
                self._update_sub = None
                self._ydoc = None
                # Previously the tunnel was only rebuilt when the user's own
                # next edit noticed it was gone, so an idle reader silently
                # stopped receiving peers' changes.
                if not self._closing and file_for_ws:
                    asyncio.create_task(self._reattach_yjs_later(file_for_ws))

    async def _handle_yjs_frame(self, data: bytes):
        """
        Parse a Yjs binary frame and send a delta or sync to Emacs.

        We use pycrdt to apply the update to our local Y.Doc mirror and
        then compute the text delta by comparing before/after.
        """
        if not self._ydoc or not self.current_file:
            return

        try:
            old_text = self._get_ytext()

            if not data:
                return

            message_type = data[0]
            if message_type == YMessageType.SYNC:
                # Handles sync-step1/step2/update and applies updates to local doc.
                self._applying_remote = True
                try:
                    reply = handle_sync_message(data[1:], self._ydoc)
                finally:
                    self._applying_remote = False
                # SyncStep2 (1) answers our step-1 and carries the room's
                # state; Update (2) means the room was already live.  Either
                # way the mirror is now real and deltas may be applied.
                if len(data) > 1 and data[1] in (1, 2):
                    self._yjs_synced.set()
                if reply is not None and self._yjs_ws and self._ws_is_open(self._yjs_ws):
                    await self._yjs_ws.send(reply)
            elif message_type == YMessageType.AWARENESS:
                # Awareness is not used for Emacs translation.
                return
            else:
                # Unknown frame type; keep tunnel alive and skip.
                LOG.debug("Ignoring unknown Yjs message type: %s", message_type)
                return

            new_text = self._get_ytext()

            if old_text != new_text:
                # Compute minimal delta
                delta = _compute_delta(old_text, new_text)
                if delta:
                    await self._send_emacs({
                        "type": "delta",
                        "file": self.current_file,
                        "ops": delta,
                        "userId": "__server__",
                    })

                    # Also send a sync on first load (old_text was empty)
                    if not old_text:
                        await self._send_emacs({
                            "type": "sync",
                            "file": self.current_file,
                            "content": new_text,
                            "version": len(new_text),
                        })

        except Exception as e:
            LOG.debug("Yjs frame handling error: %s", e)

    def _get_ytext(self) -> str:
        if not self._ydoc:
            return ""
        try:
            return str(self._ydoc.get("content", type=Text))
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Emacs delta → Yjs
    # ------------------------------------------------------------------

    async def _handle_delta(self, msg: dict):
        """Apply Emacs delta to the Yjs doc via the Yjs tunnel."""
        path = msg.get("file") or self.current_file
        if not path:
            LOG.warning("Delta received without file path")
            return

        # In practice Emacs can emit join events from transient/background buffers.
        # For edits, trust the delta file path as authoritative.
        if self.current_file != path:
            LOG.info("Switching Yjs tunnel to delta file %s (from %s)", path, self.current_file)
            self.current_file = path
            await self._attach_yjs(path)

        if not self._yjs_ws or not self._ydoc or not self._ws_is_open(self._yjs_ws):
            LOG.warning("Delta received but Yjs tunnel is closed for %s; reconnecting", path)
            self.current_file = path
            await self._attach_yjs(path)
            if not self._yjs_ws or not self._ydoc or not self._ws_is_open(self._yjs_ws):
                return

        # Do not touch the doc until it holds the room's state.
        if not self._yjs_synced.is_set():
            try:
                await asyncio.wait_for(self._yjs_synced.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                LOG.error("Delta for %s dropped: Yjs sync did not complete", path)
                await self._send_emacs({
                    "type": "log", "level": "error",
                    "message": ("Bridge is not synced yet; that edit was NOT sent. "
                                "Reopen the file to resync."),
                })
                return

        ops = _validate_ops(msg.get("ops"))
        if ops is None:
            LOG.warning("Malformed ops from Emacs for %s: %r", path, msg.get("ops"))
            await self._send_emacs({
                "type": "log", "level": "error",
                "message": "Bridge rejected a malformed delta; buffer may be out of sync",
            })
            return
        if not ops:
            return

        self._pending_updates.clear()
        try:
            text = self._ydoc.get("content", type=Text)
            # Emacs counts characters; pycrdt indexes Text by UTF-8 BYTES.  Walk
            # the ops in character space against a plain-string mirror and
            # convert each position, or every edit after a non-ASCII character
            # lands at the wrong offset -- silently dropped, misplaced, or (for
            # a delete) wiping the document for everyone in the room.
            mirror = str(text)

            # If the ops reach past the end of the mirror, this session and the
            # room disagree about the document.  Clamping here is what turned a
            # disagreement into data loss, so refuse the edit and hand Emacs the
            # authoritative text to re-align on.
            span = sum(op.get("retain", 0) + op.get("delete", 0) for op in ops)
            if span > len(mirror):
                LOG.error("Delta for %s spans %d chars but the doc holds %d; refusing",
                          path, span, len(mirror))
                await self._send_emacs({
                    "type": "sync",
                    "file": path,
                    "content": mirror,
                    "version": len(mirror),
                })
                return

            char_pos = 0

            with self._ydoc.transaction():
                for op in ops:
                    if "retain" in op:
                        char_pos = min(char_pos + op["retain"], len(mirror))
                    elif "insert" in op:
                        txt = op["insert"]
                        char_pos = min(char_pos, len(mirror))
                        text.insert(_byte_offset(mirror, char_pos), txt)
                        mirror = mirror[:char_pos] + txt + mirror[char_pos:]
                        char_pos += len(txt)
                    elif "delete" in op:
                        d = min(op["delete"], len(mirror) - char_pos)
                        if d > 0:
                            start = _byte_offset(mirror, char_pos)
                            end = _byte_offset(mirror, char_pos + d)
                            del text[start:end]
                            mirror = mirror[:char_pos] + mirror[char_pos + d:]

            # Forward only what this edit produced.  Doc.get_update() would send
            # the entire document on every keystroke.
            updates, self._pending_updates = self._pending_updates, []
            for update in updates:
                if not (update and self._yjs_ws and self._ws_is_open(self._yjs_ws)):
                    continue
                try:
                    await self._yjs_ws.send(create_update_message(update))
                except Exception as e:
                    LOG.error("Failed to forward delta to Yjs: %s", e)
                    await self._detach_yjs()
                    break

        except Exception as e:
            # pycrdt does not roll back a transaction when an exception escapes
            # it, so the mirror may now hold a partial edit that was never
            # forwarded.  Anything computed from it afterwards would be wrong;
            # rebuild the tunnel to resync from the authoritative room.
            LOG.error("Delta apply error (resyncing tunnel): %s", e)
            self._pending_updates.clear()
            await self._attach_yjs(path)

    # ------------------------------------------------------------------
    # Emacs cursor → doc-socket (for other Emacs clients) + Yjs awareness
    # ------------------------------------------------------------------

    async def _handle_cursor(self, msg: dict):
        """Forward cursor message to /ws/doc for other Emacs clients."""
        if not self._doc_ws:
            return
        # An explicit empty string is "present" to dict.get, so ask for the
        # value and fall back on anything falsy.
        sel_start = msg.get("selStart") or {}
        sel_end = msg.get("selEnd") or {}
        line = msg.get("line", 1)
        col = msg.get("col", 1)
        try:
            await self._doc_ws.send(json.dumps({
                "type": "cursor",
                "file": msg.get("file") or self.current_file,
                "line": line,
                "col": col,
                # Canonical selection fields expected by /ws/doc
                "selStartLine": msg.get("selStartLine", sel_start.get("line", line)),
                "selStartCol": msg.get("selStartCol", sel_start.get("col", col)),
                "selEndLine": msg.get("selEndLine", sel_end.get("line", line)),
                "selEndCol": msg.get("selEndCol", sel_end.get("col", col)),
                "name": self.user_name,
                "color": self.color,
                "userId": self.user_id,
            }))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # /ws/doc → Emacs relay
    # ------------------------------------------------------------------

    async def _doc_receive_loop(self):
        """Relay messages from main /ws/doc back to Emacs."""
        if not self._doc_ws:
            return
        try:
            async for raw in self._doc_ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                mtype = msg.get("type", "")

                if mtype == "welcome":
                    # Relay welcome (Emacs expects this format)
                    self.color = msg.get("color", self.color)
                    await self._send_emacs({
                        "type": "welcome",
                        "userId": self.user_id,
                        "color": self.color,
                        "users": msg.get("users", []),
                    })

                elif mtype == "chat":
                    # The hub sends "text"; older clients read "message".
                    body = msg.get("text") or msg.get("message") or ""
                    await self._send_emacs({**msg, "text": body, "message": body})

                elif mtype in ("cursor", "users"):
                    # Forward cursor/users updates from other users
                    await self._send_emacs(msg)

                elif mtype in ("user_joined", "user_left", "user_updated"):
                    # Forward as-is: the client has handlers for these, and the
                    # old log-line rendering (a Python dict repr) meant joins
                    # and leaves never reached them.
                    await self._send_emacs(msg)

                elif mtype == "preview_log":
                    # Typst compile output belongs in the client's log buffer.
                    await self._send_emacs({
                        "type": "log",
                        "level": msg.get("level", "info"),
                        "message": msg.get("message", ""),
                    })

                # Dropped on purpose: `preview` carries rendered SVG pages that
                # only the web editor can display.

        except asyncio.CancelledError:
            pass
        except websockets.ConnectionClosed:
            LOG.info("Doc tunnel closed")
        except Exception as e:
            LOG.error("Doc receive error: %s", e)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _ws_is_open(ws) -> bool:
        """
        websockets compatibility helper.
        - websockets>=16 ClientConnection: `state`
        - older WebSocketClientProtocol: `closed` / `open`
        """
        if ws is None:
            return False

        state = getattr(ws, "state", None)
        if state is not None:
            name = getattr(state, "name", None)
            if name is not None:
                return name == "OPEN"
            try:
                from websockets.protocol import State  # type: ignore
                return state == State.OPEN
            except Exception:
                pass

        closed_attr = getattr(ws, "closed", None)
        if isinstance(closed_attr, bool):
            return not closed_attr
        if callable(closed_attr):
            try:
                return not bool(closed_attr())
            except Exception:
                pass

        open_attr = getattr(ws, "open", None)
        if isinstance(open_attr, bool):
            return open_attr

        # Unknown socket type; assume usable and rely on send exceptions.
        return True

    async def _send_emacs(self, msg: dict):
        # Both receive loops call this; a Starlette WebSocket is not safe for
        # concurrent sends.
        async with self._send_lock:
            try:
                await self.emacs_ws.send_text(json.dumps(msg))
            except Exception as e:
                LOG.debug("Send to Emacs failed: %s", e)


# ----------------------------------------------------------------- #
# Delta computation (text diff → Yjs delta ops)                      #
# ----------------------------------------------------------------- #

def _byte_offset(text: str, char_index: int) -> int:
    """Character index -> UTF-8 byte index, the unit pycrdt's Text uses."""
    return len(text[:char_index].encode("utf-8"))


def _validate_ops(ops) -> Optional[list]:
    """Return ops as a clean list, or None if the payload is unusable.

    Rejecting up front matters: a bad op midway through would raise inside the
    transaction, leaving the mirror partially edited and never forwarded.
    """
    if not isinstance(ops, list):
        return None
    clean = []
    for op in ops:
        if not isinstance(op, dict):
            return None
        if "retain" in op or "delete" in op:
            key = "retain" if "retain" in op else "delete"
            value = op[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                return None
            clean.append({key: value})
        elif "insert" in op:
            if not isinstance(op["insert"], str):
                return None
            clean.append({"insert": op["insert"]})
        else:
            return None
    return clean


def _compute_delta(old: str, new: str) -> list:
    """
    Compute a minimal delta (retain/insert/delete) between old and new text.
    Uses a simple longest common prefix/suffix approach.
    """
    if old == new:
        return []

    # Find common prefix
    prefix = 0
    max_prefix = min(len(old), len(new))
    while prefix < max_prefix and old[prefix] == new[prefix]:
        prefix += 1

    # Find common suffix (avoiding overlap with prefix)
    suffix = 0
    max_suffix = min(len(old) - prefix, len(new) - prefix)
    while suffix < max_suffix and old[-(suffix + 1)] == new[-(suffix + 1)]:
        suffix += 1

    deleted = len(old) - prefix - suffix
    inserted = new[prefix:len(new) - suffix if suffix else len(new)]

    ops = []
    if prefix > 0:
        ops.append({"retain": prefix})
    if deleted > 0:
        ops.append({"delete": deleted})
    if inserted:
        ops.append({"insert": inserted})

    return ops


# ----------------------------------------------------------------- #
# FastAPI WebSocket endpoint                                          #
# ----------------------------------------------------------------- #

@app.websocket("/ws/emacs")
async def emacs_endpoint(websocket: WebSocket):
    """
    Entry point for Emacs noteworthy-collab.el clients.
    Implements the full legacy API without requiring any Emacs changes.
    """
    user_name = websocket.query_params.get("name", "Emacs")
    await websocket.accept()
    LOG.info("Emacs client connected: %s", user_name)

    session = EmacsSession(websocket, user_name)
    await session.start()

    try:
        while True:
            data = await websocket.receive_text()
            await session.handle_emacs_message(data)
    except WebSocketDisconnect:
        LOG.info("Emacs client disconnected: %s", user_name)
    except Exception as e:
        LOG.error("Emacs session error: %s", e)
    finally:
        await session.stop()


# ----------------------------------------------------------------- #
# Health check                                                        #
# ----------------------------------------------------------------- #

@app.get("/health")
async def health():
    return {"status": "ok", "service": "noteworthy-emacs-bridge"}


@app.get("/api/status")
async def api_status_proxy():
    """
    Compatibility endpoint for clients that probe /api/status on the same host
    as /ws/emacs. Falls back to a minimal payload if upstream is unreachable.
    """
    def _fetch():
        with urlopen(f"{MAIN_HTTP_BASE}/api/status", timeout=1.5) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
        return None

    try:
        # urlopen is synchronous: run it off the loop, or every other Emacs
        # session in this process stalls for the duration.
        data = await asyncio.to_thread(_fetch)
        if data is not None:
            data["bridge"] = "ok"
            return data
    except (URLError, TimeoutError, ValueError, OSError) as e:
        LOG.debug("Status proxy fallback: %s", e)

    return {
        "project": "unknown",
        "path": "",
        "preview": {},
        "bridge": "ok",
        "upstream": "unavailable",
    }
