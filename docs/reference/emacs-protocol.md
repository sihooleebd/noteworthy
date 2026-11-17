# Emacs Collaboration Protocol

> [!NOTE]
> **The protocol documented here is retired.** The `/ws/emacs` JSON bridge
> (`noteworthy/bridge/server.py`) was removed from this repository, along with
> the old web GUI it talked to. This page now only points at what replaced it.

## Current setup

Emacs collaboration is split into three independent pieces:

| Piece | What | Repository |
| --- | --- | --- |
| **emacs-collab protocol** | The wire protocol between Emacs and a bridge program: JSON lines on the bridge's stdin/stdout. It is service-agnostic; each collaboration service has its own bridge. | [`emacs-collab.el`](https://github.com/R0K0R/emacs-collab.el), see `PROTOCOL.md` |
| **syncworthy_bridge** | The bridge for a Syncworthy server (which is what `noteworthy -g` runs). It speaks emacs-collab to Emacs, and REST, `/yjs/<path>` (Yjs) and `/ws/doc` to Syncworthy. | [`syncworthy_bridge`](https://github.com/R0K0R/syncworthy_bridge) |
| **noteworthy-workspace** | The Noteworthy front end in Emacs: window layout, Typst preview, pages. `noteworthy-workspace-connect SERVER [TOKEN]` opens a server project. | [`noteworthy-workspace`](https://github.com/R0K0R/noteworthy-workspace) |

```text
Emacs (emacs-collab.el + noteworthy-workspace)
   <--emacs-collab JSON lines, stdio-->  syncworthy_bridge
   <--REST, /yjs/<path>, /ws/doc-->  Syncworthy (+ noteworthy plugin)
```

The normative description of the Emacs side is
[PROTOCOL.md](https://github.com/R0K0R/emacs-collab.el/blob/master/PROTOCOL.md);
how the bridge maps a Syncworthy server onto it (mirror directory, attach,
presence, auth tokens, view-only tokens, what is not offered) is in the
`syncworthy_bridge` README. See also the
[Collaboration guide](../guides/collaboration.md#editing-from-emacs).

## What stays the same on the server side

- Document content travels only over the binary `/yjs/<room>` WebSocket, one
  room per file; the room name is the URL-encoded project-relative path and the
  shared text is the Y.Text `content`.
- Presence, cursors and chat use the JSON `/ws/doc` socket.
- Auth tokens, when configured, go as `Authorization: Bearer` or
  `?access_token=`; see the [Studio stack](../architecture/gui-stack.md#security).

## Retired

`/ws/emacs` (the old JSON delta protocol with `join`, `delta`, `cursor`...),
the bridge on port 8001, `NOTEWORTHY_MAIN_WS`, and `noteworthy-collab.el` as a
client. Do not build new clients against them.
