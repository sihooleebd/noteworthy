# Emacs Collaboration Protocol

Wire protocol reference for Emacs integration in collaborative mode.

This documents the current implementation in:

- `noteworthy/bridge/server.py` (`/ws/emacs` bridge)
- `noteworthy/gui/server.py` (`/ws/doc` realtime socket)
- `noteworthy/gui/yjs_provider.py` (`/yjs` binary CRDT transport)

---

## Architecture

The Emacs client does not connect to `/yjs` or `/ws/doc` directly. It connects to the bridge.

```text
Emacs client <--JSON /ws/emacs--> Bridge <--JSON /ws/doc--> Main GUI server
                                     \
                                      \--Binary /yjs/<room>--> Main GUI server
```

### Transport summary

| Channel | Direction | Payload format | Purpose |
| --- | --- | --- | --- |
| `/ws/emacs` | Emacs <-> Bridge | JSON text | Legacy Emacs protocol (`join`, `delta`, `cursor`, etc.) |
| `/ws/doc` | Bridge <-> GUI server | JSON text | Presence, chat, cursor fanout, preview notifications |
| `/yjs/<room>` | Bridge <-> GUI server | Binary frames | CRDT document synchronization |

---

## Session Lifecycle

1. Emacs opens `ws://<bridge-host>:8001/ws/emacs?name=<display-name>`.
2. Bridge creates an `EmacsSession` and opens `/ws/doc?name=<name>&id=<bridge_user_id>`.
3. Emacs sends `{"type":"join","file":"..."}`.
4. Bridge:
   - sends `/ws/doc` join (`{"type":"join","path":"..."}`),
   - opens `/yjs/<urlencoded-file-path>`,
   - sends initial Yjs sync step-1.
5. Ongoing:
   - Emacs deltas -> Bridge applies to local Y.Doc mirror -> forwards update to `/yjs`.
   - Yjs updates -> Bridge computes text delta -> sends legacy `delta` (and initial `sync`) to Emacs.
   - Cursor/chat/identity pass through `/ws/doc`.

---

## `/ws/emacs` Protocol (Legacy Emacs Side)

### Emacs -> Bridge Messages

### `join`

```json
{"type":"join","file":"content/1/1.typ"}
```

- `file` (required): project-relative path.

### `leave`

```json
{"type":"leave","file":"content/1/1.typ"}
```

- Bridge detaches current `/yjs` tunnel.
- Bridge also forwards `{"type":"leave","file":...}` to `/ws/doc` (currently ignored by server).

### `delta`

```json
{
  "type":"delta",
  "file":"content/1/1.typ",
  "ops":[
    {"retain":42},
    {"delete":3},
    {"insert":"new text"}
  ]
}
```

- `ops` follows retain/insert/delete operation list.
- Bridge applies ops to local Y.Doc `content` text with bounds clamping.
- Then bridge sends resulting CRDT update bytes to `/yjs`.

### `cursor`

```json
{
  "type":"cursor",
  "file":"content/1/1.typ",
  "line":10,
  "col":4,
  "selStart":{"line":10,"col":4},
  "selEnd":{"line":10,"col":9}
}
```

- Forwarded to `/ws/doc` with user identity fields added by bridge.

### `chat`

```json
{"type":"chat","message":"hello","timestamp":1735689600000}
```

- Bridge forwards `message` as `/ws/doc` chat payload.

### `identity`

```json
{"type":"identity","name":"Alice"}
```

- Updates bridge-side display name and forwards to `/ws/doc`.

---

### Bridge -> Emacs Messages

### `welcome`

```json
{
  "type":"welcome",
  "userId":"a1b2c3d4",
  "color":"#4ECDC4",
  "users":[{"id":"...","name":"...","color":"...","file":"...","token":"..."}]
}
```

### `delta`

```json
{
  "type":"delta",
  "file":"content/1/1.typ",
  "ops":[{"retain":10},{"insert":"x"}],
  "userId":"__server__"
}
```

- Emitted when Yjs update changed text content.

### `sync`

```json
{
  "type":"sync",
  "file":"content/1/1.typ",
  "content":"full file text",
  "version":1234
}
```

- Emitted on initial load when old text was empty and first Yjs update arrives.
- `version` is currently `len(content)` (not a CRDT clock).

### `chat`, `cursor`

- Relayed from `/ws/doc` as-is.

### `log`

```json
{
  "type":"log",
  "level":"info",
  "message":"[Presence] {...}"
}
```

- Presence events (`user_joined`, `user_left`, `user_updated`) are currently translated to log lines, not a structured `users` diff packet.

---

## `/ws/doc` Protocol (Bridge <-> Main Server)

Connection:

```text
ws://localhost:8000/ws/doc?name=<name>&id=<client-id>&token=<optional-token>
```

### Bridge -> `/ws/doc`

- `join`: `{"type":"join","path":"<file>"}` (or `file`)
- `identity`: `{"type":"identity","name":"<display-name>"}`
- `chat`: `{"type":"chat","message":"...","timestamp":...}` (`text` also accepted by server)
- `cursor`: bridge sends a payload that includes `file/line/col/...`

Server behavior:

- For `cursor`, server rebuilds a canonical payload and broadcasts to peers:
  - sets authoritative `userId`, `name`, `token`,
  - keeps `file`,
  - parses numeric cursor/selection fields with defaults.

### `/ws/doc` -> Bridge

- `welcome`
- `user_joined`
- `user_left`
- `user_updated`
- `chat`
- `cursor`
- `preview`, `diagnostics` (bridge currently drops these)

---

## Yjs Translation Details

### Join / Handshake

On file join:

1. Bridge opens `ws://localhost:8000/yjs/<urlencoded-room>`.
2. Bridge creates local `Doc()` mirror.
3. Bridge sends its own Yjs sync step-1 (`create_sync_message`) and answers
   the server's step-1 with step-2. Both directions are required: answering
   the server's step-1 alone pushes the bridge's state without ever
   receiving the server's, leaving the mirror empty.

### Yjs -> Emacs

For each binary frame:

1. Read old text from local Y.Doc (`content`).
2. Apply frame with `self._ydoc.apply_update(data)`.
3. Read new text.
4. If changed:
   - compute minimal delta by longest common prefix/suffix,
   - send legacy `delta` to Emacs,
   - if old text was empty, also send full `sync`.

### Emacs -> Yjs

For incoming legacy `delta` ops:

1. Apply `retain/insert/delete` to local Y.Doc `content` inside transaction.
2. Clamp operations to current document bounds.
3. Produce update bytes with `self._ydoc.get_update()`.
4. Send update bytes to `/yjs`.

---

## Important Compatibility Notes

These are current behavior details that matter for Emacs agent work:

1. Selection field naming (resolved):
   - Main `/ws/doc` canonical cursor expects `selStartLine`, `selStartCol`, `selEndLine`, `selEndCol`.
   - The bridge sends those, falling back to the legacy `selStart`/`selEnd` objects
     when a client only supplies those. `noteworthy-collab.el` sends both.

2. Presence relay shape:
   - Bridge does not currently emit structured `users` updates for `user_joined/left/updated`.
   - It emits `type:"log"` messages containing presence JSON string.

3. `leave` on `/ws/doc`:
   - Bridge forwards it, but server currently has no `leave` branch in `/ws/doc` handler.

4. Version semantics:
   - `sync.version` is content length, not a CRDT revision number.

5. Room naming:
   - `/yjs` room is URL-encoded project-relative file path.

---

## Suggested Packet Shapes for New Emacs Agent

For best compatibility with current server behavior:

- Cursor payload should include explicit selection line/col fields:

```json
{
  "type":"cursor",
  "file":"content/1/1.typ",
  "line":10,
  "col":4,
  "selStartLine":10,
  "selStartCol":4,
  "selEndLine":10,
  "selEndCol":9
}
```

- Delta ops should remain retain/insert/delete arrays.
- Keep file paths project-relative and consistent across `join`, `delta`, and `cursor`.

---

## Source Pointers

- Bridge protocol and translation: `noteworthy/bridge/server.py`
- Main doc-socket endpoint: `noteworthy/gui/server.py` (`/ws/doc`)
- Presence model and broadcasts: `noteworthy/gui/document_hub.py`
- Yjs websocket provider: `noteworthy/gui/yjs_provider.py`
