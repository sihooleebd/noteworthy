"""Cross-document references for a book built one page at a time.

Each page is compiled on its own and the PDFs are merged, so Typst never sees
more than a page: a label defined elsewhere does not exist, and referencing it
is a hard error rather than a bad-looking reference.

Two passes bridge that.

`collect()` compiles the whole document once -- only to query it, never to
render -- and reads back every block in document order together with the page
it sits on.  That yields the text a reference should show ("Theorem 8.3") and,
for the numbering scopes that outrun a single page, where each page's counters
must start.

`rewrite_links()` runs after the merge, which is the first moment "what page did
that land on" has an answer.  Typst emits `nw-anchor:<name>` and `nw-ref:<name>`
as URI links -- the one annotation that survives pdfunite with its text intact
-- and this turns the refs into real internal jumps and drops the anchors.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from ..config import BASE_DIR, RENDERER_FILE

log = logging.getLogger("noteworthy.xref")

ANCHOR_PREFIX = "nw-anchor:"
REF_PREFIX = "nw-ref:"


# ---------------------------------------------------------------- first pass


def _query_marks(typst_path: str, extra_flags: list[str]) -> list[dict]:
    """Every marker in the whole document, in reading order.

    One query, not two: page markers and block markers share a label precisely
    so they come back interleaved.  Two queries would each be ordered and
    neither would say which page a block fell on, which is the only thing this
    pass is for.
    """
    cmd = [typst_path, "query", str(RENDERER_FILE), "<nw-mark>",
           "--root", str(BASE_DIR), "--field", "value", *extra_flags]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        log.error("xref: query failed to run: %s", e)
        return []
    if out.returncode != 0:
        # A document that cannot compile has nothing to collect; the build is
        # about to report the same error far more usefully.
        log.warning("xref: query returned %s; continuing without a label map",
                    out.returncode)
        return []
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError as e:
        log.error("xref: could not parse query output: %s", e)
        return []


def _scoped_number(number, scope: str, ch: str, pg: str, scoped: bool) -> str:
    """The number as the block itself prints it.

    Mirrors `_scoped-number' in xref.typ, and must: a page showing "Theorem 1"
    while a reference to it says "Theorem 8.1.1" is worse than either being
    wrong on its own.  A block that numbers itself locally -- a solution,
    counted within the theorem it belongs to -- gets no scope prefix here
    either, for the same reason.
    """
    if number is None:
        return ""
    if not scoped:
        return str(number)
    if scope == "document":
        return f"{ch}.{pg}.{number}"
    if scope == "chapter":
        return f"{pg}.{number}"
    return str(number)


def _caption(kind: str, title: str, number, ref_format: str,
             chapter_name: str, ch: str, pg: str, cid: str, pid: str,
             scope: str, scoped: bool = True, parent: dict | None = None) -> dict:
    """Both readings of a reference to this block.

    `same` is what to show when the reference sits on the same page as its
    target -- there, naming the page again is noise.  `full` adds the address
    for everywhere else.  Which one applies depends on where the reference is
    read, so the choice belongs to the template, not here; this only supplies
    the two strings and the location to compare against.
    """
    name = kind[:1].upper() + kind[1:]
    num = _scoped_number(number, scope, ch, pg, scoped)

    head = name
    if num:
        head = f"{name} {num}"
        if ref_format == "title-number" and title:
            head = f'{name} "{title}" {num}'
    elif title:
        # No number to identify it by, so the title is doing that job.
        head = f'{name} "{title}"'

    if not scoped and parent is not None:
        # "Solution 2" counts within the block holding it, so on its own it
        # picks out nothing: a page can hold several blocks that each have a
        # second solution.  Naming that block is what makes it an address,
        # and the block's own caption already carries however much of the
        # chapter and page the reader needs.
        return {"same": f"{head} of {parent['same']}",
                "full": f"{head} of {parent['full']}", "ch": ch, "pg": pg}
    if not scoped:
        # In no block at all, so it counts across the page and the page is
        # the only address there is.
        where = f" in {chapter_name} {pid}" if pid else ""
    elif scope == "document" and num:
        # The number is already the full address.
        where = ""
    elif scope == "chapter":
        where = f" in {chapter_name} {cid}" if cid else ""
    else:
        where = f" in {chapter_name} {pid}" if pid else ""
    if ref_format == "number-only":
        where = ""

    return {"same": head, "full": head + where, "ch": ch, "pg": pg}


def collect(typst_path: str, extra_flags: list[str], *, scope: str = "page",
            ref_format: str = "number", chapter_name: str = "Chapter",
            number_blocks: bool = False) -> dict:
    """Return label -> {same, full, ch, pg}.

    The two readings of a reference and where its target is, so the template
    can tell whether the reference is being read on the same page as the block
    it names.
    """
    marks = _query_marks(typst_path, extra_flags)
    if not marks:
        return {}

    label_map: dict[str, str] = {}
    counts: dict[str, int] = {}        # kind -> count so far, on this page
    sol_counts: dict[object, int] = {}  # block id -> solutions in it so far
    stack: list[dict] = []             # blocks currently open, innermost last
    uid = 0
    ch = pg = None
    cid = pid = ""

    for m in marks:
        if not isinstance(m, dict):
            continue
        if m.get("t") == "page":
            ch, pg = str(m.get("ch", "")), str(m.get("pg", ""))
            cid, pid = str(m.get("cid", "") or ""), str(m.get("pid", "") or "")
            # Every page, whatever the scope: the scope says how much address
            # the number shows, not where counting restarts.  Continuing the
            # count across pages made the first definition on page 8.2 read
            # "Definition 8.2.3".
            counts = {}
            # A page is compiled on its own, so a block-local counter cannot
            # see the page before it however wide the numbering scope is.
            sol_counts = {}
            stack = []
            continue
        if m.get("t") == "block-end":
            if stack:
                stack.pop()
            continue
        if m.get("t") != "block":
            continue
        kind = str(m.get("kind", "block"))
        style = str(m.get("style", "scoped"))
        given = str(m.get("num", "") or "")
        # The innermost block still open is the one this sits inside, which
        # is the only reading of "inside" that survives blocks nesting.
        parent = stack[-1] if stack else None
        if style == "scoped":
            # Advances even for a hand-numbered block, exactly as the template
            # does it, so the next automatic one does not repeat.
            counts[kind] = counts.get(kind, 0) + 1
            count = counts[kind]
        elif style == "local":
            # Counted within that block, or across the page when in none.
            key = parent["uid"] if parent else "page"
            sol_counts[key] = sol_counts.get(key, 0) + 1
            count = sol_counts[key]
        else:
            count = None
        # A solution prints its count whether or not block numbering is on:
        # that number is part of how a solution reads, not part of the
        # document-wide scheme the setting governs.
        numbered = count is not None and (number_blocks or style == "local")
        number = (given or count) if numbered else None
        entry = _caption(kind, str(m.get("title", "") or ""),
                         number, ref_format, chapter_name,
                         ch or "", pg or "", cid, pid, scope,
                         style == "scoped", parent)
        # Every block stays open until its closing mark whether or not
        # anything refers to it: a solution inside an unlabelled theorem
        # still counts within that theorem.
        uid += 1
        stack.append({"uid": uid, "same": entry["same"], "full": entry["full"]})
        label = str(m.get("label", "") or "")
        if label:
            label_map[label] = entry

    return label_map


# ------------------------------------------------------------ post-merge pass


def _uri_of(annot) -> str:
    action = annot.get("/A")
    if action is None:
        return ""
    action = action.get_object()
    if action.get("/S") != "/URI":
        return ""
    return str(action.get("/URI") or "")


def rewrite_links(pdf_path: Path) -> tuple[int, int]:
    """Turn the markers in a merged PDF into real links.

    Returns (rewritten, dropped).  Anchors are removed once used: they are
    scaffolding, and a reader clicking one would be sent to itself.
    """
    try:
        import pypdf
        from pypdf.generic import (ArrayObject, DictionaryObject, FloatObject,
                                   NameObject, NumberObject)
    except ImportError:
        log.warning("xref: pypdf not available, leaving links as markers")
        return (0, 0)

    try:
        writer = pypdf.PdfWriter(clone_from=str(pdf_path))
    except Exception as e:
        log.error("xref: could not open %s: %s", pdf_path, e)
        return (0, 0)

    # First occurrence wins: a link around a heading becomes one annotation per
    # text box, and the first is the top-left of the thing being referenced.
    anchors: dict[str, tuple[int, object]] = {}
    for index, page in enumerate(writer.pages):
        for annot in (page.get("/Annots") or []):
            obj = annot.get_object()
            uri = _uri_of(obj)
            if uri.startswith(ANCHOR_PREFIX):
                anchors.setdefault(uri[len(ANCHOR_PREFIX):], (index, obj["/Rect"]))

    rewritten = dropped = 0
    for page in writer.pages:
        annots = page.get("/Annots")
        if annots is None:
            continue
        keep = []
        for annot in annots:
            obj = annot.get_object()
            uri = _uri_of(obj)
            if uri.startswith(ANCHOR_PREFIX):
                dropped += 1
                continue
            if uri.startswith(REF_PREFIX):
                name = uri[len(REF_PREFIX):]
                target = anchors.get(name)
                if target is None:
                    # Referenced but never anchored -- leave the text, drop the
                    # dead link rather than pointing it somewhere arbitrary.
                    obj.pop(NameObject("/A"), None)
                else:
                    page_index, rect = target
                    obj[NameObject("/A")] = DictionaryObject({
                        NameObject("/S"): NameObject("/GoTo"),
                        NameObject("/D"): ArrayObject([
                            writer.pages[page_index].indirect_reference,
                            NameObject("/XYZ"),
                            FloatObject(rect[0]), FloatObject(rect[3]),
                            NumberObject(0),
                        ]),
                    })
                    rewritten += 1
            keep.append(annot)
        page[NameObject("/Annots")] = ArrayObject(keep)

    try:
        writer.write(str(pdf_path))
    except Exception as e:
        log.error("xref: could not write %s: %s", pdf_path, e)
        return (0, 0)
    log.info("xref: %d reference(s) linked, %d anchor(s) dropped", rewritten, dropped)
    return (rewritten, dropped)
