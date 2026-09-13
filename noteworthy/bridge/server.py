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
        # The room's own description of what changed, kept alive on the
        # session because pycrdt subscriptions are RAII guards.  Used in place
        # of diffing the document before and after: see `_handle_yjs_frame'.
        self._ytext = None
        self._ytext_sub = None
        self._mirror: str = ""
        self._pending_char_ops: list = []
        self._muted_text_deltas = False
        # Ops already sent to Emacs, each tagged with the revision it produced.
        # An edit Emacs wrote before it applied these is not wrong, only stale,
        # and these are what it has to be rebased past.  Emacs echoes the
        # revision it had applied, so which ones it missed is known exactly
        # rather than inferred from a character count.
        self._sent_to_emacs: list = []
        self._rev = 0
        # The file the Yjs tunnel is attached to.  Distinct from
        # `current_file', which follows the buffer Emacs is typing in and can
        # move on while a frame from the previous room is still in flight.
        self._yjs_path: str | None = None

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
                # max_size: the hub broadcasts `preview' frames carrying whole
                # rendered SVG pages, which run past the 1 MiB default.  The
                # limit is enforced on the frame, before the handler that means
                # to discard them, so the client killed its own socket with
                # 1009 and reconnected -- once a second, re-joining every file
                # and restarting the preview watch (which wipes its SVG cache)
                # on each pass.  That was the flicker.
                self._doc_ws = await websockets.connect(doc_url, max_size=None)
                LOG.info("Bridge doc-socket connected for %s", self.user_name)
                connected_at = asyncio.get_event_loop().time()
                # Re-announce the file we are on, so presence survives a reconnect.
                if self.current_file:
                    await self._doc_send({"type": "join", "path": self.current_file})
                await self._doc_receive_loop()
                # Reset the backoff only for a connection that actually held.
                # Resetting on connect alone meant a socket that died at once
                # retried every second forever, and the churn re-joined every
                # file each time -- which is what restarted the preview watch
                # (and so wiped its SVG cache) about once a second.
                if asyncio.get_event_loop().time() - connected_at > 30:
                    delay = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as e:
                LOG.error("Doc socket connect failed: %s: %s", type(e).__name__, e)
            finally:
                # Close it.  Dropping the reference left the socket ESTABLISHED
                # on both ends with nothing owning it -- one per reconnect, and
                # a loop then walks the process into its fd limit.
                if self._doc_ws is not None:
                    try:
                        await self._doc_ws.close()
                    except Exception:
                        pass
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
            leaving = msg.get("file", "")
            # Only if it is the file we are actually attached to.  Emacs sends
            # leave per buffer, and tearing the tunnel down for a buffer that
            # was never the attached one left the buffer you are typing in
            # with no tunnel at all.
            if not leaving or leaving == self._yjs_path:
                await self._detach_yjs()
                # Without this, a cursor packet arriving before the next join
                # is attributed to the file we just left.
                self.current_file = None
            await self._doc_send({"type": "leave", "file": leaving})

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

        # Already attached to this very file: answer with what we hold instead
        # of rebuilding the tunnel.  Emacs rejoins every open buffer on every
        # reconnect, and each rebuild dropped the mirror, cleared `_yjs_synced'
        # and forced a fresh full sync -- so an ordinary reconnect replaced
        # every open buffer and discarded whatever had not been sent yet.
        # Emacs clears its synced flag on any join, so it still needs the sync.
        if (self._yjs_path == path and self._ydoc is not None
                and self._yjs_ws and self._ws_is_open(self._yjs_ws)
                and self._yjs_synced.is_set()):
            LOG.info("Rejoin of %s: tunnel already open, syncing from mirror", path)
            self._pending_char_ops.clear()
            self._sent_to_emacs.clear()
            self._rev += 1
            await self._send_emacs({
                "type": "sync",
                "file": path,
                "content": self._mirror,
                "version": len(self._mirror),
                "rev": self._rev,
            })
            return

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
            # Same limit, same reason: a Yjs update for a large document (or
            # a sync carrying the whole room) is not bounded by 1 MiB either.
            self._yjs_ws = await websockets.connect(url, max_size=None)
            self._yjs_path = path
            self._ydoc = Doc()
            # Keep the subscription alive on the session: pycrdt subscriptions
            # are RAII guards, and a dropped one stops observing silently.
            self._update_sub = self._ydoc.observe(self._on_doc_update)
            self._pending_updates.clear()
            self._ytext = self._ydoc.get("content", type=Text)
            self._mirror = ""
            self._pending_char_ops.clear()
            self._sent_to_emacs.clear()
            self._ytext_sub = self._ytext.observe(self._on_text_delta)
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

    def _on_text_delta(self, event):
        """Record what changed, and keep the mirror in step with it.

        Fires synchronously inside the mutation, whoever made it, so the
        mirror can never drift from the document -- which is the whole point:
        nothing here depends on reading the document before and after an
        `await', and an edit arriving from Emacs mid-frame is simply another
        event in order rather than a difference that has to be explained.

        Deltas from applying Emacs's own edit still move the mirror, but are
        not queued: the buffer they came from does not want them back.
        """
        if not event.delta:
            return
        ops = _delta_to_char_ops(event.delta, self._mirror)
        if not ops:
            return
        if not self._muted_text_deltas:
            self._pending_char_ops.append({"base": len(self._mirror), "ops": ops})
        self._mirror = _apply_char_ops(self._mirror, ops)

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
        self._yjs_path = None
        self._update_sub = None
        self._pending_updates.clear()
        # Deltas recorded against a document we are about to drop describe
        # text the next tunnel will not have.
        self._ytext_sub = None
        self._ytext = None
        self._mirror = ""
        self._pending_char_ops.clear()
        self._sent_to_emacs.clear()
        self._muted_text_deltas = False
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

        The update is applied to our local Y.Doc; what to tell Emacs comes
        from the text observer, which recorded each change as it happened.
        """
        if not self._ydoc or not self.current_file:
            return

        try:
            # Was the mirror already holding the room's state when this frame
            # arrived?  A frame that is still *filling* the mirror is not an
            # edit anybody made, and must not be forwarded as one.
            was_synced = self._yjs_synced.is_set()
            # The file this tunnel is attached to.  `current_file' can already
            # have moved on to another buffer, and tagging a frame with it
            # delivers one file's text into another file's buffer.
            frame_file = self._yjs_path or self.current_file

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

            # Nothing here reads the document before and after.  Those two
            # reads straddle an `await', and an edit arriving from Emacs runs
            # on this same loop in between, so their difference described the
            # peer's change and the user's own as one edit -- which is how a
            # cursor ended up on a peer's the moment both typed at once.  The
            # observer has already recorded each change separately, in order,
            # against the text it was made to.
            pending, self._pending_char_ops = self._pending_char_ops, []

            if pending or not was_synced:
                if not was_synced:
                    # Still filling the mirror after an attach: "" -> partial ->
                    # full.  Diffing those steps and shipping them to Emacs sent
                    # `retain <n>, insert <rest of the document>' for text the
                    # buffer already had, which duplicated it -- a whole doc when
                    # the mirror started empty, its tail when a frame landed
                    # mid-fill.  Reconnecting is exactly when that happens, so
                    # every reconnect corrupted every open buffer.  State the
                    # room's text instead of narrating how we came to hold it.
                    text = self._get_ytext()
                    if text is None:
                        # Sending "" here would erase the buffer.  Leave the
                        # tunnel unsynced so the next frame tries again.
                        LOG.error("Skipping sync for %s: room text unreadable",
                                  frame_file)
                        self._yjs_synced.clear()
                        return
                    # The fill produced observer events too; they describe how
                    # the mirror came to hold this, which is not an edit.
                    self._pending_char_ops.clear()
                    # Emacs is about to hold exactly this, so nothing earlier
                    # is still in flight for it.
                    self._sent_to_emacs.clear()
                    self._mirror = text
                    self._rev += 1
                    await self._send_emacs({
                        "type": "sync",
                        "file": frame_file,
                        "content": text,
                        "version": len(text),
                        "rev": self._rev,
                    })
                else:
                    for entry in pending:
                        self._rev += 1
                        entry["rev"] = self._rev
                        self._sent_to_emacs.append(entry)
                        await self._send_emacs({
                            "type": "delta",
                            "file": frame_file,
                            "ops": entry["ops"],
                            "rev": self._rev,
                            "userId": "__server__",
                        })
                    # Bounded: anything this old is past any delta still in flight.
                    if len(self._sent_to_emacs) > 256:
                        del self._sent_to_emacs[:-256]

        except Exception as e:
            LOG.debug("Yjs frame handling error: %s", e)

    def _get_ytext(self):
        """The room's text, or None if it cannot be read.

        None rather than "": this feeds the full syncs, and an empty string
        returned from a failed read is indistinguishable from an empty
        document -- so a transient error here used to erase whatever the user
        had open and stash it.
        """
        if not self._ydoc:
            return None
        try:
            return str(self._ydoc.get("content", type=Text))
        except Exception as e:
            LOG.error("Could not read the room's text: %s", e)
            return None

    # ------------------------------------------------------------------
    # Emacs delta → Yjs
    # ------------------------------------------------------------------

    def _rebase_ops(self, ops, base, mirror, base_rev=None):
        """OPS rewritten to apply to MIRROR, or None if that cannot be done honestly.

        OPS were composed against a document BASE characters long -- the text
        Emacs held before it applied whatever we sent it since.  Those are
        recorded in `_sent_to_emacs', so the edit can be moved past them the
        way any collaborative editor does it, rather than rejected for being
        a few characters late.
        """
        change = _one_change(ops)
        if change is None:
            return None
        if isinstance(base_rev, int):
            # Emacs told us exactly which revision it had applied, so what it
            # missed is known rather than guessed.
            unseen = [e for e in self._sent_to_emacs
                      if e.get("rev", 0) > base_rev]
        else:
            # An older client with no revision: fall back to the character
            # count it was composed against.
            unseen = [e for e in self._sent_to_emacs if e["base"] >= base]
        if not unseen:
            # A disagreement we have no record of: this is real divergence,
            # not a crossing, and guessing at it is how buffers get spliced.
            return None
        for entry in unseen:
            for concurrent in _changes(entry["ops"]):
                change = _rebase_change(change, concurrent)
                if change is None:
                    return None
        pos, deleted, _ = change
        if pos < 0 or pos + deleted > len(mirror):
            return None
        return _change_to_ops(change)

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
            mirror = self._get_ytext()
            if mirror is None:
                LOG.error("Dropping delta for %s: room text unreadable", path)
                return

            # Emacs says how long its buffer was before the edit.  Positions
            # in a delta only mean what they say if both sides held the same
            # text, and the span check below cannot see a disagreement that an
            # insert-only delta hides -- `retain 0, insert <whole buffer>' has
            # a span of 0 and fits any document, which is how a reconnecting
            # client with a stale buffer appended its copy to the room's.
            base = msg.get("base")
            if isinstance(base, int) and base != len(mirror):
                # Emacs wrote this against the document as it stood before the
                # ops we have since sent it -- the two crossed in flight, which
                # is what happens every time two people type at once.  Refusing
                # here made concurrent editing impossible by construction: the
                # edit bounced, Emacs kept the character anyway, and every
                # later keystroke carried a base that was wrong too, until a
                # full sync threw the whole run away.
                rebased = self._rebase_ops(ops, base, mirror,
                                           msg.get("baseRev"))
                if rebased is None:
                    LOG.warning("Delta for %s (base %d, doc %d) cannot be rebased; syncing",
                                path, base, len(mirror))
                    self._sent_to_emacs.clear()
                    self._rev += 1
                    await self._send_emacs({
                        "type": "sync",
                        "file": path,
                        "content": mirror,
                        "version": len(mirror),
                        "rev": self._rev,
                    })
                    return
                LOG.info("Rebased delta for %s past %d chars of concurrent edits",
                         path, len(mirror) - base)
                ops = rebased

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

            # Applying Emacs's own edit fires the text observer as well, and
            # forwarding that back would hand the buffer its own keystroke.
            self._muted_text_deltas = True
            try:
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
            finally:
                self._muted_text_deltas = False

            # Emacs has demonstrably applied everything up to the revision it
            # named, so nothing older can still be in flight for it.
            ack = msg.get("baseRev")
            if isinstance(ack, int):
                self._sent_to_emacs = [e for e in self._sent_to_emacs
                                       if e.get("rev", 0) > ack]

            # Forward only what this edit produced.  Doc.get_update() would send
            # the entire document on every keystroke.
            updates, self._pending_updates = self._pending_updates, []
            delivered = True
            for update in updates:
                if not (update and self._yjs_ws and self._ws_is_open(self._yjs_ws)):
                    delivered = False
                    continue
                try:
                    await self._yjs_ws.send(create_update_message(update))
                except Exception as e:
                    LOG.error("Failed to forward delta to Yjs: %s", e)
                    delivered = False
                    await self._detach_yjs()
                    break
            if delivered:
                # Tell Emacs this edit is in the room, so it stops adjusting
                # the server's deltas past it.  Without the acknowledgement
                # Emacs would rebase every later inbound delta past an edit
                # the server has long since accounted for -- and acking one
                # that did NOT land would be worse, so this is guarded on
                # delivery rather than on the loop finishing.
                await self._send_emacs({"type": "ack", "file": path})
            else:
                # The edit is in our mirror but never reached the room, so the
                # two have silently diverged and every later delta would be
                # rebased against a document nobody else has.  Say so, and
                # rebuild the tunnel rather than carrying on.
                LOG.error("Edit for %s was applied locally but not delivered; "
                          "rebuilding the tunnel", path)
                await self._send_emacs({
                    "type": "log", "level": "error",
                    "message": ("An edit did not reach the room; reconnecting. "
                                "If text goes missing, it is in the stash."),
                })
                await self._attach_yjs(path)

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
        except websockets.ConnectionClosed as e:
            # Say who hung up and why.  "Doc tunnel closed" on its own turned
            # a reconnect loop into a guessing game.
            LOG.info("Doc tunnel closed: code=%s reason=%r rcvd=%s sent=%s",
                     e.code, e.reason, e.rcvd, e.sent)
        except Exception as e:
            LOG.error("Doc receive error: %s: %s", type(e).__name__, e)

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


def _changes(ops):
    """OPS as [(pos, deleted, inserted_len)] in the coordinates of the text it applies to."""
    out, pos = [], 0
    for op in ops:
        if "retain" in op:
            pos += op["retain"]
        elif "delete" in op:
            out.append([pos, op["delete"], 0])
            pos += op["delete"]
        elif "insert" in op:
            n = len(op["insert"])
            if out and out[-1][0] + out[-1][1] == pos and out[-1][2] == 0:
                out[-1][2] = n          # a delete immediately followed by an insert
            else:
                out.append([pos, 0, n])
    return [tuple(c) for c in out]


def _one_change(ops):
    """(pos, deleted, inserted) when OPS is a single contiguous edit, else None.

    Emacs composes exactly one of these per keystroke -- `after-change' gives
    one region -- so anything else is a shape we should not try to rebase.
    """
    pos, deleted, inserted, started = 0, 0, "", False
    for op in ops:
        if "retain" in op:
            if started:
                return None         # a second region: not one contiguous edit
            pos += op["retain"]
        elif "delete" in op:
            deleted += op["delete"]
            started = True
        elif "insert" in op:
            inserted += op["insert"]
            started = True
    return (pos, deleted, inserted)


def _rebase_change(change, concurrent):
    """CHANGE expressed after CONCURRENT already happened, or None if they overlap.

    The honest cases are the common ones: a peer editing entirely before this
    edit shifts it, entirely after it leaves it alone.  Where the two touch the
    same characters there is no correct rebase, and guessing is how a delta
    ends up spliced into the middle of a word.
    """
    pos, deleted, inserted = change
    cpos, cdel, cins = concurrent
    if cpos + cdel <= pos:
        return (pos + cins - cdel, deleted, inserted)
    if cpos >= pos + deleted:
        return change
    return None


def _change_to_ops(change):
    pos, deleted, inserted = change
    ops = []
    if pos:
        ops.append({"retain": pos})
    if deleted:
        ops.append({"delete": deleted})
    if inserted:
        ops.append({"insert": inserted})
    return ops


def _delta_to_char_ops(delta, old: str) -> list:
    """Translate one pycrdt delta into ops Emacs can apply.

    pycrdt counts retain/delete in UTF-8 bytes; a buffer counts characters.
    """
    raw = old.encode("utf-8")
    pos = 0
    ops = []
    for op in delta:
        if "retain" in op:
            n = int(op["retain"])
            ops.append({"retain": len(raw[pos:pos + n].decode("utf-8", "ignore"))})
            pos += n
        elif "delete" in op:
            n = int(op["delete"])
            ops.append({"delete": len(raw[pos:pos + n].decode("utf-8", "ignore"))})
            pos += n
        elif "insert" in op and isinstance(op["insert"], str):
            ops.append({"insert": op["insert"]})
    return ops


def _apply_char_ops(text: str, ops) -> str:
    """What TEXT becomes once OPS are applied, for checking our own work."""
    out = []
    i = 0
    for op in ops:
        if "retain" in op:
            out.append(text[i:i + op["retain"]]); i += op["retain"]
        elif "delete" in op:
            i += op["delete"]
        elif "insert" in op:
            out.append(op["insert"])
    out.append(text[i:])
    return "".join(out)


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

    # Read and handle on separate tasks.  Handling is serial by design --
    # deltas must be applied in the order they were typed -- but doing it
    # inline in the read loop meant slow work inside one message stalled every
    # message behind it: `_handle_delta' can wait up to five seconds for the
    # tunnel to sync, and every keystroke typed during that wait sat unread in
    # the socket.  The queue keeps the order and lets the socket drain.
    queue: asyncio.Queue = asyncio.Queue()

    async def worker():
        while True:
            item = await queue.get()
            if item is None:
                return
            try:
                await session.handle_emacs_message(item)
            except Exception as e:
                LOG.error("Error handling Emacs message: %s", e)

    worker_task = asyncio.create_task(worker())
    try:
        while True:
            data = await websocket.receive_text()
            queue.put_nowait(data)
    except WebSocketDisconnect:
        LOG.info("Emacs client disconnected: %s", user_name)
    except Exception as e:
        LOG.error("Emacs session error: %s", e)
    finally:
        queue.put_nowait(None)
        try:
            await asyncio.wait_for(worker_task, timeout=5.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            worker_task.cancel()
        except Exception:
            worker_task.cancel()
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
