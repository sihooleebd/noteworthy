#!/usr/bin/env python3

import copy
import curses
import fcntl
import gc
import json
import os
import shutil
import subprocess
import sys
import termios
import threading
import time
import tty
import argparse
import zipfile
from pathlib import Path

# =============================================================================
# CONSTANTS
# =============================================================================

# Build Paths
BUILD_DIR = Path("templates/build")
OUTPUT_FILE = Path("output.pdf")
RENDERER_FILE = "templates/parser.typ"

# System Config Paths
SYSTEM_CONFIG_DIR = Path("templates/systemconfig")
SETTINGS_FILE = SYSTEM_CONFIG_DIR / "build_settings.json"
INDEXIGNORE_FILE = SYSTEM_CONFIG_DIR / ".indexignore"

# Config File Paths
CONFIG_FILE = Path("templates/config/config.json")
HIERARCHY_FILE = Path("templates/config/hierarchy.json")
PREFACE_FILE = Path("templates/config/preface.typ")
SNIPPETS_FILE = Path("templates/config/snippets.typ")
SCHEMES_FILE = Path("templates/config/schemes.json")
SETUP_FILE = Path("templates/setup.typ")
CONTENT_DIR = Path("content")

# Terminal Size Requirements
MIN_TERM_HEIGHT = 20
MIN_TERM_WIDTH = 50

# ASCII Art
LOGO = [
    "         ,--. ", "       ,--.'| ", "   ,--,:  : | ", ",`--.'`|  ' : ",
    "|   :  :  | | ", ":   |   \\ | : ", "|   : '  '; | ", "'   ' ;.    ; ",
    "|   | | \\   | ", "'   : |  ; .' ", "|   | '`--'   ", "'   : |       ",
    ";   |.'       ", "'---'         ",
]
HAPPY_FACE = ["    __  ", " _  \\ \\ ", "(_)  | |", "     | |", " _   | |", "(_)  | |", "    /_/ "]
HMM_FACE = ["     _ ", " _  | |", "(_) | |", "    | |", " _  | |", "(_) | |", "    |_|"]
SAD_FACE = ["       __", "  _   / /", " (_) | | ", "     | | ", "  _  | | ", " (_) | | ", "      \\_\\"]

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def check_dependencies():
    if not shutil.which("typst"):
        print("Error: 'typst' not found. Install from https://typst.app")
        sys.exit(1)
    if not shutil.which("pdfinfo"):
        print("Error: 'pdfinfo' not found. Install with: brew install poppler")
        sys.exit(1)

def get_pdf_page_count(pdf_path):
    try:
        result = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True)
        for line in result.stdout.split('\n'):
            if line.startswith('Pages:'):
                return int(line.split(':')[1].strip())
    except:
        pass
    return 0

def extract_hierarchy():
    temp_file = Path("extract_hierarchy.typ")
    temp_file.write_text('#import "templates/setup.typ": hierarchy\n#metadata(hierarchy) <hierarchy>')
    try:
        result = subprocess.run(["typst", "query", str(temp_file), "<hierarchy>"], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)[0]["value"]
    except subprocess.CalledProcessError as e:
        print(f"Error extracting hierarchy: {e.stderr}")
        sys.exit(1)
    finally:
        temp_file.unlink(missing_ok=True)

def load_settings():
    try:
        SYSTEM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if SETTINGS_FILE.exists():
            return json.loads(SETTINGS_FILE.read_text())
    except: pass
    return {}

def save_settings(settings):
    try:
        SYSTEM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    except: pass

def load_indexignore():
    """Load ignored file patterns from .indexignore (one per line)."""
    try:
        if INDEXIGNORE_FILE.exists():
            lines = INDEXIGNORE_FILE.read_text().strip().split('\n')
            return set(l.strip() for l in lines if l.strip() and not l.startswith('#'))
    except: pass
    return set()

def save_indexignore(ignored):
    """Save ignored file patterns to .indexignore."""
    try:
        SYSTEM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        content = "# Files to ignore during hierarchy sync\n# One file ID per line (e.g., 01.03)\n\n"
        content += '\n'.join(sorted(ignored))
        INDEXIGNORE_FILE.write_text(content)
    except: pass

def sync_hierarchy_with_content():
    """
    Scan content directory and compare with hierarchy.json.
    Returns (missing_files, new_files) where:
    - missing_files: list of page IDs in hierarchy but not on disk
    - new_files: list of page IDs found on disk but not in hierarchy
    Does NOT auto-add files - caller must decide.
    """
    hierarchy = json.loads(HIERARCHY_FILE.read_text())
    
    # Build set of page IDs from hierarchy
    hierarchy_ids = set()
    for ch in hierarchy:
        for page in ch.get("pages", []):
            hierarchy_ids.add(page["id"])
    
    # Scan content directory for .typ files
    disk_ids = set()
    if CONTENT_DIR.exists():
        for chapter_dir in sorted(CONTENT_DIR.iterdir()):
            if chapter_dir.is_dir() and chapter_dir.name.startswith("chapter"):
                for typ_file in sorted(chapter_dir.glob("*.typ")):
                    page_id = typ_file.stem
                    disk_ids.add(page_id)
    
    missing_files = sorted(hierarchy_ids - disk_ids)
    new_files = sorted(disk_ids - hierarchy_ids)
    
    return missing_files, new_files

def add_files_to_hierarchy(page_ids):
    """Add the given page IDs to hierarchy.json with blank titles."""
    hierarchy = json.loads(HIERARCHY_FILE.read_text())
    
    # Group by chapter prefix
    by_chapter = {}
    for page_id in page_ids:
        ch_prefix = page_id.split(".")[0]
        by_chapter.setdefault(ch_prefix, []).append(page_id)
    
    for ch_prefix, ids in by_chapter.items():
        # Find or create chapter
        target_ch = None
        for ch in hierarchy:
            if ch.get("pages") and ch["pages"][0]["id"].startswith(ch_prefix + "."):
                target_ch = ch
                break
        
        if target_ch is None:
            ch_num = int(ch_prefix)
            target_ch = {"title": "", "summary": "", "pages": []}
            insert_idx = 0
            for i, ch in enumerate(hierarchy):
                if ch.get("pages"):
                    existing_prefix = int(ch["pages"][0]["id"].split(".")[0])
                    if existing_prefix < ch_num:
                        insert_idx = i + 1
            hierarchy.insert(insert_idx, target_ch)
        
        for page_id in sorted(ids):
            if not any(p["id"] == page_id for p in target_ch["pages"]):
                target_ch["pages"].append({"id": page_id, "title": ""})
        
        target_ch["pages"].sort(key=lambda p: p["id"])
    
    HIERARCHY_FILE.write_text(json.dumps(hierarchy, indent=4))

def add_single_file_to_hierarchy(page_id, title):
    """Add a single page ID to hierarchy.json with the given title."""
    try:
        hierarchy = json.loads(HIERARCHY_FILE.read_text())
        ch_prefix = page_id.split(".")[0]
        
        # Find existing chapter with matching prefix
        target_ch = None
        for ch in hierarchy:
            if ch.get("pages"):
                for p in ch["pages"]:
                    if p["id"].startswith(ch_prefix + "."):
                        target_ch = ch
                        break
                if target_ch:
                    break
        
        if target_ch is None:
            # Create new chapter
            ch_num = int(ch_prefix)
            target_ch = {"title": "", "summary": "", "pages": []}
            insert_idx = len(hierarchy)
            for i, ch in enumerate(hierarchy):
                if ch.get("pages"):
                    existing_prefix = int(ch["pages"][0]["id"].split(".")[0])
                    if existing_prefix > ch_num:
                        insert_idx = i
                        break
            hierarchy.insert(insert_idx, target_ch)
        
        if not any(p["id"] == page_id for p in target_ch["pages"]):
            target_ch["pages"].append({"id": page_id, "title": title})
            target_ch["pages"].sort(key=lambda p: p["id"])
        
        HIERARCHY_FILE.write_text(json.dumps(hierarchy, indent=4))
    except Exception:
        pass  # Silently fail rather than crash



def compile_target(target, output, page_offset=None, page_map=None, extra_flags=None, callback=None, log_callback=None):
    cmd = ["typst", "compile", RENDERER_FILE, str(output), "--root", ".", "--input", f"target={target}"]
    if page_offset: cmd.extend(["--input", f"page-offset={page_offset}"])
    if page_map: cmd.extend(["--input", f"page-map={json.dumps(page_map)}"])
    if extra_flags: cmd.extend(extra_flags)
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    all_stderr = []
    
    try:
        # Make stderr non-blocking for real-time output
        fd = proc.stderr.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        
        while proc.poll() is None:
            if callback: callback()
            try:
                chunk = proc.stderr.read(4096)
                if chunk:
                    all_stderr.append(chunk)
                    if log_callback: log_callback(chunk)
            except: pass
            time.sleep(0.05)
        
        # Get any remaining output
        stdout, stderr = proc.communicate()
        if stderr:
            all_stderr.append(stderr)
            if log_callback:
                log_callback(stderr)
        
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, output=stdout, stderr=''.join(all_stderr))
        return ''.join(all_stderr)
    finally:
        # Explicit cleanup
        if proc.stdout: proc.stdout.close()
        if proc.stderr: proc.stderr.close()
        del all_stderr
        gc.collect()

def merge_pdfs(pdf_files, output):
    files = [str(p) for p in pdf_files if p.exists()]
    if not files: return False
    
    if shutil.which("pdfunite"):
        subprocess.run(["pdfunite"] + files + [str(output)], check=True, capture_output=True)
        return "pdfunite"
    elif shutil.which("gs"):
        subprocess.run(["gs", "-dBATCH", "-dNOPAUSE", "-q", "-sDEVICE=pdfwrite", f"-sOutputFile={output}"] + files, check=True, capture_output=True)
        return "ghostscript"
    return None

def zip_build_directory(build_dir, output="build_pdfs.zip"):
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(build_dir):
            for f in files:
                path = Path(root) / f
                z.write(path, path.relative_to(build_dir.parent))

def create_pdf_metadata(chapters, page_map, output_file):
    bookmarks = []
    for key, title in [("cover", "Cover"), ("preface", "Preface"), ("outline", "Table of Contents")]:
        if key in page_map:
            bookmarks.extend([f"BookmarkBegin", f"BookmarkTitle: {title}", f"BookmarkLevel: 1", f"BookmarkPageNumber: {page_map[key]}"])
    
    for ch in chapters:
        ch_id = ch["pages"][0]["id"][:2]
        if f"chapter-{ch_id}" in page_map:
            bookmarks.extend([f"BookmarkBegin", f"BookmarkTitle: {ch['title']}", f"BookmarkLevel: 1", f"BookmarkPageNumber: {page_map[f'chapter-{ch_id}']}"])
        for p in ch["pages"]:
            if p["id"] in page_map:
                bookmarks.extend([f"BookmarkBegin", f"BookmarkTitle: {p['title']}", f"BookmarkLevel: 2", f"BookmarkPageNumber: {page_map[p['id']]}"])
    
    Path(output_file).write_text('\n'.join(bookmarks))

def apply_pdf_metadata(pdf, bookmarks_file, title, author):
    temp = BUILD_DIR / "temp.pdf"
    if shutil.which("pdftk"):
        info = BUILD_DIR / "info.txt"
        info.write_text(f"InfoBegin\nInfoKey: Title\nInfoValue: {title}\nInfoKey: Author\nInfoValue: {author}\n")
        subprocess.run(["pdftk", str(pdf), "update_info", str(info), "output", str(temp)], check=True, capture_output=True)
        temp2 = BUILD_DIR / "temp2.pdf"
        subprocess.run(["pdftk", str(temp), "update_info", str(bookmarks_file), "output", str(temp2)], check=True, capture_output=True)
        shutil.move(temp2, pdf)
        return True
    elif shutil.which("gs"):
        pdfmark = BUILD_DIR / "bookmarks.pdfmark"
        marks = [f"[ /Title ({title}) /Author ({author}) /DOCINFO pdfmark"]
        lines = Path(bookmarks_file).read_text().split('\n')
        i = 0
        while i < len(lines):
            if lines[i].strip() == "BookmarkBegin":
                t = lines[i+1].split(": ", 1)[1] if ": " in lines[i+1] else ""
                pg = lines[i+3].split(": ", 1)[1] if ": " in lines[i+3] else "1"
                marks.append(f"[ /Title ({t}) /Page {pg} /Count 0 /OUT pdfmark")
                i += 4
            else:
                i += 1
        pdfmark.write_text('\n'.join(marks))
        subprocess.run(["gs", "-dBATCH", "-dNOPAUSE", "-q", "-sDEVICE=pdfwrite", f"-sOutputFile={temp}", str(pdf), str(pdfmark)], check=True, capture_output=True)
        shutil.move(temp, pdf)
        return True
    return False

# =============================================================================
# CURSES HELPERS
# =============================================================================

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    for i, color in enumerate([curses.COLOR_CYAN, curses.COLOR_GREEN, curses.COLOR_YELLOW, 
                               curses.COLOR_WHITE, curses.COLOR_MAGENTA, curses.COLOR_RED], 1):
        curses.init_pair(i, color, -1)
    curses.curs_set(0)

def disable_flow_control():
    try:
        fd = sys.stdin.fileno()
        attrs = termios.tcgetattr(fd)
        attrs[0] &= ~(termios.IXON | termios.IXOFF)
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
    except:
        pass

def safe_addstr(scr, y, x, text, attr=0):
    try:
        h, w = scr.getmaxyx()
        if 0 <= y < h and 0 <= x < w:
            scr.addstr(y, x, text[:w - x - 1], attr)
    except curses.error:
        pass

def prompt_save(scr):
    h, w = scr.getmaxyx()
    safe_addstr(scr, h - 1, 2, "Save? (y/n/c): ", curses.color_pair(3) | curses.A_BOLD)
    scr.refresh()
    c = scr.getch()
    return chr(c) if c in (ord('y'), ord('n'), ord('c')) else 'c'

def show_saved(scr):
    h, w = scr.getmaxyx()
    safe_addstr(scr, h - 1, 2, "Saved!", curses.color_pair(2) | curses.A_BOLD)
    scr.refresh()
    curses.napms(500)

def draw_box(scr, y, x, h, w, title=""):
    try:
        scr.addstr(y, x, "╔" + "═" * (w - 2) + "╗")
        for i in range(1, h - 1):
            scr.addstr(y + i, x, "║" + " " * (w - 2) + "║")
        scr.addstr(y + h - 1, x, "╚" + "═" * (w - 2) + "╝")
        if title:
            scr.addstr(y, x + 2, f" {title} ", curses.color_pair(1) | curses.A_BOLD)
    except curses.error:
        pass

def check_terminal_size(scr):
    while True:
        h, w = scr.getmaxyx()
        if h >= MIN_TERM_HEIGHT and w >= MIN_TERM_WIDTH:
            return True
        scr.clear()
        y = h // 2 - 1
        safe_addstr(scr, y, max(0, (w - 19) // 2), "Terminal too small!", curses.color_pair(6) | curses.A_BOLD)
        safe_addstr(scr, y + 1, max(0, (w - 15) // 2), f"Current: {h}×{w}", curses.color_pair(4))
        safe_addstr(scr, y + 2, max(0, (w - 15) // 2), f"Required: {MIN_TERM_HEIGHT}×{MIN_TERM_WIDTH}", curses.color_pair(4) | curses.A_DIM)
        scr.refresh()
        scr.timeout(100)
        if scr.getch() == ord('q'):
            return False
    scr.timeout(-1)

# =============================================================================
# SCREEN DISPLAYS
# =============================================================================

def copy_to_clipboard(text):
    try:
        subprocess.run(["pbcopy"], input=text.encode('utf-8'), check=True)
        return True
    except:
        return False

def show_error_screen(scr, error):
    import traceback
    log = traceback.format_exc()
    if log.strip() == "NoneType: None":
        log = str(error)
    
    view_log = False
    copied = False
    while True:
        scr.clear()
        h, w = scr.getmaxyx()
        
        if view_log:
            header = "ERROR LOG (press 'v' to go back, 'c' to copy)"
            if copied:
                header = "ERROR LOG (copied to clipboard!)"
            safe_addstr(scr, 0, 2, header, curses.color_pair(6) | curses.A_BOLD)
            for i, line in enumerate(log.split('\n')[:h-3]):
                safe_addstr(scr, i + 2, 2, line, curses.color_pair(4))
        else:
            y = max(0, (h - len(SAD_FACE) - 8) // 2)
            for i, line in enumerate(SAD_FACE):
                safe_addstr(scr, y + i, (w - 9) // 2, line, curses.color_pair(6) | curses.A_BOLD)
            
            my = y + len(SAD_FACE) + 2
            safe_addstr(scr, my, (w - 12) // 2, "BUILD FAILED", curses.color_pair(6) | curses.A_BOLD)
            err = str(error)[:w-10]
            safe_addstr(scr, my + 2, (w - len(err)) // 2, err, curses.color_pair(4))
            safe_addstr(scr, my + 4, (w - 50) // 2, "Press 'v' to view log  |  Press any other key to exit", curses.color_pair(4) | curses.A_DIM)
        
        scr.refresh()
        key = scr.getch()
        if key == ord('v'):
            view_log = not view_log
            copied = False
        elif key == ord('c') and view_log:
            copied = copy_to_clipboard(log)
        elif not view_log:
            break

def show_success_screen(scr, page_count, has_warnings=False, typst_logs=None):
    view_log = False
    copied = False
    while True:
        scr.clear()
        h, w = scr.getmaxyx()
        
        if view_log and typst_logs:
            header = "TYPST LOG (press 'v' to go back, 'c' to copy)"
            if copied:
                header = "TYPST LOG (copied to clipboard!)"
            safe_addstr(scr, 0, 2, header, curses.color_pair(3) | curses.A_BOLD)
            for i, line in enumerate(typst_logs[:h-3]):
                c = 6 if 'error:' in line.lower() else 3 if 'warning:' in line.lower() else 4
                safe_addstr(scr, i + 2, 2, line[:w-4], curses.color_pair(c))
        else:
            face = HMM_FACE if has_warnings else HAPPY_FACE
            color = curses.color_pair(3) if has_warnings else curses.color_pair(2)
            
            y = max(0, (h - len(face) - 8) // 2)
            for i, line in enumerate(face):
                safe_addstr(scr, y + i, (w - len(face[0])) // 2, line, color | curses.A_BOLD)
            
            my = y + len(face) + 2
            title = "BUILD SUCCEEDED (with warnings)" if has_warnings else "BUILD SUCCEEDED!"
            safe_addstr(scr, my, (w - len(title)) // 2, title, color | curses.A_BOLD)
            msg = f"Created: {OUTPUT_FILE} ({page_count} pages)"
            safe_addstr(scr, my + 2, (w - len(msg)) // 2, msg, curses.color_pair(4))
            
            if has_warnings:
                hint = "Press 'v' to view log  |  Press any other key to exit"
            else:
                hint = "Press any key to exit..."
            safe_addstr(scr, my + 4, (w - len(hint)) // 2, hint, curses.color_pair(4) | curses.A_DIM)
        
        scr.refresh()
        key = scr.getch()
        if key == ord('v') and has_warnings:
            view_log = not view_log
            copied = False
        elif key == ord('c') and view_log and typst_logs:
            copied = copy_to_clipboard('\n'.join(typst_logs))
        elif not view_log:
            break

# =============================================================================
# BUILD MENU
# =============================================================================

class BuildMenu:
    def __init__(self, scr, hierarchy):
        self.scr, self.hierarchy = scr, hierarchy
        self.typst_flags, self.scroll, self.cursor = [], 0, 0
        
        # Load saved settings
        settings = load_settings()
        self.debug = settings.get('debug', False)
        self.frontmatter = settings.get('frontmatter', True)
        self.leave_pdfs = settings.get('leave_pdfs', False)
        self.typst_flags = settings.get('typst_flags', [])
        saved_pages = set(tuple(p) for p in settings.get('selected_pages', []))
        
        self.items, self.selected = [], {}
        for ci, ch in enumerate(hierarchy):
            self.items.append(('ch', ci, None))
            for ai in range(len(ch["pages"])):
                self.items.append(('art', ci, ai))
                # Use saved selection if available, else default to True
                self.selected[(ci, ai)] = (ci, ai) in saved_pages if saved_pages else True
        
        init_colors()
        self.h, self.w = scr.getmaxyx()
    
    def ch_selected(self, ci):
        return all(self.selected.get((ci, ai), False) for ai in range(len(self.hierarchy[ci]["pages"])))
    
    def ch_partial(self, ci):
        cnt = sum(1 for ai in range(len(self.hierarchy[ci]["pages"])) if self.selected.get((ci, ai)))
        return 0 < cnt < len(self.hierarchy[ci]["pages"])
    
    def toggle_ch(self, ci):
        v = not self.ch_selected(ci)
        for ai in range(len(self.hierarchy[ci]["pages"])):
            self.selected[(ci, ai)] = v
    
    def refresh(self):
        self.h, self.w = self.scr.getmaxyx()
        self.scr.clear()
        
        lh, obh = len(LOGO), 7
        layout = "vert" if self.h >= lh + 3 + obh + 7 else ("horz" if self.h >= lh + 3 + obh and self.w >= 90 else "compact" if self.w >= 90 else "vert")
        
        def items(by, bx, bw, rows):
            vr = rows - 2
            if self.cursor < self.scroll: self.scroll = self.cursor
            elif self.cursor >= self.scroll + vr: self.scroll = self.cursor - vr + 1
            
            for r in range(vr):
                idx = self.scroll + r
                if idx >= len(self.items): break
                t, ci, ai = self.items[idx]
                y = by + 1 + r
                cur = idx == self.cursor
                
                if cur: safe_addstr(self.scr, y, bx + 2, "▶", curses.color_pair(3) | curses.A_BOLD)
                
                if t == 'ch':
                    ch = self.hierarchy[ci]
                    cb = "[✓]" if self.ch_selected(ci) else "[~]" if self.ch_partial(ci) else "[ ]"
                    cc = 2 if self.ch_selected(ci) else 3 if self.ch_partial(ci) else 4
                    safe_addstr(self.scr, y, bx + 4, cb, curses.color_pair(cc))
                    ch_num = ch['pages'][0]['id'][:2] if ch.get('pages') else f"{ci+1:02d}"
                    safe_addstr(self.scr, y, bx + 7, f" Ch {ch_num}: {ch['title']}"[:bw-12], curses.color_pair(1))
                else:
                    p = self.hierarchy[ci]["pages"][ai]
                    sel = self.selected.get((ci, ai), False)
                    safe_addstr(self.scr, y, bx + 6, "[✓]" if sel else "[ ]", curses.color_pair(2 if sel else 4))
                    safe_addstr(self.scr, y, bx + 9, f" {p['id']}: {p['title']}"[:bw-14], curses.color_pair(4))
        
        def opts(sy, bx, bw):
            for i, (lbl, val, key) in enumerate([
                ("Debug Mode:", self.debug, "d"), ("Frontmatter:", self.frontmatter, "f"), ("Leave PDFs:", self.leave_pdfs, "l")
            ]):
                safe_addstr(self.scr, sy + 1 + i, bx + 2, f"{lbl:14}", curses.color_pair(4))
                safe_addstr(self.scr, sy + 1 + i, bx + 16, "[ON] " if val else "[OFF]", curses.color_pair(2 if val else 6) | curses.A_BOLD)
                safe_addstr(self.scr, sy + 1 + i, bx + 22, f"({key})", curses.color_pair(4) | curses.A_DIM)
            
            flags = " ".join(self.typst_flags) or "(none)"
            safe_addstr(self.scr, sy + 4, bx + 2, "Typst Flags:  ", curses.color_pair(4))
            safe_addstr(self.scr, sy + 4, bx + 16, flags[:bw-20], curses.color_pair(5 if self.typst_flags else 4) | curses.A_DIM)
            safe_addstr(self.scr, sy + 5, bx + 16, "(c)", curses.color_pair(4) | curses.A_DIM)
        
        if layout == "compact":
            lw, rw = 20, min(50, self.w - 24)
            lx = (self.w - lw - rw - 2) // 2
            rx = lx + lw + 2
            ly = max(0, (self.h - lh) // 2 - 1)
            for i, line in enumerate(LOGO[:self.h-1]):
                safe_addstr(self.scr, ly + i, lx + 3, line, curses.color_pair(1) | curses.A_BOLD)
            safe_addstr(self.scr, ly + lh, lx + (lw - 10) // 2, "NOTEWORTHY", curses.color_pair(1) | curses.A_BOLD)
            draw_box(self.scr, 0, rx, obh, rw, "Options")
            opts(0, rx, rw)
            ch = max(3, self.h - obh - 3)
            draw_box(self.scr, obh + 1, rx, ch, rw, "Select Chapters")
            items(obh + 1, rx, rw, ch)
        elif layout == "horz":
            total_h = lh + 2 + obh
            start_y = max(0, (self.h - total_h - 2) // 2)
            lbw, rbw = min(40, (self.w - 6) // 2), min(50, (self.w - 6) // 2)
            lx = (self.w - lbw - rbw - 2) // 2
            rx = lx + lbw + 2
            lgx = lx + (lbw - 14) // 2
            for i, line in enumerate(LOGO[:self.h-2]):
                safe_addstr(self.scr, start_y + i, lgx, line, curses.color_pair(1) | curses.A_BOLD)
            safe_addstr(self.scr, start_y + lh, lx + (lbw - 10) // 2, "NOTEWORTHY", curses.color_pair(1) | curses.A_BOLD)
            draw_box(self.scr, start_y + lh + 2, lx, obh, lbw, "Options")
            opts(start_y + lh + 2, lx, lbw)
            ch = min(lh + 2 + obh, self.h - 2)
            draw_box(self.scr, start_y, rx, ch, rbw, "Select Chapters")
            items(start_y, rx, rbw, ch)
        else:
            ch_rows = min(len(self.items) + 2, 10)
            total_h = lh + 2 + obh + 1 + ch_rows + 2
            start_y = max(0, (self.h - total_h) // 2)
            lgx = (self.w - 14) // 2
            for i, line in enumerate(LOGO):
                safe_addstr(self.scr, start_y + i, lgx, line, curses.color_pair(1) | curses.A_BOLD)
            safe_addstr(self.scr, start_y + lh + 1, (self.w - 10) // 2, "NOTEWORTHY", curses.color_pair(1) | curses.A_BOLD)
            bw, bx = min(60, self.w - 4), (self.w - min(60, self.w - 4)) // 2
            draw_box(self.scr, start_y + lh + 3, bx, obh, bw, "Options")
            opts(start_y + lh + 3, bx, bw)
            cy = start_y + lh + 3 + obh + 1
            ch = min(len(self.items) + 2, self.h - cy - 3)
            draw_box(self.scr, cy, bx, ch, bw, "Select Chapters")
            items(cy, bx, bw, ch)
        
        safe_addstr(self.scr, self.h - 1, (self.w - 78) // 2, "e:Configure  |  ↑↓:Nav  Space:Toggle  a:All  n:None  Enter:Build  Esc/q:Quit", curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
    
    def run(self):
        self.refresh()
        while True:
            if not check_terminal_size(self.scr): return None
            
            k = self.scr.getch()
            if k in (ord('q'), 27): return None  # q or Esc
            elif k in (ord('\n'), curses.KEY_ENTER, 10):
                result = {'selected_pages': [(ci, ai) for ci in range(len(self.hierarchy)) for ai in range(len(self.hierarchy[ci]["pages"])) if self.selected.get((ci, ai))],
                          'debug': self.debug, 'frontmatter': self.frontmatter, 'leave_individual': self.leave_pdfs, 'typst_flags': self.typst_flags}
                # Save settings for next time
                save_settings({'debug': self.debug, 'frontmatter': self.frontmatter, 'leave_pdfs': self.leave_pdfs,
                               'typst_flags': self.typst_flags, 'selected_pages': result['selected_pages']})
                return result
            elif k in (curses.KEY_UP, ord('k')): self.cursor = max(0, self.cursor - 1)
            elif k in (curses.KEY_DOWN, ord('j')): self.cursor = min(len(self.items) - 1, self.cursor + 1)
            elif k == ord(' '):
                t, ci, ai = self.items[self.cursor]
                if t == 'ch': self.toggle_ch(ci)
                else: self.selected[(ci, ai)] = not self.selected.get((ci, ai), False)
            elif k == ord('a'):
                for ci in range(len(self.hierarchy)):
                    for ai in range(len(self.hierarchy[ci]["pages"])): self.selected[(ci, ai)] = True
            elif k == ord('n'):
                for ci in range(len(self.hierarchy)):
                    for ai in range(len(self.hierarchy[ci]["pages"])): self.selected[(ci, ai)] = False
            elif k == ord('d'): self.debug = not self.debug
            elif k == ord('f'): self.frontmatter = not self.frontmatter
            elif k == ord('l'): self.leave_pdfs = not self.leave_pdfs
            elif k == ord('c'): self.configure_flags()
            elif k == ord('e'):
                show_editor_menu(self.scr)
            self.refresh()
    
    def configure_flags(self):
        curses.echo()
        curses.curs_set(1)
        dh, dw = 10, min(60, self.w - 4)
        dy, dx = (self.h - dh) // 2, (self.w - dw) // 2
        d = curses.newwin(dh, dw, dy, dx)
        d.box()
        d.addstr(0, 2, " Typst Flags ", curses.color_pair(1) | curses.A_BOLD)
        d.addstr(2, 2, "Current: " + (" ".join(self.typst_flags) or "(none)")[:dw-12])
        d.addstr(4, 2, "1. --font-path /path  2. --ppi 144  3. Clear")
        d.addstr(6, 2, "Enter flags or preset: ")
        d.refresh()
        s = d.getstr(6, 25, dw - 27).decode('utf-8').strip()
        if s == "1":
            d.addstr(7, 2, "Font path: ")
            d.refresh()
            p = d.getstr(7, 13, dw - 15).decode('utf-8').strip()
            if p: self.typst_flags = ["--font-path", p]
        elif s == "2": self.typst_flags = ["--ppi", "144"]
        elif s == "3": self.typst_flags = []
        elif s: self.typst_flags = s.split()
        curses.noecho()
        curses.curs_set(0)


# =============================================================================
# EDITORS
# =============================================================================

def extract_themes():
    try:
        schemes = json.loads(SCHEMES_FILE.read_text())
        return list(schemes.keys())
    except:
        return ["dark", "light", "rose-pine", "nord", "dracula", "gruvbox"]

def hex_to_curses_color(hex_color):
    if not hex_color or not hex_color.startswith('#'): return 4
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        lum = (0.299 * r + 0.587 * g + 0.114 * b)
        if lum > 180: return 4
        if r > g and r > b: return 6
        if g > r and g > b: return 2
        if b > r and b > g: return 1
        if r > 150 and g > 100: return 3
        return 5
    except:
        return 4

def show_editor_menu(scr):
    init_colors()
    disable_flow_control()  # Allow Ctrl+S to work in editors
    cursor = 0
    options = [
        ("1", "Config Editor", "Document settings"),
        ("2", "Hierarchy Editor", "Chapter/page structure"),
        ("3", "Scheme Editor", "Color themes"),
        ("4", "Preface Editor", "Preface content"),
        ("5", "Snippets Editor", "Custom macros"),
        ("6", "Indexignore Editor", "Ignored files"),
    ]
    
    while True:
        h, w = scr.getmaxyx()
        scr.clear()
        
        # Calculate layout - vertically centered
        title_h = 2
        list_h = len(options) + 2
        total_h = title_h + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        
        safe_addstr(scr, start_y, (w - 14) // 2, "SELECT EDITOR", curses.color_pair(1) | curses.A_BOLD)
        
        bw = min(55, w - 4)
        bx = (w - bw) // 2
        draw_box(scr, start_y + 2, bx, list_h, bw, "Editors")
        
        for i, (key, name, desc) in enumerate(options):
            y = start_y + 3 + i
            if i == cursor:
                safe_addstr(scr, y, bx + 2, ">", curses.color_pair(3) | curses.A_BOLD)
            safe_addstr(scr, y, bx + 4, f"{key}. {name}", curses.color_pair(4) | (curses.A_BOLD if i == cursor else 0))
            safe_addstr(scr, y, bx + 25, desc[:bw-27], curses.color_pair(4) | curses.A_DIM)
        
        safe_addstr(scr, h - 1, (w - 32) // 2, "↑↓:Nav  Enter:Select  Esc/q:Back", curses.color_pair(4) | curses.A_DIM)
        scr.refresh()
        
        k = scr.getch()
        if k in (ord('q'), 27):  # q or Esc
            return
        elif k in (curses.KEY_UP, ord('k')): cursor = max(0, cursor - 1)
        elif k in (curses.KEY_DOWN, ord('j')): cursor = min(len(options) - 1, cursor + 1)
        elif k in (ord('\n'), curses.KEY_ENTER, 10) or (ord('1') <= k <= ord('6')):
            idx = k - ord('1') if ord('1') <= k <= ord('6') else cursor
            if idx == 0: ConfigEditor(scr).run()
            elif idx == 1: HierarchyEditor(scr).run()
            elif idx == 2: SchemeEditor(scr).run()
            elif idx == 3: TextEditor(scr, PREFACE_FILE, "Preface Editor").run()
            elif idx == 4: SnippetsEditor(scr).run()
            elif idx == 5: IndexignoreEditor(scr).run()


class TextEditor:
    def __init__(self, scr, filepath=None, title="Editor", initial_text=None):
        self.scr = scr
        self.filepath = filepath
        self.title = title
        
        if initial_text is not None:
            self.lines = initial_text.split('\n')
        elif filepath and filepath.exists():
            self.lines = filepath.read_text().split('\n')
        else:
            self.lines = [""]
            
        self.cy, self.cx = 0, 0 # Logical cursor position
        self.sy = 0 # Visual scroll offset
        self.modified = False
        init_colors()
        
    def _get_visual_lines(self, width):
        visual_lines = []
        for i, line in enumerate(self.lines):
            if not line:
                visual_lines.append(("", i, 0))
                continue
                
            curr = 0
            while curr < len(line):
                # Find split point
                rem_len = len(line) - curr
                if rem_len <= width:
                    visual_lines.append((line[curr:], i, curr))
                    break
                
                # Soft wrap logic
                limit = curr + width
                sub = line[curr:limit]
                last_space = sub.rfind(' ')
                
                if last_space != -1:
                    split = curr + last_space + 1
                else:
                    split = limit
                    
                visual_lines.append((line[curr:split], i, curr))
                curr = split
        return visual_lines

    def save(self):
        if self.filepath:
            try:
                self.filepath.write_text('\n'.join(self.lines))
                self.modified = False
                return True
            except: return False
        else:
            return '\n'.join(self.lines)
    
    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        fname = self.filepath.name if self.filepath else "New Text"
        header = f" {self.title} - {fname} "
        if self.modified: header = "* " + header
        safe_addstr(self.scr, 0, 0, "─" * w, curses.color_pair(1))
        safe_addstr(self.scr, 0, 2, header, curses.color_pair(1) | curses.A_BOLD)
        
        # Calculate layout
        content_w = w - 6 # 4 chars for line num, 1 space, 1 margin
        visual_lines = self._get_visual_lines(content_w)
        
        # Find visual cursor position
        vcy, vcx = 0, 0
        for i, (text, l_idx, start_idx) in enumerate(visual_lines):
            if l_idx == self.cy:
                if self.cx >= start_idx and self.cx <= start_idx + len(text):
                    # Found the line containing cursor
                    # Special case: if cursor is at exact end of a wrapped line (not last part), 
                    # it should technically be on next line? No, typical behavior is end of line.
                    # But if self.cx == start_idx + len(text) and it's not the last chunk...
                    # Let's stick to: cursor stays on the chunk where it fits.
                    # If it's exactly at split point, prefer next line?
                    # Actually, standard is: if I type at end of line, it wraps.
                    # If self.cx == start_idx + len(text) and there is a next chunk for same line,
                    # then cursor should be at start of next chunk.
                    
                    is_last_chunk = True
                    if i + 1 < len(visual_lines):
                        next_l_idx = visual_lines[i+1][1]
                        if next_l_idx == l_idx: is_last_chunk = False
                    
                    if self.cx == start_idx + len(text) and not is_last_chunk:
                        continue # Match on next chunk
                        
                    vcy = i
                    vcx = self.cx - start_idx
                    break
        
        # Scroll
        ch = h - 3
        if vcy < self.sy: self.sy = vcy
        elif vcy >= self.sy + ch: self.sy = vcy - ch + 1
        
        # Draw
        for i in range(ch):
            idx = self.sy + i
            if idx >= len(visual_lines): break
            
            text, l_idx, start_idx = visual_lines[idx]
            y = 1 + i
            
            # Line number only for first chunk
            if start_idx == 0:
                safe_addstr(self.scr, y, 0, f"{l_idx + 1:4} ", curses.color_pair(4) | curses.A_DIM)
            else:
                safe_addstr(self.scr, y, 0, "     ", curses.color_pair(4))
                
            safe_addstr(self.scr, y, 5, text, curses.color_pair(4))
        
        safe_addstr(self.scr, h - 2, 0, "─" * w, curses.color_pair(1))
        safe_addstr(self.scr, h - 1, 2, f"^S:Save  ^X:Exit  Ln {self.cy + 1}, Col {self.cx + 1}", curses.color_pair(4) | curses.A_DIM)
        
        # Move cursor
        screen_y = 1 + vcy - self.sy
        screen_x = 5 + vcx
        if 1 <= screen_y < h - 2 and 5 <= screen_x < w:
            try: self.scr.move(screen_y, screen_x)
            except: pass
        self.scr.refresh()
        
        return visual_lines # Return for use in run()

    def run(self):
        curses.curs_set(1)
        disable_flow_control()  # Allow Ctrl+S to work
        while True:
            visual_lines = self.refresh()
            k = self.scr.getch()
            
            if k == 24:  # Ctrl+X
                if self.modified:
                    h, w = self.scr.getmaxyx()
                    safe_addstr(self.scr, h - 1, 2, "Save? (y/n/c): ", curses.color_pair(3) | curses.A_BOLD)
                    self.scr.refresh()
                    c = self.scr.getch()
                    if c == ord('y'):
                        res = self.save()
                        if not self.filepath: return res
                        return True
                    elif c == ord('c'): continue
                return None if not self.filepath else True
            elif k == 19:  # Ctrl+S
                res = self.save()
                if res:
                    h, w = self.scr.getmaxyx()
                    safe_addstr(self.scr, h - 1, 2, "Saved!", curses.color_pair(2) | curses.A_BOLD)
                    self.scr.refresh(); curses.napms(500)
                    if not self.filepath: return res
            
            # Navigation
            elif k == curses.KEY_UP:
                # Find current visual line index
                vcy = 0
                for i, (text, l_idx, start_idx) in enumerate(visual_lines):
                    if l_idx == self.cy:
                        is_last_chunk = True
                        if i + 1 < len(visual_lines) and visual_lines[i+1][1] == l_idx: is_last_chunk = False
                        if self.cx >= start_idx and (self.cx < start_idx + len(text) or (self.cx == start_idx + len(text) and is_last_chunk)):
                            vcy = i; break
                
                if vcy > 0:
                    target_vcy = vcy - 1
                    t_text, t_lidx, t_start = visual_lines[target_vcy]
                    # Try to keep same visual x offset
                    curr_vx = self.cx - visual_lines[vcy][2]
                    self.cy = t_lidx
                    self.cx = t_start + min(curr_vx, len(t_text))
                    
            elif k == curses.KEY_DOWN:
                vcy = 0
                for i, (text, l_idx, start_idx) in enumerate(visual_lines):
                    if l_idx == self.cy:
                        is_last_chunk = True
                        if i + 1 < len(visual_lines) and visual_lines[i+1][1] == l_idx: is_last_chunk = False
                        if self.cx >= start_idx and (self.cx < start_idx + len(text) or (self.cx == start_idx + len(text) and is_last_chunk)):
                            vcy = i; break
                            
                if vcy < len(visual_lines) - 1:
                    target_vcy = vcy + 1
                    t_text, t_lidx, t_start = visual_lines[target_vcy]
                    curr_vx = self.cx - visual_lines[vcy][2]
                    self.cy = t_lidx
                    self.cx = t_start + min(curr_vx, len(t_text))
            
            elif k == curses.KEY_LEFT:
                if self.cx > 0: self.cx -= 1
                elif self.cy > 0: self.cy -= 1; self.cx = len(self.lines[self.cy])
            elif k == curses.KEY_RIGHT:
                if self.cx < len(self.lines[self.cy]): self.cx += 1
                elif self.cy < len(self.lines) - 1: self.cy += 1; self.cx = 0
            elif k == curses.KEY_HOME: self.cx = 0
            elif k == curses.KEY_END: self.cx = len(self.lines[self.cy])
            
            # Editing
            elif k in (curses.KEY_BACKSPACE, 127, 8):
                if self.cx > 0:
                    self.lines[self.cy] = self.lines[self.cy][:self.cx-1] + self.lines[self.cy][self.cx:]
                    self.cx -= 1; self.modified = True
                elif self.cy > 0:
                    pl = len(self.lines[self.cy - 1])
                    self.lines[self.cy - 1] += self.lines[self.cy]
                    del self.lines[self.cy]; self.cy -= 1; self.cx = pl; self.modified = True
            elif k == curses.KEY_DC:
                if self.cx < len(self.lines[self.cy]):
                    self.lines[self.cy] = self.lines[self.cy][:self.cx] + self.lines[self.cy][self.cx+1:]
                    self.modified = True
                elif self.cy < len(self.lines) - 1:
                    self.lines[self.cy] += self.lines[self.cy + 1]
                    del self.lines[self.cy + 1]; self.modified = True
            elif k in (ord('\n'), 10):
                self.lines.insert(self.cy + 1, self.lines[self.cy][self.cx:])
                self.lines[self.cy] = self.lines[self.cy][:self.cx]
                self.cy += 1; self.cx = 0; self.modified = True
            elif k == 9: # Tab
                self.lines[self.cy] = self.lines[self.cy][:self.cx] + "    " + self.lines[self.cy][self.cx:]
                self.cx += 4; self.modified = True
            elif 32 <= k <= 126:
                self.lines[self.cy] = self.lines[self.cy][:self.cx] + chr(k) + self.lines[self.cy][self.cx:]
                self.cx += 1; self.modified = True
        curses.curs_set(0)


class ConfigEditor:
    def __init__(self, scr):
        self.scr = scr
        self.config = json.loads(CONFIG_FILE.read_text())
        self.cursor, self.scroll, self.modified = 0, 0, False
        themes = extract_themes()
        self.fields = [
            ("title", "Title", "str"), ("subtitle", "Subtitle", "str"),
            ("authors", "Authors", "list"), ("affiliation", "Affiliation", "str"),
            ("font", "Body Font", "str"), ("title-font", "Title Font", "str"),
            ("display-mode", "Theme", "choice", themes),
            ("show-solution", "Show Solutions", "bool"),
            ("display-cover", "Display Cover", "bool"),
            ("display-outline", "Display Outline", "bool"),
            ("display-chap-cover", "Chapter Covers", "bool"),
            ("chapter-name", "Chapter Label", "str"), ("subchap-name", "Section Label", "str"),
            ("box-margin", "Box Margin", "str"), ("box-inset", "Box Inset", "str"),
            ("render-sample-count", "Render Samples", "int"),
        ]
        init_colors()
    
    def get_display(self, key):
        v = self.config.get(key)
        if v is None: return "(none)"
        if isinstance(v, bool): return "ON" if v else "OFF"
        if isinstance(v, list): return ", ".join(str(x) for x in v)
        return str(v)
    
    def save(self):
        try:
            CONFIG_FILE.write_text(json.dumps(self.config, indent=4))
            self.modified = False; return True
        except: return False
    
    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        # Calculate layout - vertically centered
        title_h = 2
        list_h = min(len(self.fields) + 2, h - 6)
        total_h = title_h + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        
        # Title
        safe_addstr(self.scr, start_y, (w - 14) // 2, "CONFIG EDITOR", curses.color_pair(1) | curses.A_BOLD)
        
        bw, bx = min(70, w - 4), (w - min(70, w - 4)) // 2
        draw_box(self.scr, start_y + 2, bx, list_h, bw, "Settings")
        
        vis = list_h - 2
        if self.cursor < self.scroll: self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis: self.scroll = self.cursor - vis + 1
        
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.fields): break
            f = self.fields[idx]; key, label, ftype = f[0], f[1], f[2]
            y = start_y + 3 + i; cur = idx == self.cursor
            
            if cur: safe_addstr(self.scr, y, bx + 2, ">", curses.color_pair(3) | curses.A_BOLD)
            safe_addstr(self.scr, y, bx + 4, f"{label}:", curses.color_pair(4))
            
            val_x = bx + 22
            val = self.get_display(key)
            if ftype == "bool":
                c = curses.color_pair(2) if self.config.get(key) else curses.color_pair(6)
                safe_addstr(self.scr, y, val_x, val, c | curses.A_BOLD)
            elif ftype == "choice":
                safe_addstr(self.scr, y, val_x, val[:bw-26], curses.color_pair(5) | curses.A_BOLD)
            else:
                safe_addstr(self.scr, y, val_x, val[:bw-26], curses.color_pair(4))
        
        footer = "* ↑↓:Nav  Enter:Edit  Space:Toggle  s:Save  Esc/q:Back" if self.modified else "↑↓:Nav  Enter:Edit  Space:Toggle  s:Save  Esc/q:Back"
        safe_addstr(self.scr, h - 1, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
    
    def run(self):
        self.refresh()
        while True:
            k = self.scr.getch()
            
            if k in (ord('q'), 27):  # q or Esc
                if self.modified:
                    c = prompt_save(self.scr)
                    if c == 'y': self.save()
                    elif c == 'c': self.refresh(); continue
                return
            elif k in (curses.KEY_UP, ord('k')): self.cursor = max(0, self.cursor - 1)
            elif k in (curses.KEY_DOWN, ord('j')): self.cursor = min(len(self.fields) - 1, self.cursor + 1)
            elif k in (ord('\n'), 10):
                f = self.fields[self.cursor]; key, ftype = f[0], f[2]
                if ftype == "bool":
                    self.config[key] = not self.config.get(key, False); self.modified = True
                elif ftype == "choice":
                    opts = f[3]; cur = self.config.get(key, opts[0])
                    try: ni = (opts.index(cur) + 1) % len(opts)
                    except: ni = 0
                    self.config[key] = opts[ni]; self.modified = True
                else:
                    curr_val = self.config.get(key)
                    if isinstance(curr_val, list): curr_str = ", ".join(str(x) for x in curr_val)
                    else: curr_str = str(curr_val) if curr_val is not None else ""
                    
                    new_val = TextEditor(self.scr, initial_text=curr_str, title=f"Edit {f[1]}").run()
                    
                    if new_val is not None:
                        if ftype == "int":
                            try: self.config[key] = int(new_val)
                            except: pass
                        elif ftype == "list":
                            # Handle both commas and newlines as separators
                            cleaned_val = new_val.replace('\n', ',')
                            self.config[key] = [s.strip() for s in cleaned_val.split(",") if s.strip()]
                        elif new_val.lower() in ("none", "null", ""): self.config[key] = None
                        else: self.config[key] = new_val
                        self.modified = True
            elif k == ord(' '):
                f = self.fields[self.cursor]
                if f[2] == "bool": self.config[f[0]] = not self.config.get(f[0], False); self.modified = True
                elif f[2] == "choice":
                    opts = f[3]; cur = self.config.get(f[0], opts[0])
                    try: ni = (opts.index(cur) + 1) % len(opts)
                    except: ni = 0
                    self.config[f[0]] = opts[ni]; self.modified = True
            elif k == ord('s') and self.save():
                show_saved(self.scr)
            self.refresh()


class IndexignoreEditor:
    """Simple editor for .indexignore file - list of ignored file IDs."""
    def __init__(self, scr):
        self.scr = scr
        self.items = sorted(load_indexignore())
        self.cursor = 0
        self.scroll = 0
        self.modified = False
        init_colors()
    
    def save(self):
        save_indexignore(set(self.items))
        self.modified = False
        return True
    
    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        bw = min(50, w - 4)
        bh = min(h - 6, 20)
        bx = (w - bw) // 2
        by = (h - bh) // 2
        
        draw_box(self.scr, by, bx, bh, bw, " Indexignore Editor ")
        
        safe_addstr(self.scr, by + 1, bx + 2, f"Ignored files: {len(self.items)}", curses.color_pair(4) | curses.A_DIM)
        
        visible = bh - 5
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + visible:
            self.scroll = self.cursor - visible + 1
        
        if not self.items:
            safe_addstr(self.scr, by + 3, bx + 4, "(no ignored files)", curses.color_pair(4) | curses.A_DIM)
        else:
            for i in range(visible):
                idx = self.scroll + i
                if idx >= len(self.items):
                    break
                y = by + 3 + i
                item = self.items[idx]
                if idx == self.cursor:
                    safe_addstr(self.scr, y, bx + 2, ">", curses.color_pair(3) | curses.A_BOLD)
                    safe_addstr(self.scr, y, bx + 4, item, curses.color_pair(1) | curses.A_BOLD)
                else:
                    safe_addstr(self.scr, y, bx + 4, item, curses.color_pair(4))
        
        footer = "a:Add  d:Delete  s:Save  q:Quit"
        safe_addstr(self.scr, by + bh - 1, bx + (bw - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        
        self.scr.refresh()
    
    def run(self):
        while True:
            self.refresh()
            k = self.scr.getch()
            
            if k in (ord('q'), 27):
                if self.modified:
                    # Ask to save
                    pass  # For simplicity, just exit
                return
            elif k in (curses.KEY_UP, ord('k')) and self.items:
                self.cursor = max(0, self.cursor - 1)
            elif k in (curses.KEY_DOWN, ord('j')) and self.items:
                self.cursor = min(len(self.items) - 1, self.cursor + 1)
            elif k == ord('a'):
                # Add new item
                curses.echo()
                curses.curs_set(1)
                h, w = self.scr.getmaxyx()
                self.scr.addstr(h - 2, 2, "Enter file ID to ignore: ")
                self.scr.clrtoeol()
                self.scr.refresh()
                try:
                    new_id = self.scr.getstr(h - 2, 27, 20).decode('utf-8').strip()
                    if new_id and new_id not in self.items:
                        self.items.append(new_id)
                        self.items.sort()
                        self.modified = True
                except:
                    pass
                curses.noecho()
                curses.curs_set(0)
            elif k == ord('d') and self.items:
                del self.items[self.cursor]
                self.cursor = min(self.cursor, len(self.items) - 1) if self.items else 0
                self.modified = True
            elif k == ord('s'):
                self.save()
                show_saved(self.scr)


class HierarchyEditor:
    def __init__(self, scr):
        self.scr = scr
        self.hierarchy = json.loads(HIERARCHY_FILE.read_text())
        self.cursor, self.scroll, self.modified = 0, 0, False
        self.items = []
        self._build_items()
        init_colors()
    
    def _build_items(self):
        self.items = []
        for ci, ch in enumerate(self.hierarchy):
            self.items.append(("ch_title", ci, None, ch.get("title", "")))
            self.items.append(("ch_summary", ci, None, ch.get("summary", "")))
            for pi, pg in enumerate(ch.get("pages", [])):
                self.items.append(("pg_id", ci, pi, pg.get("id", "")))
                self.items.append(("pg_title", ci, pi, pg.get("title", "")))
            # Add "new page" option after each chapter's pages
            self.items.append(("add_page", ci, None, None))
        # Add "new chapter" option at the end
        self.items.append(("add_chapter", None, None, None))
    
    def _get_value(self, item):
        t, ci, pi, _ = item
        if t == "ch_title": return self.hierarchy[ci].get("title", "")
        if t == "ch_summary":
            s = self.hierarchy[ci].get("summary", "")
            return s[:40] + "..." if len(s) > 40 else s
        if t == "pg_id": return self.hierarchy[ci]["pages"][pi].get("id", "")
        if t == "pg_title": return self.hierarchy[ci]["pages"][pi].get("title", "")
        return ""
    
    def _set_value(self, val):
        t, ci, pi, _ = self.items[self.cursor]
        if t == "ch_title": self.hierarchy[ci]["title"] = val
        elif t == "ch_summary": self.hierarchy[ci]["summary"] = val
        elif t == "pg_id": self.hierarchy[ci]["pages"][pi]["id"] = val
        elif t == "pg_title": self.hierarchy[ci]["pages"][pi]["title"] = val
        self.modified = True; self._build_items()
    
    def _add_chapter(self):
        new_ch = {"title": "New Chapter", "summary": "", "pages": []}
        self.hierarchy.append(new_ch)
        self.modified = True
        self._build_items()
        # Move cursor to the new chapter title
        for i, item in enumerate(self.items):
            if item[0] == "ch_title" and item[1] == len(self.hierarchy) - 1:
                self.cursor = i
                break
    
    def _add_page(self, ci):
        # Generate a new page ID
        existing_ids = [p["id"] for ch in self.hierarchy for p in ch.get("pages", [])]
        ch_prefix = f"{ci+1:02d}"
        page_num = 1
        while f"{ch_prefix}.{page_num:02d}" in existing_ids:
            page_num += 1
        new_id = f"{ch_prefix}.{page_num:02d}"
        
        new_page = {"id": new_id, "title": "New Page"}
        self.hierarchy[ci]["pages"].append(new_page)
        self.modified = True
        self._build_items()
        
        # Create actual .typ file on disk
        chapter_dir = CONTENT_DIR / f"chapter {ch_prefix}"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        typ_file = chapter_dir / f"{new_id}.typ"
        if not typ_file.exists():
            typ_file.write_text(f'// Section {new_id}\n\n#import "/templates/setup.typ": *\n\n')
    
    def _delete_current(self):
        t, ci, pi, _ = self.items[self.cursor]
        if t in ("ch_title", "ch_summary"):
            # Delete entire chapter
            if len(self.hierarchy) > 1:  # Keep at least one chapter
                del self.hierarchy[ci]
                self.modified = True
                self._build_items()
                self.cursor = min(self.cursor, len(self.items) - 1)
        elif t in ("pg_id", "pg_title"):
            # Delete page
            del self.hierarchy[ci]["pages"][pi]
            self.modified = True
            self._build_items()
            self.cursor = min(self.cursor, len(self.items) - 1)
    
    def save(self):
        try:
            HIERARCHY_FILE.write_text(json.dumps(self.hierarchy, indent=4))
            self.modified = False; return True
        except: return False
    
    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        title_h = 2
        list_h = min(len(self.items) + 2, h - 6)
        total_h = title_h + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        
        safe_addstr(self.scr, start_y, (w - 18) // 2, "HIERARCHY EDITOR", curses.color_pair(1) | curses.A_BOLD)
        
        bw, bx = min(75, w - 4), (w - min(75, w - 4)) // 2
        draw_box(self.scr, start_y + 2, bx, list_h, bw, "Structure")
        
        vis = list_h - 2
        if self.cursor < self.scroll: self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis: self.scroll = self.cursor - vis + 1
        
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.items): break
            item = self.items[idx]; t, ci, pi, _ = item
            y = start_y + 3 + i; cur = idx == self.cursor
            
            if cur: safe_addstr(self.scr, y, bx + 2, ">", curses.color_pair(3) | curses.A_BOLD)
            
            if t == "ch_title":
                safe_addstr(self.scr, y, bx + 4, f"Ch {ci+1} Title:", curses.color_pair(1) | curses.A_BOLD)
                safe_addstr(self.scr, y, bx + 18, self._get_value(item)[:bw-22], curses.color_pair(4))
            elif t == "ch_summary":
                safe_addstr(self.scr, y, bx + 4, "  Summary:", curses.color_pair(4))
                safe_addstr(self.scr, y, bx + 18, self._get_value(item)[:bw-22], curses.color_pair(4))
            elif t == "pg_id":
                safe_addstr(self.scr, y, bx + 6, "Page ID:", curses.color_pair(5))
                safe_addstr(self.scr, y, bx + 18, self._get_value(item)[:bw-22], curses.color_pair(4))
            elif t == "pg_title":
                safe_addstr(self.scr, y, bx + 6, "  Title:", curses.color_pair(4))
                safe_addstr(self.scr, y, bx + 18, self._get_value(item)[:bw-22], curses.color_pair(4))
            elif t == "add_page":
                safe_addstr(self.scr, y, bx + 6, "+ Add page to this chapter...", curses.color_pair(3 if cur else 4) | curses.A_DIM)
            elif t == "add_chapter":
                safe_addstr(self.scr, y, bx + 4, "+ Add new chapter...", curses.color_pair(3 if cur else 4) | curses.A_DIM)
        
        footer = "* ↑↓:Nav  Enter:Edit/Add  d:Delete  s:Save  Esc/q:Back" if self.modified else "↑↓:Nav  Enter:Edit/Add  d:Delete  s:Save  Esc/q:Back"
        safe_addstr(self.scr, h - 1, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
    
    def run(self):
        self.refresh()
        while True:
            k = self.scr.getch()
            if k in (ord('q'), 27):
                if self.modified:
                    c = prompt_save(self.scr)
                    if c == 'y': self.save()
                    elif c == 'c': self.refresh(); continue
                return
            elif k in (curses.KEY_UP, ord('k')): self.cursor = max(0, self.cursor - 1)
            elif k in (curses.KEY_DOWN, ord('j')): self.cursor = min(len(self.items) - 1, self.cursor + 1)
            elif k in (ord('\n'), 10):
                item = self.items[self.cursor]; t, ci, pi, _ = item
                if t == "add_chapter":
                    self._add_chapter()
                elif t == "add_page":
                    self._add_page(ci)
                else:
                    curr_val = self.hierarchy[ci].get("summary", "") if t == "ch_summary" else self._get_value(item)
                    new_val = TextEditor(self.scr, initial_text=curr_val, title="Edit Value").run()
                    if new_val is not None:
                        self._set_value(new_val)
            elif k == ord('d'):
                item = self.items[self.cursor]; t = item[0]
                if t not in ("add_chapter", "add_page"):
                    self._delete_current()
            elif k == ord('s') and self.save():
                show_saved(self.scr)
            self.refresh()


class SchemeEditor:
    def __init__(self, scr):
        self.scr = scr
        self.schemes = json.loads(SCHEMES_FILE.read_text())
        self.theme_names = list(self.schemes.keys())
        self.current_theme = 0
        self.cursor, self.scroll, self.modified = 0, 0, False
        self._build_items()
        init_colors()
    
    def _build_items(self):
        theme = self.schemes[self.theme_names[self.current_theme]]
        self.items = []
        # Page colors
        for key in ["page-fill", "text-main", "text-heading", "text-muted", "text-accent"]:
            self.items.append((key, theme.get(key, "")))
        # Block colors
        for block, data in theme.get("blocks", {}).items():
            self.items.append((f"block.{block}.fill", data.get("fill", "")))
            self.items.append((f"block.{block}.stroke", data.get("stroke", "")))
        # Plot colors
        plot = theme.get("plot", {})
        for key in ["stroke", "highlight", "grid-opacity"]:
            self.items.append((f"plot.{key}", str(plot.get(key, ""))))
    
    def _get_value(self, key):
        theme = self.schemes[self.theme_names[self.current_theme]]
        if key.startswith("block."):
            parts = key.split(".")
            return theme.get("blocks", {}).get(parts[1], {}).get(parts[2], "")
        elif key.startswith("plot."):
            parts = key.split(".")
            return str(theme.get("plot", {}).get(parts[1], ""))
        return theme.get(key, "")
    
    def _set_value(self, key, val):
        theme = self.schemes[self.theme_names[self.current_theme]]
        if key.startswith("block."):
            parts = key.split(".")
            if "blocks" not in theme: theme["blocks"] = {}
            if parts[1] not in theme["blocks"]: theme["blocks"][parts[1]] = {}
            theme["blocks"][parts[1]][parts[2]] = val
        elif key.startswith("plot."):
            parts = key.split(".")
            if "plot" not in theme: theme["plot"] = {}
            # Handle grid-opacity as float
            if parts[1] == "grid-opacity":
                try:
                    theme["plot"][parts[1]] = float(val)
                except:
                    theme["plot"][parts[1]] = val
            else:
                theme["plot"][parts[1]] = val
        else:
            theme[key] = val
        self.modified = True
    
    def _get_label(self, key):
        if key.startswith("block."):
            parts = key.split(".")
            return f"{parts[1]}.{parts[2]}"
        elif key.startswith("plot."):
            parts = key.split(".")
            return f"plot.{parts[1]}"
        return key
    
    def save(self):
        try:
            SCHEMES_FILE.write_text(json.dumps(self.schemes, indent=4))
            self.modified = False; return True
        except: return False
    
    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        # Calculate layout - vertically centered
        title_h = 3  # Title + theme selector
        list_h = min(len(self.items) + 3, h - 6)
        total_h = title_h + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        
        # Title
        safe_addstr(self.scr, start_y, (w - 14) // 2, "SCHEME EDITOR", curses.color_pair(1) | curses.A_BOLD)
        
        # Theme selector
        theme_text = f"< {self.theme_names[self.current_theme]} >"
        safe_addstr(self.scr, start_y + 1, (w - len(theme_text)) // 2, theme_text, curses.color_pair(5) | curses.A_BOLD)
        
        # Two column box
        bw = min(70, w - 4)
        bx = (w - bw) // 2
        left_w = 22  # Key column width
        
        draw_box(self.scr, start_y + 3, bx, list_h, bw, "Colors")
        
        # Column headers
        safe_addstr(self.scr, start_y + 4, bx + 4, "Property", curses.color_pair(1) | curses.A_BOLD)
        safe_addstr(self.scr, start_y + 4, bx + left_w + 2, "Color", curses.color_pair(1) | curses.A_BOLD)
        
        # Divider line
        for i in range(1, list_h - 1):
            safe_addstr(self.scr, start_y + 3 + i, bx + left_w, "│", curses.color_pair(4) | curses.A_DIM)
        
        # Scroll handling
        vis = list_h - 3  # Account for header row
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis:
            self.scroll = self.cursor - vis + 1
        
        # Draw items
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.items):
                break
            key, _ = self.items[idx]
            y = start_y + 5 + i
            cur = idx == self.cursor
            
            if cur:
                safe_addstr(self.scr, y, bx + 2, ">", curses.color_pair(3) | curses.A_BOLD)
            
            # Left column: property name (uniform indentation)
            label = self._get_label(key)
            safe_addstr(self.scr, y, bx + 4, label[:left_w - 6], curses.color_pair(5 if cur else 4))
            
            # Right column: color swatch + hex value
            hex_val = self._get_value(key)
            color = hex_to_curses_color(hex_val)
            safe_addstr(self.scr, y, bx + left_w + 2, "██", curses.color_pair(color))
            safe_addstr(self.scr, y, bx + left_w + 5, hex_val[:bw - left_w - 8], curses.color_pair(4))
        
        footer = "* ←→:Theme  ↑↓:Nav  Enter:Edit  n:New  d:Del  s:Save  Esc/q:Back" if self.modified else "←→:Theme  ↑↓:Nav  Enter:Edit  n:New  d:Del  s:Save  Esc/q:Back"
        safe_addstr(self.scr, h - 1, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
    
    def _create_new_scheme(self):
        # Get new scheme name
        name = TextEditor(self.scr, initial_text="new-scheme", title="New Scheme Name").run()
        if name and name not in self.schemes:
            # Copy current theme as template
            current = self.schemes[self.theme_names[self.current_theme]]
            self.schemes[name] = copy.deepcopy(current)
            self.theme_names = list(self.schemes.keys())
            self.current_theme = self.theme_names.index(name)
            self._build_items()
            self.modified = True
    
    def _delete_current_scheme(self):
        if len(self.theme_names) > 1:
            del self.schemes[self.theme_names[self.current_theme]]
            self.theme_names = list(self.schemes.keys())
            self.current_theme = min(self.current_theme, len(self.theme_names) - 1)
            self._build_items()
            self.modified = True
    
    def run(self):
        self.refresh()
        while True:
            k = self.scr.getch()
            if k in (ord('q'), 27):  # q or Esc
                if self.modified:
                    c = prompt_save(self.scr)
                    if c == 'y': self.save()
                    elif c == 'c': self.refresh(); continue
                return
            elif k == curses.KEY_LEFT:
                self.current_theme = (self.current_theme - 1) % len(self.theme_names)
                self._build_items(); self.cursor = min(self.cursor, len(self.items) - 1)
            elif k == curses.KEY_RIGHT:
                self.current_theme = (self.current_theme + 1) % len(self.theme_names)
                self._build_items(); self.cursor = min(self.cursor, len(self.items) - 1)
            elif k in (curses.KEY_UP, ord('k')): self.cursor = max(0, self.cursor - 1)
            elif k in (curses.KEY_DOWN, ord('j')): self.cursor = min(len(self.items) - 1, self.cursor + 1)
            elif k in (ord('\n'), 10):
                key, _ = self.items[self.cursor]
                curr_val = self._get_value(key)
                new_val = TextEditor(self.scr, initial_text=curr_val, title="Edit Color").run()
                if new_val is not None:
                    self._set_value(key, new_val)
                    self._build_items()
            elif k == ord('n'):
                self._create_new_scheme()
            elif k == ord('d'):
                self._delete_current_scheme()
            elif k == ord('s') and self.save():
                show_saved(self.scr)
            self.refresh()


class SnippetsEditor:
    def __init__(self, scr):
        self.scr = scr
        self.cursor, self.scroll, self.modified = 0, 0, False
        self._load_snippets()
        init_colors()
    
    def _load_snippets(self):
        self.snippets = []
        try:
            content = SNIPPETS_FILE.read_text()
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('#let ') and '=' in line:
                    rest = line[5:]
                    eq_pos = rest.find('=')
                    if eq_pos != -1:
                        name = rest[:eq_pos].strip()
                        if '(' in name:
                            name = name[:name.find('(') + 1] + name[name.find('(') + 1:name.find(')') + 1]
                        definition = rest[eq_pos + 1:].strip()
                        self.snippets.append([name, definition])
        except:
            pass
        if not self.snippets:
            self.snippets = [["example", "[example text]"]]
    
    def _save_snippets(self):
        lines = []
        for name, definition in self.snippets:
            lines.append(f"#let {name} = {definition}")
        SNIPPETS_FILE.write_text('\n'.join(lines) + '\n')
        self.modified = False
    
    def save(self):
        try:
            self._save_snippets()
            return True
        except:
            return False
    
    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        # Calculate layout - vertically centered
        title_h = 2
        list_h = min(len(self.snippets) + 2, h - 6)
        total_h = title_h + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        
        # Title
        safe_addstr(self.scr, start_y, (w - 16) // 2, "SNIPPETS EDITOR", curses.color_pair(1) | curses.A_BOLD)
        
        # Two column box
        bw = min(80, w - 4)
        bx = (w - bw) // 2
        left_w = 20  # Name column width
        
        draw_box(self.scr, start_y + 2, bx, list_h, bw, "Snippets")
        
        # Column headers
        safe_addstr(self.scr, start_y + 3, bx + 4, "Name", curses.color_pair(1) | curses.A_BOLD)
        safe_addstr(self.scr, start_y + 3, bx + left_w + 2, "Definition", curses.color_pair(1) | curses.A_BOLD)
        
        # Divider line
        for i in range(1, list_h - 1):
            safe_addstr(self.scr, start_y + 2 + i, bx + left_w, "│", curses.color_pair(4) | curses.A_DIM)
        
        # Scroll handling - include +1 for the "add new" row
        total_items = len(self.snippets) + 1
        vis = list_h - 3  # Account for header row
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis:
            self.scroll = self.cursor - vis + 1
        
        # Draw items
        for i in range(vis):
            idx = self.scroll + i
            if idx >= total_items:
                break
            y = start_y + 4 + i
            cur = idx == self.cursor
            
            if cur:
                safe_addstr(self.scr, y, bx + 2, ">", curses.color_pair(3) | curses.A_BOLD)
            
            if idx < len(self.snippets):
                # Regular snippet row
                name, definition = self.snippets[idx]
                safe_addstr(self.scr, y, bx + 4, name[:left_w - 6], curses.color_pair(5 if cur else 4))
                def_text = definition[:bw - left_w - 6]
                safe_addstr(self.scr, y, bx + left_w + 2, def_text, curses.color_pair(4))
            else:
                # "Add new" row
                safe_addstr(self.scr, y, bx + 4, "+ Add new snippet...", curses.color_pair(3 if cur else 4) | curses.A_DIM)
        
        footer = "* ↑↓:Nav  Enter:Edit/Add  d:Delete  s:Save  Esc/q:Back" if self.modified else "↑↓:Nav  Enter:Edit/Add  d:Delete  s:Save  Esc/q:Back"
        safe_addstr(self.scr, h - 1, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
    
    def run(self):
        self.refresh()
        while True:
            k = self.scr.getch()
            total_items = len(self.snippets) + 1  # Include "add new" row
            
            if k in (ord('q'), 27):  # q or Esc
                if self.modified:
                    c = prompt_save(self.scr)
                    if c == 'y': self.save()
                    elif c == 'c': self.refresh(); continue
                return
            elif k in (curses.KEY_UP, ord('k')):
                self.cursor = max(0, self.cursor - 1)
            elif k in (curses.KEY_DOWN, ord('j')):
                self.cursor = min(total_items - 1, self.cursor + 1)
            elif k in (ord('\n'), 10):
                if self.cursor >= len(self.snippets):
                    # "Add new" row selected - create new snippet
                    self.snippets.append(["new_snippet", "[definition]"])
                    self.cursor = len(self.snippets) - 1
                    self.modified = True
                    # Immediately edit the new snippet
                    name, definition = self.snippets[self.cursor]
                    new_name = TextEditor(self.scr, initial_text=name, title="New Snippet Name").run()
                    if new_name is not None:
                        self.snippets[self.cursor][0] = new_name
                    new_def = TextEditor(self.scr, initial_text=definition, title="New Definition").run()
                    if new_def is not None:
                        self.snippets[self.cursor][1] = new_def
                elif self.snippets:
                    name, definition = self.snippets[self.cursor]
                    # Edit name
                    new_name = TextEditor(self.scr, initial_text=name, title="Edit Snippet Name").run()
                    if new_name is not None:
                        self.snippets[self.cursor][0] = new_name
                        self.modified = True
                    # Edit definition
                    new_def = TextEditor(self.scr, initial_text=definition, title="Edit Definition").run()
                    if new_def is not None:
                        self.snippets[self.cursor][1] = new_def
                        self.modified = True
            elif k == ord('n'):  # New snippet (shortcut)
                self.snippets.append(["new_snippet", "[definition]"])
                self.cursor = len(self.snippets) - 1
                self.modified = True
            elif k == ord('d') and self.cursor < len(self.snippets) and self.snippets:  # Delete (not on "add" row)
                del self.snippets[self.cursor]
                if self.cursor >= len(self.snippets):
                    self.cursor = max(0, len(self.snippets) - 1)
                self.modified = True
            elif k == ord('s') and self.save():
                show_saved(self.scr)
            self.refresh()


# =============================================================================
# BUILD UI
# =============================================================================

class BuildUI:
    def __init__(self, scr, debug=False):
        self.scr, self.debug_mode = scr, debug
        self.logs, self.typst_logs = [], []
        self.task, self.phase, self.progress, self.total = "", "", 0, 0
        self.view, self.scroll = "normal", 0
        self.has_warnings = False
        init_colors()
        self.h, self.w = scr.getmaxyx()
    
    def log(self, msg, ok=False): self.logs.append((msg, ok)); self.logs = self.logs[-20:]; self.refresh()
    def debug(self, msg):
        if self.debug_mode: self.log(f"[DEBUG] {msg}")
    def log_typst(self, out):
        if out:
            self.typst_logs.extend([l for l in out.split('\n') if l.strip()])
            self.typst_logs = self.typst_logs[-100:]
            if 'warning:' in out.lower(): self.has_warnings = True
    def set_phase(self, p): self.phase = p; self.refresh()
    def set_task(self, t): self.task = t; self.refresh()
    def set_progress(self, p, t): self.progress, self.total = p, t; self.refresh()
    
    def check_input(self):
        try:
            k = self.scr.getch()
            if k == -1:
                return
            if k == ord('v'):
                self.view = "typst" if self.view == "normal" else "normal"
                self.scroll = 0
            elif self.view == "typst":
                if k in (curses.KEY_UP, ord('k')):
                    self.scroll = max(0, self.scroll - 1)
                elif k in (curses.KEY_DOWN, ord('j')):
                    self.scroll = min(max(0, len(self.typst_logs) - 1), self.scroll + 1)
        except:
            pass
    
    def refresh(self):
        self.check_input()
        
        self.h, self.w = self.scr.getmaxyx()
        self.scr.clear()
        
        lh = min(15, self.h - 12)
        total_h = 1 + 5 + 1 + lh + 1  # title + progress box + gap + log box + footer
        start_y = max(0, (self.h - total_h) // 2)
        
        title = "NOTEWORTHY BUILD SYSTEM" + (" [DEBUG]" if self.debug_mode else "")
        safe_addstr(self.scr, start_y, (self.w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
        
        bw, bx = min(60, self.w - 4), (self.w - min(60, self.w - 4)) // 2
        draw_box(self.scr, start_y + 2, bx, 5, bw, "Progress")
        if self.phase: safe_addstr(self.scr, start_y + 3, bx + 2, self.phase[:bw-4], curses.color_pair(5))
        if self.task: safe_addstr(self.scr, start_y + 4, bx + 2, f"→ {self.task}"[:bw-4], curses.color_pair(4))
        if self.total:
            filled = int((bw - 12) * self.progress / self.total)
            safe_addstr(self.scr, start_y + 5, bx + 2, "█" * filled + "░" * (bw - 12 - filled), curses.color_pair(3))
            safe_addstr(self.scr, start_y + 5, bx + bw - 8, f"{100*self.progress//self.total:3d}%", curses.color_pair(3) | curses.A_BOLD)
        
        if self.view == "typst":
            draw_box(self.scr, start_y + 8, bx, lh, bw, "Typst Output (↑↓ scroll)")
            if self.typst_logs:
                for i, line in enumerate(self.typst_logs[self.scroll:self.scroll + lh - 2]):
                    c = 6 if 'error:' in line.lower() else 3 if 'warning:' in line.lower() else 4
                    safe_addstr(self.scr, start_y + 9 + i, bx + 2, line[:bw-4], curses.color_pair(c))
            else:
                safe_addstr(self.scr, start_y + 9, bx + 2, "(no output yet)", curses.color_pair(4) | curses.A_DIM)
        else:
            draw_box(self.scr, start_y + 8, bx, lh, bw, "Build Log")
            for i, (msg, ok) in enumerate(self.logs[-(lh-2):]):
                safe_addstr(self.scr, start_y + 9 + i, bx + 2, ("✓ " if ok else "  ") + msg[:bw-6], curses.color_pair(2 if ok else 4))
        
        safe_addstr(self.scr, self.h - 1, (self.w - 50) // 2, "Press Ctrl+C to cancel  |  Press 'v' to toggle view", curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()

# =============================================================================
# BUILD LOGIC
# =============================================================================

def run_build(scr, args, hierarchy, opts):
    ui = BuildUI(scr, opts['debug'])
    scr.keypad(True)
    scr.nodelay(False)
    scr.timeout(0)
    
    # Thread-safe lock for UI updates
    ui_lock = threading.Lock()
    progress_counter = [0]  # Use list for mutable reference in closures
    
    def safe_log(msg, ok=False):
        with ui_lock:
            ui.log(msg, ok)
    
    def safe_log_typst(out):
        with ui_lock:
            ui.log_typst(out)
    
    def safe_refresh():
        with ui_lock:
            ui.refresh()
    
    def increment_progress(total):
        with ui_lock:
            progress_counter[0] += 1
            ui.set_progress(progress_counter[0], total)
    
    safe_log("Checking dependencies...")
    check_dependencies()
    safe_log("Dependencies OK", True)
    
    if BUILD_DIR.exists(): shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir()
    safe_log("Build directory prepared", True)
    
    pages = opts.get('selected_pages', [])
    by_ch = {}
    for ci, ai in pages:
        by_ch.setdefault(ci, []).append(ai)
    
    chapters = [(i, hierarchy[i]) for i in sorted(by_ch.keys())]
    safe_log(f"Building {len(pages)} pages from {len(chapters)} chapters", True)
    
    # Determine thread count (use CPU count, but cap at 4 to avoid memory issues)
    max_workers = min(4, os.cpu_count() or 2)
    safe_log(f"Using {max_workers} parallel workers", True)
    
    total = (3 if opts['frontmatter'] else 0) + sum(1 + len(by_ch[ci]) for ci, _ in chapters)
    ui.set_phase("Compiling Sections")
    ui.set_progress(0, total + 1)
    
    page_map, current, pdfs = {}, 1, []
    flags = opts.get('typst_flags', [])
    # Import for parallel compilation
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def compile_simple(target, output, extra_flags):
        compile_target(target, output, extra_flags=extra_flags)
        return (target, output, get_pdf_page_count(output))
    
    # Phase 1: Frontmatter in parallel (cover, preface don't need page offsets; TOC is regenerated later)
    if opts['frontmatter']:
        with ui_lock:
            ui.set_task("Compiling frontmatter in parallel...")
        
        frontmatter_tasks = [
            ("cover", BUILD_DIR / "00_cover.pdf", "Cover"),
            ("preface", BUILD_DIR / "01_preface.pdf", "Preface"),
            ("outline", BUILD_DIR / "02_outline.pdf", "TOC"),
        ]
        
        frontmatter_results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(compile_simple, t, o, flags): t for t, o, _ in frontmatter_tasks}
            for future in as_completed(futures):
                target = futures[future]
                try:
                    t, out, page_count = future.result()
                    frontmatter_results[t] = (out, page_count)
                    increment_progress(total + 1)
                except Exception as e:
                    safe_log(f"Error compiling {target}: {e}")
                    raise
        
        # Add frontmatter to pdfs in correct order and calculate page offsets
        for target, out, label in frontmatter_tasks:
            if target in frontmatter_results:
                output, page_count = frontmatter_results[target]
                pdfs.append(output)
                page_map[target] = current
                current += page_count
                safe_log(f"{label} compiled", True)
    
    # Phase 2: Compile all chapter covers in parallel, then content pages sequentially per chapter
    # First, compile all chapter covers in parallel
    chapter_covers = []
    for ci, ch in chapters:
        ch_id = ch["pages"][0]["id"][:2]
        out = BUILD_DIR / f"10_chapter_{ch_id}_cover.pdf"
        chapter_covers.append((f"chapter-{ch_id}", out, ch_id, ci))
    
    if chapter_covers:
        with ui_lock:
            ui.set_task(f"Compiling {len(chapter_covers)} chapter covers in parallel...")
        
        cover_results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(compile_simple, t, o, flags): t for t, o, _, _ in chapter_covers}
            for future in as_completed(futures):
                target = futures[future]
                try:
                    t, out, page_count = future.result()
                    cover_results[t] = (out, page_count)
                except Exception as e:
                    safe_log(f"Error compiling {target}: {e}")
                    raise
        
        safe_log(f"Chapter covers compiled in parallel", True)
    
    # Now process each chapter: add cover to pdfs, then compile content pages sequentially
    for ci, ch in chapters:
        ch_id = ch["pages"][0]["id"][:2]
        cover_target = f"chapter-{ch_id}"
        cover_out = BUILD_DIR / f"10_chapter_{ch_id}_cover.pdf"
        
        # Add chapter cover (already compiled)
        if cover_target in cover_results:
            output, page_count = cover_results[cover_target]
            page_map[cover_target] = current
            pdfs.append(output)
            current += page_count
            increment_progress(total + 1)
        
        # Compile content pages sequentially (required for correct page offsets)
        for ai in sorted(by_ch[ci]):
            p = ch["pages"][ai]
            with ui_lock:
                ui.set_task(f"Section {p['id']}: {p['title']}")
            out = BUILD_DIR / f"20_page_{p['id']}.pdf"
            page_map[p["id"]] = current
            compile_target(p["id"], out, page_offset=current, extra_flags=flags, callback=safe_refresh, log_callback=safe_log_typst)
            pdfs.append(out)
            current += get_pdf_page_count(out)
            increment_progress(total + 1)
        
        safe_log(f"Chapter {ch_id} compiled", True)
        
        # Cleanup after each chapter
        gc.collect()
    
    # Phase 3: Regenerate TOC with final page map
    if opts['frontmatter']:
        with ui_lock:
            ui.set_task("Regenerating TOC")
        out = BUILD_DIR / "02_outline.pdf"
        compile_target("outline", out, page_offset=page_map["outline"], page_map=page_map, extra_flags=flags, callback=safe_refresh, log_callback=safe_log_typst)
        safe_log("TOC regenerated", True)
    
    safe_log(f"Total pages: {current - 1}", True)
    
    # Phase 4: Merge and metadata
    ui.set_phase("Merging PDFs")
    method = merge_pdfs(pdfs, OUTPUT_FILE)
    if method: safe_log(f"Merged with {method}", True)
    
    # Cleanup pdfs list
    pdfs.clear()
    gc.collect()
    
    ui.set_phase("Adding Metadata")
    bm = BUILD_DIR / "bookmarks.txt"
    create_pdf_metadata([ch for _, ch in chapters], page_map, bm)
    apply_pdf_metadata(OUTPUT_FILE, bm, "Noteworthy Framework", "Sihoo Lee, Lee Hojun")
    safe_log("PDF metadata applied", True)
    
    if opts['leave_individual']:
        zip_build_directory(BUILD_DIR)
        safe_log("Individual PDFs archived", True)
    
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        safe_log("Build directory cleaned", True)
    
    ui.set_phase("BUILD COMPLETE!")
    ui.set_progress(total + 1, total + 1)
    safe_log(f"Created {OUTPUT_FILE} ({current - 1} pages)", True)
    
    # Final cleanup
    gc.collect()
    
    scr.nodelay(False)
    show_success_screen(scr, current - 1, ui.has_warnings, ui.typst_logs)

# =============================================================================
# INIT WIZARD
# =============================================================================

class InitWizard:
    def __init__(self, scr):
        self.scr = scr
        self.config = {
            "title": "",
            "subtitle": "",
            "authors": [],
            "affiliation": "",
            "logo": None,
            "show-solution": True,
            "solutions-text": "Solutions",
            "problems-text": "Problems",
            "chapter-name": "Chapter",
            "subchap-name": "Section",
            "font": "IBM Plex Serif",
            "title-font": "Noto Sans Adlam",
            "display-cover": True,
            "display-outline": True,
            "display-chap-cover": True,
            "box-margin": "5pt",
            "box-inset": "15pt",
            "render-sample-count": 1000,
            "display-mode": "rose-pine"
        }
        self.steps = [
            ("title", "Document Title", "Enter the main title of your document:", "str"),
            ("subtitle", "Subtitle", "Enter a subtitle (optional, press Enter to skip):", "str"),
            ("authors", "Authors", "Enter author names (comma-separated):", "list"),
            ("affiliation", "Affiliation", "Enter your organization/affiliation:", "str"),
            ("display-mode", "Color Theme", "Use ←/→ to select, Enter to confirm:", "choice", ["rose-pine", "dark", "light", "nord", "dracula", "gruvbox"]),
            ("font", "Body Font", "Enter body font name:", "str"),
            ("title-font", "Title Font", "Enter title font name:", "str"),
            ("chapter-name", "Chapter Label", "What to call chapters (e.g., 'Chapter', 'Unit'):", "str"),
            ("subchap-name", "Section Label", "What to call sections (e.g., 'Section', 'Lesson'):", "str"),
        ]
        self.current_step = 0
        self.choice_index = 0  # For choice type slider
        init_colors()
    
    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        total_h = 16
        start_y = max(1, (h - total_h) // 2)
        
        safe_addstr(self.scr, start_y, (w - 22) // 2, "NOTEWORTHY SETUP WIZARD", curses.color_pair(1) | curses.A_BOLD)
        safe_addstr(self.scr, start_y + 1, (w - 40) // 2, "Let's set up your document configuration", curses.color_pair(4) | curses.A_DIM)
        
        prog = f"Step {self.current_step + 1} of {len(self.steps)}"
        safe_addstr(self.scr, start_y + 3, (w - len(prog)) // 2, prog, curses.color_pair(5))
        
        step = self.steps[self.current_step]
        key, label, prompt, stype = step[0], step[1], step[2], step[3]
        
        bw = min(60, w - 4)
        bx = (w - bw) // 2
        draw_box(self.scr, start_y + 5, bx, 7, bw, label)
        
        safe_addstr(self.scr, start_y + 6, bx + 2, prompt[:bw-4], curses.color_pair(4))
        
        if stype == "choice":
            # Show slider selector
            choices = step[4]
            choice_text = f"◀  {choices[self.choice_index]}  ▶"
            safe_addstr(self.scr, start_y + 8, (w - len(choice_text)) // 2, choice_text, curses.color_pair(5) | curses.A_BOLD)
            # Show dots for position
            dots = "".join("●" if i == self.choice_index else "○" for i in range(len(choices)))
            safe_addstr(self.scr, start_y + 9, (w - len(dots)) // 2, dots, curses.color_pair(4) | curses.A_DIM)
            footer = "←→:Select  Enter:Confirm  Backspace:Back  Esc:Cancel"
        else:
            curr_val = self.config.get(key, "")
            if isinstance(curr_val, list):
                curr_val = ", ".join(curr_val)
            if curr_val:
                safe_addstr(self.scr, start_y + 8, bx + 2, f"Default: {str(curr_val)[:bw-12]}", curses.color_pair(4) | curses.A_DIM)
            footer = "Enter:Input  Backspace:Back  Esc:Cancel"
        
        safe_addstr(self.scr, h - 1, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
    
    def get_input(self):
        curses.echo()
        curses.curs_set(1)
        
        h, w = self.scr.getmaxyx()
        bw = min(60, w - 4)
        bx = (w - bw) // 2
        start_y = max(1, (h - 16) // 2)
        
        safe_addstr(self.scr, start_y + 10, bx + 2, "> ", curses.color_pair(3) | curses.A_BOLD)
        self.scr.refresh()
        
        try:
            value = self.scr.getstr(start_y + 10, bx + 4, bw - 6).decode('utf-8').strip()
        except:
            value = ""
        
        curses.noecho()
        curses.curs_set(0)
        return value
    
    def run(self):
        while self.current_step < len(self.steps):
            self.refresh()
            k = self.scr.getch()
            
            step = self.steps[self.current_step]
            key, stype = step[0], step[3]
            
            if k == 27:  # Esc
                return None
            elif k in (curses.KEY_BACKSPACE, 127, 8) and self.current_step > 0:
                self.current_step -= 1
                # Reset choice index for new step if it's a choice
                if self.steps[self.current_step][3] == "choice":
                    choices = self.steps[self.current_step][4]
                    curr = self.config.get(self.steps[self.current_step][0], choices[0])
                    self.choice_index = choices.index(curr) if curr in choices else 0
            elif stype == "choice":
                choices = step[4]
                if k == curses.KEY_LEFT:
                    self.choice_index = (self.choice_index - 1) % len(choices)
                elif k == curses.KEY_RIGHT:
                    self.choice_index = (self.choice_index + 1) % len(choices)
                elif k in (ord('\n'), 10, curses.KEY_ENTER):
                    self.config[key] = choices[self.choice_index]
                    self.current_step += 1
                    self.choice_index = 0
            elif k in (ord('\n'), 10, curses.KEY_ENTER):
                value = self.get_input()
                if value or key != "title":
                    if stype == "list":
                        self.config[key] = [s.strip() for s in value.split(",") if s.strip()] if value else []
                    else:
                        self.config[key] = value if value else self.config.get(key, "")
                    self.current_step += 1
                elif not value and key == "title":
                    h, w = self.scr.getmaxyx()
                    safe_addstr(self.scr, h - 2, (w - 20) // 2, "Title is required!", curses.color_pair(6) | curses.A_BOLD)
                    self.scr.refresh()
                    curses.napms(1000)
        
        try:
            CONFIG_FILE.write_text(json.dumps(self.config, indent=4))
            return True
        except:
            return None

def needs_init():
    return not CONFIG_FILE.exists()

# =============================================================================
# ENTRY POINTS
# =============================================================================

def run_app(scr, args):
    init_colors()
    if not check_terminal_size(scr): return
    
    # Check if we need to run the init wizard
    if needs_init():
        wizard = InitWizard(scr)
        if wizard.run() is None:
            return  # User cancelled
    
    scr.clear()
    h, w = scr.getmaxyx()
    safe_addstr(scr, h // 2, (w - 24) // 2, "Syncing content files...", curses.color_pair(1) | curses.A_BOLD)
    scr.refresh()
    
    # Sync hierarchy with content directory
    try:
        missing_files, new_files = sync_hierarchy_with_content()
    except Exception as e:
        show_error_screen(scr, f"Error syncing hierarchy: {e}")
        return
    
    # Load ignored files from .indexignore
    ignored_files = load_indexignore()
    new_files = [f for f in new_files if f not in ignored_files]
    
    # FATAL ERROR if files are missing from content
    if missing_files:
        scr.clear()
        h, w = scr.getmaxyx()
        
        # Draw sad face
        face = SAD_FACE
        face_start_y = max(2, (h - len(face) - 12) // 2)
        face_x = (w - len(face[0])) // 2
        for i, line in enumerate(face):
            safe_addstr(scr, face_start_y + i, face_x, line, curses.color_pair(6) | curses.A_BOLD)
        
        # Error message
        msg_y = face_start_y + len(face) + 2
        safe_addstr(scr, msg_y, (w - 12) // 2, "BUILD FAILED", curses.color_pair(6) | curses.A_BOLD)
        
        error_msg = "Files in hierarchy.json are missing from content/"
        safe_addstr(scr, msg_y + 2, (w - len(error_msg)) // 2, error_msg, curses.color_pair(6))
        
        # List missing files
        list_y = msg_y + 4
        max_show = min(len(missing_files), h - list_y - 4)
        for i, page_id in enumerate(missing_files[:max_show]):
            path = f"content/chapter {page_id[:2]}/{page_id}.typ"
            safe_addstr(scr, list_y + i, (w - len(path) - 4) // 2, f"• {path}", curses.color_pair(6))
        if len(missing_files) > max_show:
            safe_addstr(scr, list_y + max_show, (w - 20) // 2, f"... and {len(missing_files) - max_show} more", curses.color_pair(6) | curses.A_DIM)
        
        safe_addstr(scr, h - 2, (w - 30) // 2, "Press any key to exit...", curses.color_pair(4) | curses.A_DIM)
        scr.refresh()
        scr.getch()
        return  # Exit program
    
    # Handle new files one at a time
    for page_id in new_files:
        scr.clear()
        h, w = scr.getmaxyx()
        
        bw = min(55, w - 6)
        bh = 11
        bx = (w - bw) // 2
        by = (h - bh) // 2
        
        draw_box(scr, by, bx, bh, bw, " New File Found ")
        
        # Explanation
        safe_addstr(scr, by + 2, bx + 2, "A file was found that is not in hierarchy.", curses.color_pair(4))
        
        safe_addstr(scr, by + 4, bx + 2, f"File: {page_id}.typ", curses.color_pair(1) | curses.A_BOLD)
        safe_addstr(scr, by + 5, bx + 2, f"Path: content/chapter {page_id[:2]}/", curses.color_pair(4) | curses.A_DIM)
        
        safe_addstr(scr, by + 7, bx + 2, "What would you like to do?", curses.color_pair(4))
        safe_addstr(scr, by + bh - 2, bx + 2, "'a' add  |  'i' ignore  |  's' skip", curses.color_pair(4) | curses.A_DIM)
        
        scr.refresh()
        k = scr.getch()
        
        if k == ord('a'):
            # Prompt for title
            curses.echo()
            curses.curs_set(1)
            
            scr.clear()
            h, w = scr.getmaxyx()
            
            draw_box(scr, by, bx, bh, bw, f" Add {page_id} ")
            safe_addstr(scr, by + 2, bx + 2, "Enter title:", curses.color_pair(4))
            safe_addstr(scr, by + 4, bx + 2, "> ", curses.color_pair(3) | curses.A_BOLD)
            scr.refresh()
            
            try:
                title = scr.getstr(by + 4, bx + 4, bw - 8).decode('utf-8').strip()
            except:
                title = ""
            
            curses.noecho()
            curses.curs_set(0)
            
            if not title:
                title = page_id  # Default to page ID if blank
            
            # Add single file to hierarchy with the title
            add_single_file_to_hierarchy(page_id, title)
            
        elif k == ord('i'):
            # Add to .indexignore
            ignored_files.add(page_id)
            save_indexignore(ignored_files)
        # 's' or any other key = skip (just continue to next file)
    
    scr.clear()
    h, w = scr.getmaxyx()
    safe_addstr(scr, h // 2, (w - 11) // 2, "Indexing...", curses.color_pair(1) | curses.A_BOLD)
    scr.refresh()
    
    hierarchy = extract_hierarchy()
    menu = BuildMenu(scr, hierarchy)
    opts = menu.run()
    
    if opts is None: return
    if not opts.get('selected_pages'):
        show_error_screen(scr, "No pages selected")
        return
    
    try:
        run_build(scr, args, hierarchy, opts)
    except Exception as e:
        show_error_screen(scr, e)

def main():
    parser = argparse.ArgumentParser(description="Build Noteworthy documentation")
    args = parser.parse_args()
    
    try:
        curses.wrapper(lambda scr: run_app(scr, args))
    except KeyboardInterrupt:
        print("\nBuild cancelled.")
        if BUILD_DIR.exists(): shutil.rmtree(BUILD_DIR)
        sys.exit(1)
    except Exception as e:
        print(f"\nBuild failed: {e}")
        import traceback; traceback.print_exc()
        if BUILD_DIR.exists(): shutil.rmtree(BUILD_DIR)
        sys.exit(1)

if __name__ == "__main__":
    main()
