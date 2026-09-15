"""An MCP server, so an agent edits the document rather than the file.

The file is the document's export.  Writing it behind a live room's back
gets the old text put straight back over the new one at the room's next
save, and nobody connected ever sees the edit -- which is why deploying a
generated file has always had to be followed by `/api/rooms/reload'.  Every
tool here goes through the room instead, so an edit reaches each open editor
the way a keystroke does and the file follows on the room's own save.

Spoken over Streamable HTTP (one POST, one JSON-RPC answer) rather than
stdio: the rooms live in this process, and an agent elsewhere can reach them
over the same port the editor already uses.

  claude mcp add --transport http noteworthy http://<host>:8010/mcp
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
SERVER_INFO = {"name": "noteworthy", "version": "1.0.0"}

# Editable text.  Not only `.typ': the schemes, the config, the templates and
# the build scripts are all part of the book as far as an agent is concerned.
TEXT_SUFFIXES = {
    ".typ", ".json", ".md", ".toml", ".yml", ".yaml", ".txt", ".csv",
    ".el", ".py", ".sh", ".nix", ".js", ".ts", ".css", ".html", ".svg",
    ".cfg", ".ini", ".lock",
}
SKIP_DIRS = {".git", "build", "node_modules", "__pycache__", ".noteworthy-crdt",
             "output", "dist", ".venv"}

TOOLS = [
    {
        "name": "list_documents",
        "description": (
            "List the project's editable documents, saying which are open in a "
            "live room right now (someone has the file open) and how long each is."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "under": {"type": "string",
                          "description": "Only paths under this directory, e.g. 'content/8'"},
            },
        },
    },
    {
        "name": "read_document",
        "description": (
            "Read a document. Returns the live room's text when the file is open "
            "in an editor -- which can be ahead of what is on disk -- and the file "
            "otherwise."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string",
                                    "description": "Project-relative, e.g. 'content/8/2.typ'"}},
            "required": ["path"],
        },
    },
    {
        "name": "edit_document",
        "description": (
            "Replace old_string with new_string in a document, through its room, so "
            "every open editor sees the edit and nothing of theirs is overwritten. "
            "old_string must appear exactly once unless replace_all is set."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
                "replace_all": {"type": "boolean", "default": False},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "append_document",
        "description": "Add text to the end of a document, through its room.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "text": {"type": "string"}},
            "required": ["path", "text"],
        },
    },
    {
        "name": "check_document",
        "description": (
            "Compile the book and return typst's diagnostics, so an edit can be "
            "checked before it is left behind."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _base_dir() -> Path:
    from ..gui.server import BASE_DIR
    return Path(BASE_DIR)


def _safe_path(rel: str) -> Path:
    """Resolve REL inside the project, refusing anything that climbs out."""
    base = _base_dir().resolve()
    target = (base / rel).resolve()
    if target != base and base not in target.parents:
        raise ValueError(f"path outside the project: {rel}")
    return target


def _documents(under: str | None = None):
    base = _base_dir().resolve()
    root = (base / under).resolve() if under else base
    if under and base not in root.parents and root != base:
        raise ValueError(f"path outside the project: {under}")
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(base).parts):
            continue
        out.append(p.relative_to(base).as_posix())
    return out


def _edit_on_disk(path: Path, old: str, new: str, replace_all: bool = False) -> int:
    """The same edit, for a file nobody has open.

    Same rules as the room path -- one match unless told otherwise -- so
    whether an edit is refused does not depend on who happens to be editing.
    """
    from ..gui.yjs_provider import find_edit_hits

    content = path.read_text(encoding="utf-8")
    hits = find_edit_hits(content, old, replace_all=replace_all)
    for i in reversed(hits):
        content = content[:i] + new + content[i + len(old):]
    tmp = path.with_name(f".{path.name}.nw-tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return len(hits)


async def _call_tool(name: str, args: dict) -> str:
    from ..gui.yjs_provider import yjs_provider

    if name == "list_documents":
        paths = _documents(args.get("under"))
        lines = []
        for rel in paths:
            room = yjs_provider.rooms.get(rel)
            if room is not None:
                try:
                    from pycrdt import Text
                    n = len(str(room.ydoc.get("content", type=Text)))
                    lines.append(f"{rel}  [open now, {n} chars]")
                    continue
                except Exception:
                    pass
            try:
                n = len(_safe_path(rel).read_text(encoding="utf-8"))
            except Exception:
                n = 0
            lines.append(f"{rel}  [{n} chars]")
        return "\n".join(lines) if lines else "(no documents)"

    if name == "read_document":
        rel = args["path"]
        room = yjs_provider.rooms.get(rel)
        if room is not None:
            from pycrdt import Text
            return str(room.ydoc.get("content", type=Text))
        return _safe_path(rel).read_text(encoding="utf-8")

    if name == "edit_document":
        rel = args["path"]
        path = _safe_path(rel)
        old, new = args["old_string"], args["new_string"]
        all_of_them = bool(args.get("replace_all"))
        if rel in yjs_provider.rooms:
            # Somebody has it open.  The edit goes into the document as the
            # one deletion and insertion it is, so what reaches them is that
            # much of a change and no more -- their cursor, their scroll and
            # their undo survive it.  Replacing the text wholesale is what
            # `rooms/reload' does, and it takes the editor out from under them.
            n = await yjs_provider.edit_room(rel, old, new, replace_all=all_of_them)
            return (f"replaced {n} occurrence(s) in {rel}, as a delta through the "
                    "live room: open editors have it, and the room saves the file")
        n = _edit_on_disk(path, old, new, replace_all=all_of_them)
        return f"replaced {n} occurrence(s) in {rel} on disk; no editor has it open"

    if name == "append_document":
        rel = args["path"]
        path = _safe_path(rel)
        addition = args["text"]
        if rel in yjs_provider.rooms:
            from pycrdt import Text
            room = yjs_provider.rooms[rel]
            text = room.ydoc.get("content", type=Text)
            text += addition          # an insert at the end: again, a delta
            return (f"appended {len(addition)} chars to {rel} through the live room")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(addition)
        return f"appended {len(addition)} chars to {rel} on disk"

    if name == "check_document":
        from ..gui.server import check_diagnostics
        result = await check_diagnostics({})
        diags = result.get("diagnostics", [])
        if not diags:
            return "no diagnostics: the book compiles"
        return "\n".join(
            f"{d.get('severity', 'error')}: {d.get('file', '?')}:{d.get('line', '?')} "
            f"{d.get('message', '')}"
            for d in diags
        )

    raise ValueError(f"unknown tool: {name}")


async def handle_rpc(msg: dict) -> dict | None:
    """One JSON-RPC message in, one answer out (None for a notification)."""
    method = msg.get("method")
    mid = msg.get("id")

    if method is not None and mid is None:
        # A notification: nothing to answer, including `initialized'.
        return None

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if method == "initialize":
        asked = (msg.get("params") or {}).get("protocolVersion")
        version = asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        return ok({
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        })

    if method == "ping":
        return ok({})

    if method == "tools/list":
        return ok({"tools": TOOLS})

    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            text = await _call_tool(name, args)
            return ok({"content": [{"type": "text", "text": text}], "isError": False})
        except Exception as e:
            log.warning("[MCP] %s failed: %s: %s", name, type(e).__name__, e)
            # A failed tool is a result, not a protocol error: the agent is
            # meant to read what went wrong and try something else.
            return ok({"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}],
                       "isError": True})

    return err(-32601, f"method not found: {method}")
