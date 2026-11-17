"""Typst diagnostics for /api/check: compile the whole book and parse typst's errors.

The body is the old gui/server.py check_diagnostics unchanged, except that the
blocking compile now runs in a worker thread instead of stalling the event loop
(and with it every websocket) for the length of the compile.
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile

from ..config import BASE_DIR, RENDERER_FILE

log = logging.getLogger("noteworthy.syncworthy_plugin")

# Long enough for a book that is merely large, short enough that a runaway
# page is a failed check rather than a wedged machine.
CHECK_TIMEOUT_SECONDS = 180


def _check_book_sync() -> dict:
    """Run typst compile to get diagnostics."""
    # Find typst binary
    typst_bin = shutil.which("typst")
    if not typst_bin:
        # Try common paths
        for path in ["/opt/homebrew/bin/typst", "/usr/local/bin/typst", os.path.expanduser("~/.cargo/bin/typst")]:
            if os.path.exists(path):
                typst_bin = path
                break
    
    if not typst_bin:
        log.error("typst binary not found")
        return {"diagnostics": [], "error": "typst not found"}
    
    # Create temp file for output
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # Scan content directory to get actual chapter/page structure
        content_dir = BASE_DIR / "content"
        chapter_folders = []
        page_folders = {}
        
        if content_dir.exists():
            # Get sorted chapter directories (numeric order)
            ch_dirs = sorted(
                [d for d in content_dir.iterdir() if d.is_dir() and d.name.replace('.', '', 1).lstrip('-').isdigit()],
                key=lambda d: float(d.name) if d.name.replace('.', '', 1).lstrip('-').isdigit() else 999
            )
            for ch_dir in ch_dirs:
                chapter_folders.append(ch_dir.name)
                # Get sorted page files (numeric order, without .typ extension)
                pg_files = sorted(
                    [f.stem for f in ch_dir.glob("*.typ") if f.stem.replace('.', '', 1).lstrip('-').isdigit()],
                    key=lambda s: float(s) if s.replace('.', '', 1).lstrip('-').isdigit() else 999
                )
                # Keyed by folder NAME (see utils.scan_content); keying by
                # index only matched while chapters ran 0,1,2,... .
                page_folders[ch_dir.name] = pg_files
        
        # Run typst compile with folder info.
        #
        # Bounded, because this compiles the whole book and a single page can
        # make that unbounded: `smp = 1007' in one figure -- a sample count
        # feeding every surface and curve on the page -- took 23 minutes and
        # 21.9 GB of a 31 GB machine before anyone noticed, with nothing to
        # stop it but the OOM killer.  Cetz costs roughly the square of the
        # sample count, so this is a cliff a keystroke can walk off.
        try:
            result = subprocess.run(
                [
                    typst_bin, "compile", str(RENDERER_FILE), tmp_path,
                    "--root", str(BASE_DIR),
                    "--input", f"chapter-folders={json.dumps(chapter_folders)}",
                    "--input", f"page-folders={json.dumps(page_folders)}"
                ],
                capture_output=True,
                text=True,
                timeout=CHECK_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            log.error("check: typst exceeded %ss; a page is pathological",
                      CHECK_TIMEOUT_SECONDS)
            return {
                "diagnostics": [],
                "error": (f"typst did not finish within {CHECK_TIMEOUT_SECONDS}s "
                          "and was stopped. Some page costs far more than the "
                          "rest -- a large sample or segment count in a figure "
                          "is the usual reason."),
            }
        
        log.debug(f"typst stderr: {result.stderr}")
        log.debug(f"typst returncode: {result.returncode}")
        
        diagnostics = []
        lines = result.stderr.split('\n')
        current_error = None
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith("error:"):
                msg = stripped[6:].strip()
                current_error = {"message": msg, "severity": "error"}
            
            # Typst uses Unicode box-drawing: ┌─ file:line:col
            elif ("┌" in stripped or "├" in stripped) and current_error:
                # Extract location after the box character
                # Format: ┌─ file.typ:line:col or ├─ file.typ:line:col
                idx = stripped.find("─")
                if idx != -1:
                    location = stripped[idx+1:].strip()
                    parts = location.split(':')
                    if len(parts) >= 3:
                        try:
                            line_num = int(parts[-2])
                            col_num = int(parts[-1])
                            path_str = ":".join(parts[:-2]).strip()
                            
                            current_error["line"] = line_num
                            current_error["col"] = col_num
                            current_error["file"] = path_str
                            diagnostics.append(current_error)
                            current_error = None
                        except ValueError:
                            pass
        
        log.debug(f"Parsed diagnostics: {diagnostics}")
        return {"diagnostics": diagnostics}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


async def check_book() -> dict:
    return await asyncio.to_thread(_check_book_sync)


class NoteworthyDiagnostics:
    """Syncworthy diagnostics provider (see syncworthy.plugins.Diagnostics)."""

    extensions = (".typ",)

    async def check(self, ctx, path: str) -> dict:
        return await check_book()
