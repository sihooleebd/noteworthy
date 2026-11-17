"""Noteworthy's MCP tools for Syncworthy: render_document and check_document.

The bodies are the old noteworthy/mcp/server.py ones, parametrized on the
project root instead of reaching for gui.server; the generic tools
(list/read/edit/append) are Syncworthy's own.
"""
from pathlib import Path

from syncworthy.plugins import McpTool

from .diagnostics import check_book


RENDER_DESCRIPTION = "Render the book, a chapter or a single page and hand back what it looks like. Page images by default, which is what checking your own figure needs; format 'pdf' returns the file itself. Targets are named, not indexed: 'content/8/2.typ', '8/2' or '8'."
RENDER_SCHEMA = {'properties': {'format': {'default': 'png',
                           'description': 'Either way the pages come back as images to look at; '
                                          "'pdf' also leaves the PDF on the server and says where.",
                           'enum': ['png', 'pdf'],
                           'type': 'string'},
                'pages': {'description': "Which rendered pages to return, e.g. '1' or '2-4'. "
                                         'Default: all, up to the cap.',
                          'type': 'string'},
                'ppi': {'default': 110, 'type': 'number'},
                'target': {'description': "'content/8/2.typ' or '8/2' for one page, '8' for a "
                                          "whole chapter, 'cover'/'preface'/'outline', or omit for "
                                          'the whole book.',
                           'type': 'string'}},
 'type': 'object'}

CHECK_DESCRIPTION = "Compile the book and return typst's diagnostics, so an edit can be checked before it is left behind."
CHECK_SCHEMA = {'properties': {}, 'type': 'object'}


# A page image the agent has to look at is worth its tokens; a bookful of them
# is not.  Beyond these it says what it rendered and where, and shows nothing.
# A render answers in pictures.  Handing back a PDF's bytes was worse than
# useless: base64 is text, so the 621 kB book arrived as 828,740 characters --
# a context window's worth of tokens -- and not one of them was something that
# could be looked at.  Pages come back as images, which cost image tokens and
# can actually be seen; the PDF, when asked for, is written and named.
MAX_IMAGES = 6


def _project_inputs(base: Path) -> tuple[list[str], dict[str, list[str]]]:
    """The chapter and page folders, in the order the parser numbers them."""
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


def _resolve_target(base: Path, target: str | None) -> tuple[str | None, str]:
    """A named target -> what the parser wants, which counts from zero.

    `target=0/1' is the second page of the first chapter, not `content/0/1.typ'.
    Nobody should have to know that to render a page they can see the name of.
    """
    if not target:
        return None, "the whole book"
    if target in ("cover", "preface", "outline"):
        return target, target

    chapters, pages = _project_inputs(base)
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


async def _render(base: Path, args: dict) -> list[dict]:
    """Render, and answer in the content blocks MCP has for pictures and files."""
    import base64
    import json as _json
    import shutil
    import subprocess
    import tempfile

    typst = shutil.which("typst")
    if not typst:
        raise ValueError("typst not on PATH for the server process")

    target, described = _resolve_target(base, args.get("target"))
    fmt = args.get("format", "png")
    chapters, pages = _project_inputs(base)

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


async def _check_document(ctx, args: dict) -> str:
    result = await check_book()
    diags = result.get("diagnostics", [])
    if not diags:
        return "no diagnostics: the book compiles"
    return "\n".join(
        f"{d.get('severity', 'error')}: {d.get('file', '?')}:{d.get('line', '?')} "
        f"{d.get('message', '')}"
        for d in diags
    )


async def _render_document(ctx, args: dict):
    return await _render(ctx.root, args)


def tools() -> list[McpTool]:
    return [
        McpTool("render_document", RENDER_DESCRIPTION, RENDER_SCHEMA, _render_document),
        McpTool("check_document", CHECK_DESCRIPTION, CHECK_SCHEMA, _check_document),
    ]
