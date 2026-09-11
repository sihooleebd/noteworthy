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


def _scoped_number(number, scope: str, ch: str, pg: str) -> str:
    """The number as the block itself prints it.

    Mirrors `_scoped-number' in xref.typ, and must: a page showing "Theorem 1"
    while a reference to it says "Theorem 8.1.1" is worse than either being
    wrong on its own.
    """
    if number is None:
        return ""
    if scope == "document":
        return f"{ch}.{pg}.{number}"
    if scope == "chapter":
        return f"{pg}.{number}"
    return str(number)


def _caption(kind: str, title: str, number, ref_format: str,
             chapter_name: str, ch: str, pg: str, cid: str, pid: str,
             scope: str) -> dict:
    """Both readings of a reference to this block.

    `same` is what to show when the reference sits on the same page as its
    target -- there, naming the page again is noise.  `full` adds the address
    for everywhere else.  Which one applies depends on where the reference is
    read, so the choice belongs to the template, not here; this only supplies
    the two strings and the location to compare against.
    """
    name = kind[:1].upper() + kind[1:]
    num = _scoped_number(number, scope, ch, pg)

    head = name
    if num:
        head = f"{name} {num}"
        if ref_format == "title-number" and title:
            head = f'{name} "{title}" {num}'
    elif title:
        # No number to identify it by, so the title is doing that job.
        head = f'{name} "{title}"'

    if scope == "document" and num:
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
            number_blocks: bool = False) -> tuple[dict, dict]:
    """Return (label_map, offsets_by_target).

    `label_map` is label -> {same, full, ch, pg}: the two readings of a
    reference and where its target is, so the template can tell whether the
    reference is being read on that same page.
    `offsets_by_target` is "ch/pg" -> {kind: starting count}, empty under
    `page` scope because a page is exactly what one compilation can see.
    """
    marks = _query_marks(typst_path, extra_flags)
    if not marks:
        return {}, {}

    label_map: dict[str, str] = {}
    offsets: dict[str, dict[str, int]] = {}
    counts: dict[str, int] = {}        # kind -> count so far, within the scope
    ch = pg = None
    cid = pid = ""
    prev_ch = None

    for m in marks:
        if not isinstance(m, dict):
            continue
        if m.get("t") == "page":
            ch, pg = str(m.get("ch", "")), str(m.get("pg", ""))
            cid, pid = str(m.get("cid", "") or ""), str(m.get("pid", "") or "")
            if scope == "page" or (scope == "chapter" and ch != prev_ch):
                counts = {}
            prev_ch = ch
            # What this page's counters must start from.  Recorded before the
            # page's own blocks are counted, which is what makes it a start.
            offsets[f"{ch}/{pg}"] = dict(counts)
            continue
        if m.get("t") != "block":
            continue
        kind = str(m.get("kind", "block"))
        counts[kind] = counts.get(kind, 0) + 1
        label = str(m.get("label", "") or "")
        if label:
            number = counts[kind] if number_blocks else None
            label_map[label] = _caption(kind, str(m.get("title", "") or ""),
                                        number, ref_format, chapter_name,
                                        ch or "", pg or "", cid, pid, scope)

    if scope == "page":
        # Every page starts from nothing, so there is nothing to inject.
        offsets = {}
    return label_map, offsets


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
