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
| **Conflict-Free**          | Optional Yjs CRDT integration        |


---

## Solo Mode

For users who prefer working alone or offline, Noteworthy offers a dedicated **Solo Mode**.

### Why use Solo Mode?
- **Privacy**: No external connections, no chat, no online user visibility.
- **Simplicity**: Direct file editing without synchronization overhead.
- **Fast Live Preview**: Powered by [Tinymist](https://github.com/Myriad-Dreamin/tinymist) for instant rendering.

### Usage
Launch with the `-nc` flag:

```bash
noteworthy -g -nc
```

In Solo Mode, the "Solo" badge appears in the header, and collaboration features (Chat, Online Users) are disabled.

### Fast Preview

Solo Mode uses Tinymist for live preview instead of standard `typst watch`:
- **Instant updates**: Sub-100ms render times
- **Efficient**: Incremental SVG updates via WebSocket
- **Embedded**: Preview runs directly in the browser

---

## Starting a Session

### Local Network

For users on the same network:

```bash
# Start the server (accessible on LAN)
noteworthy -g
```

Share `http://<your-ip>:8000` with collaborators.

### Remote via ngrok

For internet collaboration:

1. **Install ngrok**: https://ngrok.com/download

2. **Start Noteworthy**:
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

Noteworthy uses a hybrid synchronization system:

1. **CRDT Backend (Optional)**: If available, uses `Yjs` for conflict-free real-time editing
2. **Standard Sync**: Falls back to last-write-wins if CRDT modules (`pycrdt`) are missing

### Conflict Prevention

- **Single-file scope**: Only one user can save a file at a time
- **Server authority**: Server version is always canonical
- **Optimistic UI**: Edits appear instantly, confirm on save
- **Selection Awareness**: Use selection highlighting to avoid stepping on teammates' toes

---

## Editing from Emacs

Emacs clients ([noteworthy-collab.el](https://github.com/R0K0R/noteworthy-collab.el))
do not speak the binary Yjs protocol. They connect to the bridge, which
translates a JSON delta protocol to and from the CRDT layer:

```text
Emacs --JSON /ws/emacs--> bridge (8001) --binary /yjs--> Studio (8000)
                                        \--JSON /ws/doc-->
```

Start the Studio server as usual, then run the bridge alongside it:

```bash
noteworthy -g                                              # Studio on :8000
uvicorn noteworthy.bridge.server:app --port 8001           # bridge on :8001
```

Point Emacs at the bridge, not the Studio port:

```elisp
(setq noteworthy-collab-server-url "ws://localhost:8001/ws/emacs")
```

Emacs peers appear in the web UI like any other collaborator — shared cursors,
selections and chat all cross the bridge. See the
[Emacs Protocol reference](../reference/emacs-protocol.md) for the wire format.

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

> [!WARNING]
> Noteworthy Studio does not have authentication. Anyone with the URL can:
> - View all files
> - Edit any content
> - See chat messages

For sensitive projects:
- Use ngrok's authentication features
- Limit sharing to trusted collaborators
- Consider a VPN for remote access

---

## Next Steps

- [Building Guide →](building.md)
- [Studio Architecture →](../architecture/gui-stack.md)
