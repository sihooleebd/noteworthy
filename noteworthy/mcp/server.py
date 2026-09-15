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
        "name": "render_document",
        "description": (
            "Render the book, a chapter or a single page and hand back what it "
            "looks like. Page images by default, which is what checking your own "
            "figure needs; format 'pdf' returns the file itself. Targets are "
            "named, not indexed: 'content/8/2.typ', '8/2' or '8'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": (
                        "'content/8/2.typ' or '8/2' for one page, '8' for a whole "
                        "chapter, 'cover'/'preface'/'outline', or omit for the "
                        "whole book."
                    ),
                },
                "format": {
                    "type": "string",
                    "enum": ["png", "pdf"],
                    "default": "png",
                    "description": (
                        "Either way the pages come back as images to look at; "
                        "'pdf' also leaves the PDF on the server and says where."
                    ),
                },
                "pages": {
                    "type": "string",
                    "description": "Which rendered pages to return, e.g. '1' or '2-4'. Default: all, up to the cap.",
                },
                "ppi": {"type": "number", "default": 110},
            },
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


def _expected_token() -> str | None:
    """The token every request must carry, from the environment or a file.

    `NOTEWORTHY_MCP_TOKEN_FILE' so the secret can live in a file the process
    can read and nothing else can -- /run/agenix/... , mode 400 -- rather than
    in a unit file or a store path that is world-readable by construction.
    """
    import os

    path = os.environ.get("NOTEWORTHY_MCP_TOKEN_FILE")
    if path:
        try:
            return Path(path).read_text(encoding="utf-8").strip() or None
        except OSError as e:
            log.error("[MCP] token file %s unreadable: %s", path, e)
            return None
    return (os.environ.get("NOTEWORTHY_MCP_TOKEN") or "").strip() or None


def authorize(header: str | None, query_token: str | None = None) -> tuple[bool, str]:
    """Whether a request may proceed, and why not when it may not.

    Fails closed.  With no token configured the endpoint refuses everyone,
    rather than serving whoever can reach it: the tools here read and rewrite
    the book, and `tailscale funnel' arrives over loopback like anything else,
    so there is no address this could trust its way out of.
    """
    import hmac

    expected = _expected_token()
    if not expected:
        return False, ("this server has no NOTEWORTHY_MCP_TOKEN set, so it "
                       "serves nobody")
    # A query token as well as a header, for clients that cannot send one.
    # Claude's mobile and web connectors authenticate by OAuth or not at all,
    # and a 401 sends them looking for metadata this server does not publish.
    # A token in the URL is weaker -- it is kept in the connector's config and
    # shows up in any logging that records URLs -- so it is the fallback, not
    # the way in.
    if query_token:
        given = query_token.strip()
    elif header and header.lower().startswith("bearer "):
        given = header.split(" ", 1)[1].strip()
    else:
        return False, "missing bearer token"
    if not hmac.compare_digest(given, expected):
        return False, "bad token"
    return True, ""


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


# A page image the agent has to look at is worth its tokens; a bookful of them
# is not.  Beyond these it says what it rendered and where, and shows nothing.
# A render answers in pictures.  Handing back a PDF's bytes was worse than
# useless: base64 is text, so the 621 kB book arrived as 828,740 characters --
# a context window's worth of tokens -- and not one of them was something that
# could be looked at.  Pages come back as images, which cost image tokens and
# can actually be seen; the PDF, when asked for, is written and named.
MAX_IMAGES = 6


def _project_inputs() -> tuple[list[str], dict[str, list[str]]]:
    """The chapter and page folders, in the order the parser numbers them."""
    base = _base_dir()
    content = base / "content"
    chapters: list[str] = []
    pages: dict[str, list[str]] = {}
    if not content.exists():
        return chapters, pages

    def numeric(name: str) -> bool:
        return name.replace(".", "", 1).lstrip("-").isdigit()

    for d in sorted((d for d in content.iterdir() if d.is_dir() and numeric(d.name)),
                    key=lambda d: float(d.name)):
        chapters.append(d.name)
        pages[d.name] = sorted((f.stem for f in d.glob("*.typ") if numeric(f.stem)),
                               key=float)
    return chapters, pages


def _resolve_target(target: str | None) -> tuple[str | None, str]:
    """A named target -> what the parser wants, which counts from zero.

    `target=0/1' is the second page of the first chapter, not `content/0/1.typ'.
    Nobody should have to know that to render a page they can see the name of.
    """
    if not target:
        return None, "the whole book"
    if target in ("cover", "preface", "outline"):
        return target, target

    chapters, pages = _project_inputs()
    rel = target
    for prefix in ("content/", "./content/"):
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
    rel = rel[:-4] if rel.endswith(".typ") else rel

    if "/" in rel:
        ch, pg = rel.split("/", 1)
        if ch not in chapters:
            raise ValueError(f"no chapter {ch}; have {', '.join(chapters)}")
        if pg not in pages.get(ch, []):
            raise ValueError(f"no page {ch}/{pg}; have {', '.join(pages.get(ch, []))}")
        return f"{chapters.index(ch)}/{pages[ch].index(pg)}", f"content/{ch}/{pg}.typ"
    if rel not in chapters:
        raise ValueError(f"no chapter {rel}; have {', '.join(chapters)}")
    return f"chapter-{chapters.index(rel)}", f"chapter {rel}"


def _page_range(spec: str | None, count: int) -> list[int]:
    if not spec:
        return list(range(1, count + 1))
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return [n for n in out if 1 <= n <= count]


async def _render(args: dict) -> list[dict]:
    """Render, and answer in the content blocks MCP has for pictures and files."""
    import base64
    import json as _json
    import shutil
    import subprocess
    import tempfile

    typst = shutil.which("typst")
    if not typst:
        raise ValueError("typst not on PATH for the server process")

    target, described = _resolve_target(args.get("target"))
    fmt = args.get("format", "png")
    base = _base_dir()
    chapters, pages = _project_inputs()

    inputs = [
        "--input", f"chapter-folders={_json.dumps(chapters)}",
        "--input", f"page-folders={_json.dumps(pages)}",
    ]
    if target:
        inputs += ["--input", f"target={target}"]

    with tempfile.TemporaryDirectory(prefix="nw-render-") as tmp:
        def compile_to(out: Path, extra: list[str]) -> subprocess.CompletedProcess:
            return subprocess.run(
                [typst, "compile", str(base / "templates" / "core" / "parser.typ"),
                 str(out), "--root", str(base), *inputs, *extra],
                capture_output=True, text=True, timeout=300,
            )

        # The pages, as pictures, which is the answer either way.
        done = compile_to(Path(tmp) / "render-{n}.png",
                          ["--ppi", str(int(args.get("ppi", 110)))])
        if done.returncode != 0:
            head = (done.stderr or done.stdout).strip().splitlines()[:12]
            return [{"type": "text", "text": "render failed:\n" + "\n".join(head)}]

        note = ""
        if fmt == "pdf":
            kept = base / "build" / "render"
            kept.mkdir(parents=True, exist_ok=True)
            name = (args.get("target") or "book").replace("/", "-").removesuffix(".typ") + ".pdf"
            pdf = compile_to(kept / name, [])
            note = (f"; PDF at {kept / name} ({(kept / name).stat().st_size:,} bytes)"
                    if pdf.returncode == 0 else f"; PDF failed: {pdf.stderr.strip()[:120]}")

        shots = sorted(Path(tmp).glob("render-*.png"),
                       key=lambda p: int(p.stem.split("-")[-1]))
        wanted = _page_range(args.get("pages"), len(shots))
        shown = wanted[:MAX_IMAGES]
        blocks: list[dict] = [{
            "type": "text",
            "text": f"rendered {described}: {len(shots)} page(s), showing "
                    f"{len(shown)}{note}",
        }]
        for n in shown:
            blocks.append({"type": "image",
                           "data": base64.b64encode(shots[n - 1].read_bytes()).decode("ascii"),
                           "mimeType": "image/png"})
        if len(wanted) > MAX_IMAGES:
            blocks.append({"type": "text",
                           "text": f"{len(wanted) - MAX_IMAGES} more page(s) not shown; "
                                   "name them with `pages`"})
        return blocks


async def _call_tool(name: str, args: dict) -> str | list[dict]:
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

    if name == "render_document":
        return await _render(args)

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
            result = await _call_tool(name, args)
            # A tool may answer in blocks -- a render hands back pictures, and a
            # picture is the whole point of asking it.
            content = (result if isinstance(result, list)
                       else [{"type": "text", "text": result}])
            return ok({"content": content, "isError": False})
        except Exception as e:
            log.warning("[MCP] %s failed: %s: %s", name, type(e).__name__, e)
            # A failed tool is a result, not a protocol error: the agent is
            # meant to read what went wrong and try something else.
            return ok({"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}],
                       "isError": True})

    return err(-32601, f"method not found: {method}")
