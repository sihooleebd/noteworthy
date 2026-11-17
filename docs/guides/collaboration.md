# Collaboration

Real-time collaborative editing with Noteworthy Studio.

## Overview

Noteworthy Studio supports real-time collaboration, allowing multiple users to edit the same document simultaneously.

### Features

| Feature                    | Description                          |
| -------------------------- | ------------------------------------ |
| **Shared cursors**         | Real-time cursor tracking            |
| **Selection Highlighting** | **Google Docs-style** text selection |
| **Preview Navigation**     | Click preview to jump to source      |
| **Global Chat**            | Built-in messaging                   |
| **Conflict-Free**          | Yjs CRDT — concurrent edits merge    |


---

## Working alone

Studio is Syncworthy with a Noteworthy plugin (see the
[Studio stack](../architecture/gui-stack.md)). There is no separate solo mode
any more: the old `-nc` flag and the `gui_solo` GUI are gone. Alone on the
default loopback bind, with no tokens, you are the only user; chat and the user
list simply stay empty.

Tinymist preview is available either way: the `/api/tinymist/*` endpoints serve
the full-document preview next to the incremental SVG preview.

---

## Starting a Session

### Local Network

For users on the same network:

```bash
# Start the server, listening on every interface
noteworthy -g --bind 0.0.0.0
```

Share `http://<your-ip>:8000` with collaborators.

> [!IMPORTANT]
> `--bind` is required here. Studio defaults to `127.0.0.1`, which accepts
> connections only from the machine it runs on, so plain `noteworthy -g` is
> unreachable from anywhere else on the network.

> [!IMPORTANT]
> On a non-loopback bind Syncworthy **refuses to start without auth tokens**.
> Set `SYNCWORTHY_EDIT_TOKEN` (and optionally `SYNCWORTHY_VIEW_TOKEN` for
> read-only guests) before starting, or pass `--insecure-open` to serve with no
> authentication at all. See [Access control](#access-control).

### Remote via ngrok

For internet collaboration:

1. **Install ngrok**: https://ngrok.com/download

2. **Start Noteworthy** (the default loopback bind is fine — ngrok connects
   from the same machine):
   ```bash
   noteworthy -g
   ```

3. **Expose the port**:
   ```bash
   ngrok http 8000
   ```

4. **Share the URL**: Copy the HTTPS URL (e.g., `https://xxxx.ngrok-free.app`)

> [!IMPORTANT]
> Collaborators access the **exact same session** as you. All edits are synchronized.

---

## Collaboration Features

### Shared Cursors

When multiple users are connected:
- Each user has a unique color
- Cursor positions are shown in real-time
- Click on a user's avatar to jump to their location

### Selection Highlighting

Collaborate like you're in Google Docs:
- **See what others select**: Text selections are broadcast in real-time
- **Color-coded**: Selections match the user's assigned color
- **Conflict awareness**: Helps avoid editing same sentence simultaneously

### Preview Source Navigation

Bidirectional navigation makes editing easier:
- **Click-to-Source**: Click any text in the preview to jump to that location in the editor
- **Highlight Animation**: The target line briefly flashes gold to orient you
- **Contextual Matching**: Uses smart text matching to find the right location even if source maps are approximate

### Setting Your Name

1. Click the **Settings** icon
2. Enter your display name
3. Your name appears to other collaborators

### Chat

The built-in chat allows team communication:

1. Click the **Chat** toggle (bottom right)
2. Type messages
3. Press Enter to send

An unread indicator appears when new messages arrive.

---

## File Synchronization

### How It Works

Document content is synchronized entirely by Yjs CRDT. `pycrdt` and
`pycrdt-websocket` are required dependencies, so there is no fallback path and
no last-write-wins mode:

1. **Content** travels over the binary `/yjs` WebSocket, one room per file. Each
   client holds a `Y.Doc` bound to its Monaco model.
2. **Everything else** — presence, chat, cursors, preview and build events —
   travels over the separate JSON `/ws/doc` socket, managed by `DocumentHub`.

### Conflict Prevention

- **Conflict-free merges**: Concurrent edits to the same file converge by
  construction; there is no save lock and no canonical server version to lose to
- **Per-file rooms**: Each open file syncs independently
- **Instant local echo**: Edits apply locally and propagate as CRDT updates
- **Selection Awareness**: Use selection highlighting to avoid stepping on teammates' toes

---

## Access control

Syncworthy authenticates with project tokens, each with a role:

| Role   | Can                                                                   |
| ------ | --------------------------------------------------------------------- |
| `edit` | everything                                                            |
| `view` | read documents, see presence, chat; its edits are dropped, writes are refused |

```bash
export SYNCWORTHY_EDIT_TOKEN=...      # also ..._FILE to read it from a file
export SYNCWORTHY_VIEW_TOKEN=...
noteworthy -g --bind 0.0.0.0
```

More tokens (named, from an environment variable or a file; never inline) go in
a `syncworthy.toml` in the project:

```toml
[auth]
tokens = [
  { name = "me",    token_env  = "SYNCWORTHY_TOKEN_ME", role = "edit" },
  { name = "class", token_file = "/run/secrets/class",  role = "view" },
]
```

A collaborator opens `http://<host>:8000/?token=<token>` once; the server then
sets an HttpOnly cookie. Scripts send `Authorization: Bearer <token>`.
The `/mcp` endpoint keeps its own bearer token (`NOTEWORTHY_MCP_TOKEN`).

`--insecure-open` serves with no tokens on a non-loopback address. Use it only
on a network you trust (a Tailscale tailnet, say).

---

## Editing from Emacs

Emacs joins a Studio session through
[**noteworthy-workspace**](https://github.com/R0K0R/noteworthy-workspace), the
Noteworthy front end of
[emacs-collab.el](https://github.com/R0K0R/emacs-collab.el), with
[`syncworthy_bridge`](https://github.com/R0K0R/syncworthy_bridge) as the bridge
program (it must be on `PATH`, or set `noteworthy-workspace-bridge-command`).

```elisp
(require 'noteworthy-workspace)
M-x noteworthy-workspace-connect RET http://host:8000 RET <token>
```

The bridge mirrors the project into a local directory you choose; buffers there
sync live through the server's `/yjs` rooms, and Emacs users appear in the web UI
with cursors, selections and chat like anyone else. For a server that wants a
token, put a line in auth-source (`machine <host> port <port> login token password
<secret>`). A view-only token mirrors files and shows peers but cannot edit.

The old setup (`uvicorn noteworthy.bridge.server:app`, the `/ws/emacs`
endpoint and `noteworthy-collab.el`) is retired and no longer in this
repository. The wire protocol is emacs-collab's
[PROTOCOL.md](https://github.com/R0K0R/emacs-collab.el/blob/master/PROTOCOL.md);
see the [Emacs protocol page](../reference/emacs-protocol.md).

---

## Best Practices

1. **Communicate**: Use chat to coordinate edits
2. **Divide work**: Each person works on different pages
3. **Save often**: Changes sync on save
4. **Use preview**: Verify changes compile correctly

---

## Troubleshooting

### Connection Lost

If WebSocket disconnects:
- Refresh the page
- Check network connectivity
- Verify server is still running

### Edits Not Syncing

1. Check the connection indicator (top right)
2. Ensure file is saved (`Ctrl+S`)
3. Refresh both browsers

### Multiple Tabs

Each browser tab is a separate session. Avoid editing the same file in multiple tabs.

---

## Security Notes

Studio has token authentication (see [Access control](#access-control)). The
default bind is loopback with no tokens, which is only reachable from your own
machine.

> [!WARNING]
> With `--insecure-open` on a non-loopback address, anyone who can reach the URL can:
> - View all files
> - Edit any content
> - See chat messages

For sensitive projects:
- Use tokens, and give guests a `view` token
- Prefer a VPN or Tailscale over a public tunnel (it also gives you HTTPS)
- If you use ngrok, use its authentication features as well
- Limit sharing to trusted collaborators
