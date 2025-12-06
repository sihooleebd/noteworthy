#!/usr/bin/env python3
import copy
import curses
import fcntl
import json
import os
import shutil
import subprocess
import sys
import termios
import time
import tty
import argparse
import zipfile
import urllib.request
import urllib.parse
import tempfile
from pathlib import Path

import logging

# Reduce Esc key delay (must be set before curses.initscr)
os.environ.setdefault('ESCDELAY', '25')

# =============================================================================
# CONSTANTS
# =============================================================================

# Build Paths
BASE_DIR = Path(__file__).parent.resolve()
BUILD_DIR = BASE_DIR / "templates/build"
OUTPUT_FILE = BASE_DIR / "output.pdf" # Output to the same directory as noteworthy.py
RENDERER_FILE = BASE_DIR / "templates/parser.typ"

# System Config Paths
SYSTEM_CONFIG_DIR = BASE_DIR / "templates/systemconfig"
SETTINGS_FILE = SYSTEM_CONFIG_DIR / "build_settings.json"
INDEXIGNORE_FILE = SYSTEM_CONFIG_DIR / ".indexignore"

# Config File Paths
CONFIG_FILE = BASE_DIR / "templates/config/config.json"
HIERARCHY_FILE = BASE_DIR / "templates/config/hierarchy.json"
PREFACE_FILE = BASE_DIR / "templates/config/preface.typ"
SNIPPETS_FILE = BASE_DIR / "templates/config/snippets.typ"
SCHEMES_FILE = BASE_DIR / "templates/config/schemes.json"
SETUP_FILE = BASE_DIR / "templates/setup.typ"

# Terminal Size Requirements
MIN_TERM_HEIGHT = 30 # Increased for margins
MIN_TERM_WIDTH = 52

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



def load_config_safe():
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text())
    except: pass
    return {}







def get_formatted_name(path_str, hierarchy, config=None):
    """Get fully formatted name like 'Problem 01.01' (index-based)"""
    if config is None: config = load_config_safe()
    
    path = Path(path_str)
    if not path.stem.isdigit() or not path.parent.name.isdigit():
        return path.name
        
    ci = int(path.parent.name)
    pi = int(path.stem)
    
    total_chapters = len(hierarchy)
    total_pages = 0
    if ci < len(hierarchy):
        total_pages = len(hierarchy[ci].get("pages", []))
        
    # Calculate widths
    ch_width = len(str(total_chapters))
    pg_width = len(str(total_pages)) if total_pages > 0 else 2
    
    # Pad indices (1-based for display)
    ch_disp = str(ci + 1).zfill(ch_width)
    pg_disp = str(pi + 1).zfill(pg_width)
    
    label = config.get("subchap-name", "Section")
    return f"{label} {ch_disp}.{pg_disp}"

def check_dependencies():
    if not shutil.which("typst"):
        print("Error: 'typst' not found. Install from https://typst.app")
        sys.exit(1)
    if not shutil.which("pdfinfo"):
        print("Error: 'pdfinfo' not found. Install with: brew install poppler")
        sys.exit(1)
    if not (shutil.which("pdfunite") or shutil.which("gs")):
        print("Error: Neither 'pdfunite' nor 'gs' (ghostscript) found. Install poppler-utils or ghostscript.")
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
    """Load set of ignored file IDs from .indexignore"""
    try:
        if INDEXIGNORE_FILE.exists():
            lines = INDEXIGNORE_FILE.read_text().strip().split('\n')
            return {l.strip() for l in lines if l.strip() and not l.startswith('#')}
    except: pass
    return set()

def save_indexignore(ignored_set):
    """Save set of ignored file IDs to .indexignore"""
    try:
        SYSTEM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        content = "# Files to ignore during hierarchy sync\n# One file ID per line (e.g., 01.03)\n\n"
        content += '\n'.join(sorted(ignored_set))
        INDEXIGNORE_FILE.write_text(content)
    except: pass

def sync_hierarchy_with_content():
    """Compare hierarchy.json with actual content files (index-based)."""
    hierarchy = json.loads(HIERARCHY_FILE.read_text())
    
    missing_files = []
    new_files = []
    
    # 1. Check hierarchy against disk (Missing)
    for i, ch in enumerate(hierarchy):
        for j, pg in enumerate(ch.get("pages", [])):
            path = Path(f"content/{i}/{j}.typ")
            if not path.exists():
                missing_files.append(str(path))
                
    # 2. Check disk against hierarchy (New/Extra)
    content_dir = Path("content")
    if content_dir.exists():
        for ch_dir in content_dir.iterdir():
            if ch_dir.is_dir() and ch_dir.name.isdigit():
                i = int(ch_dir.name)
                # Check if chapter index is valid in hierarchy
                if i >= len(hierarchy):
                    # Whole chapter is extra
                    for f in ch_dir.glob("*.typ"):
                        new_files.append(str(f))
                else:
                    # Check pages
                    for f in ch_dir.glob("*.typ"):
                        if f.stem.isdigit():
                            j = int(f.stem)
                            pages = hierarchy[i].get("pages", [])
                            if j >= len(pages):
                                new_files.append(str(f))
                                
    return sorted(missing_files), sorted(new_files)



def compile_target(target, output, page_offset=None, page_map=None, extra_flags=None, callback=None, log_callback=None):
    cmd = ["typst", "compile", str(RENDERER_FILE), str(output), "--root", str(BASE_DIR), "--input", f"target={target}"]
    if page_offset: cmd.extend(["--input", f"page-offset={page_offset}"])
    if page_map:
        # Write page map to file to avoid ARG_MAX issues
        pm_file = BUILD_DIR / "page_map.json"
        try:
            pm_file.write_text(json.dumps(page_map))
            logging.info(f"Wrote page_map to {pm_file} ({len(json.dumps(page_map))} bytes)")
            # Pass path relative to project root, starting with /
            rel_path = pm_file.relative_to(BASE_DIR)
            cmd.extend(["--input", f"page-map-file=/{rel_path}"])
        except Exception as e:
            logging.error(f"Failed to write page_map file: {e}")
            # Fallback to string (might crash if too long)
            cmd.extend(["--input", f"page-map={json.dumps(page_map)}"])
            
    if extra_flags: cmd.extend(extra_flags)
    
    logging.info(f"Executing typst for {target}")
    if log_callback: log_callback(f"[compile] {target} -> {output.name}\n")
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as e:
        logging.error(f"Popen failed for {target}: {e}")
        raise e
    all_output = []
    
    # Make stderr non-blocking for real-time output
    fd = proc.stderr.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
    # Also make stdout non-blocking
    fd_out = proc.stdout.fileno()
    fl_out = fcntl.fcntl(fd_out, fcntl.F_GETFL)
    fcntl.fcntl(fd_out, fcntl.F_SETFL, fl_out | os.O_NONBLOCK)
    
    while proc.poll() is None:
        if callback and callback() is False:
            proc.terminate()
            raise Exception("Build cancelled")
        try:
            chunk = proc.stderr.read(4096)
            if chunk:
                all_output.append(chunk)
                if log_callback: log_callback(chunk)
        except: pass
        try:
            chunk = proc.stdout.read(4096)
            if chunk:
                all_output.append(chunk)
                if log_callback: log_callback(chunk)
        except: pass
        time.sleep(0.05)
    
    # Get any remaining output
    stdout, stderr = proc.communicate()
    if stderr:
        all_output.append(stderr)
        if log_callback:
            log_callback(stderr)
    if stdout:
        all_output.append(stdout)
        if log_callback:
            log_callback(stdout)
    
    if proc.returncode != 0:
        logging.error(f"Typst compilation failed for {target}. Return code: {proc.returncode}")
        logging.error(f"Output: {''.join(all_output)}")
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=stdout, stderr=''.join(all_output))
    
    if log_callback: log_callback(f"[done] {target}\n")
    return ''.join(all_output)

def merge_pdfs(pdf_files, output):
    files = [str(p) for p in pdf_files if p.exists()]
    logging.info(f"Merging {len(files)} files. First: {files[0] if files else 'None'}")
    if not files: return False
    
    if shutil.which("pdfunite"):
        logging.info("Using pdfunite")
        try:
            subprocess.run(["pdfunite"] + files + [str(output)], check=True, capture_output=True)
            return "pdfunite"
        except Exception as e:
            logging.error(f"pdfunite failed: {e}")
    elif shutil.which("gs"):
        logging.info("Using ghostscript")
        try:
            subprocess.run(["gs", "-dBATCH", "-dNOPAUSE", "-q", "-sDEVICE=pdfwrite", f"-sOutputFile={output}"] + files, check=True, capture_output=True)
            return "ghostscript"
        except Exception as e:
            logging.error(f"ghostscript failed: {e}")
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
    
    for ci, ch in chapters:
        ch_id = str(ci + 1)
        if f"chapter-{ch_id}" in page_map:
            bookmarks.extend([f"BookmarkBegin", f"BookmarkTitle: {ch['title']}", f"BookmarkLevel: 1", f"BookmarkPageNumber: {page_map[f'chapter-{ch_id}']}"])
        for ai, p in enumerate(ch["pages"]):
            key = f"{ci}/{ai}"
            if key in page_map:
                bookmarks.extend([f"BookmarkBegin", f"BookmarkTitle: {p['title']}", f"BookmarkLevel: 2", f"BookmarkPageNumber: {page_map[key]}"])
    
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
# TUI HELPERS
# =============================================================================

class TUI:
    """Shared TUI helper functions"""
    @staticmethod
    def init_colors():
        curses.start_color()
        curses.use_default_colors()
        for i, color in enumerate([curses.COLOR_CYAN, curses.COLOR_GREEN, curses.COLOR_YELLOW, 
                                   curses.COLOR_WHITE, curses.COLOR_MAGENTA, curses.COLOR_RED], 1):
            curses.init_pair(i, color, -1)
        curses.curs_set(0)

    @staticmethod
    def disable_flow_control():
        """Disable XON/XOFF flow control to allow Ctrl+S/Ctrl+Q"""
        try:
            fd = sys.stdin.fileno()
            attrs = termios.tcgetattr(fd)
            attrs[0] &= ~(termios.IXON | termios.IXOFF)
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
        except: pass

    @staticmethod
    def safe_addstr(scr, y, x, text, attr=0):
        try:
            h, w = scr.getmaxyx()
            # MARGIN = 1, coordinates are 0-based relative to usable area
            real_y = y + 1
            real_x = x + 1
            if 0 <= real_y < h - 1 and 0 <= real_x < w - 1:
                scr.addstr(real_y, real_x, text[:w - 1 - real_x], attr)
        except curses.error: pass

    @staticmethod
    def draw_box(scr, y, x, h, w, title=""):
        try:
            # Adjust coordinates for margin
            real_y, real_x = y + 1, x + 1
            scr.addstr(real_y, real_x, "╔" + "═" * (w - 2) + "╗")
            for i in range(1, h - 1):
                scr.addstr(real_y + i, real_x, "║" + " " * (w - 2) + "║")
            scr.addstr(real_y + h - 1, real_x, "╚" + "═" * (w - 2) + "╝")
            if title:
                scr.addstr(real_y, real_x + 2, f" {title} ", curses.color_pair(1) | curses.A_BOLD)
        except curses.error: pass

    @staticmethod
    def prompt_save(scr):
        """Show save confirmation prompt, returns 'y', 'n', or 'c'"""
        h_raw, w_raw = scr.getmaxyx()
        h, w = h_raw - 2, w_raw - 2
        TUI.safe_addstr(scr, h - 1, 2, "Save? (y/n/c): ", curses.color_pair(3) | curses.A_BOLD)
        scr.refresh()
        c = scr.getch()
        return chr(c) if c in (ord('y'), ord('n'), ord('c')) else 'c'

    @staticmethod
    def show_saved(scr):
        """Show 'Saved!' message briefly"""
        h_raw, w_raw = scr.getmaxyx()
        h, w = h_raw - 2, w_raw - 2
        TUI.safe_addstr(scr, h - 1, 2, "Saved!", curses.color_pair(2) | curses.A_BOLD)
        scr.refresh()
        curses.napms(500)

    @staticmethod
    def check_terminal_size(scr):
        was_error = False
        while True:
            h, w = scr.getmaxyx()
            if h >= MIN_TERM_HEIGHT and w >= MIN_TERM_WIDTH:
                if was_error:
                    scr.clear()
                    scr.refresh()
                    scr.timeout(-1)
                return True
            
            was_error = True
            scr.clear()
            y = h // 2 - 1
            TUI.safe_addstr(scr, y, max(0, (w - 19) // 2), "Terminal too small!", curses.color_pair(6) | curses.A_BOLD)
            TUI.safe_addstr(scr, y + 1, max(0, (w - 15) // 2), f"Current: {h}×{w}", curses.color_pair(4))
            TUI.safe_addstr(scr, y + 2, max(0, (w - 15) // 2), f"Required: {MIN_TERM_HEIGHT}×{MIN_TERM_WIDTH}", curses.color_pair(4) | curses.A_DIM)
            scr.refresh()
            scr.timeout(100)
            if scr.getch() in (ord('q'), 27): return False

# =============================================================================
# BASE EDITORS
# =============================================================================

class BaseEditor:
    """Base class for full-screen editors"""
    def __init__(self, scr, title="Editor"):
        self.scr = scr
        self.title = title
        self.modified = False
        TUI.init_colors()
    
    def refresh(self): raise NotImplementedError
    def save(self): raise NotImplementedError
    
    def run(self):
        self.refresh()
        while True:
            if not TUI.check_terminal_size(self.scr): return
            k = self.scr.getch()
            if k == 27:  # Esc
                if self.modified: self.save()
                return
            elif k == ord('s') and self.save():
                TUI.show_saved(self.scr)
            else:
                self._handle_input(k)
            self.refresh()

    def _handle_input(self, k): pass

class ListEditor(BaseEditor):
    """Base class for list-based editors"""
    def __init__(self, scr, title="List Editor"):
        super().__init__(scr, title)
        self.items = []
        self.cursor = 0
        self.scroll = 0
        self.box_title = "Items"
        self.box_width = 70
    
    def _draw_item(self, y, x, item, width, selected): raise NotImplementedError
    
    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        # Calculate layout
        list_h = min(len(self.items) + 2, h - 8)
        total_h = 2 + list_h + 2 # Title + Box + Footer
        start_y = max(1, (h - total_h) // 2)
        
        # Title
        title_str = f"{self.title}{' *' if self.modified else ''}"
        TUI.safe_addstr(self.scr, start_y, (w - len(title_str)) // 2, title_str, curses.color_pair(1) | curses.A_BOLD)
        
        # Box
        bw = min(self.box_width, w - 4)
        bx = (w - bw) // 2
        TUI.draw_box(self.scr, start_y + 2, bx, list_h, bw, self.box_title)
        
        # Items
        vis = list_h - 2
        if self.cursor < self.scroll: self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis: self.scroll = self.cursor - vis + 1
        
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.items): break
            y = start_y + 3 + i
            self._draw_item(y, bx, self.items[idx], bw, idx == self.cursor)
            
        self._draw_footer(h, w)
        self.scr.refresh()
        
    def _draw_footer(self, h, w):
        footer = "Esc: Save & Exit"
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    def _handle_input(self, k):
        if k in (curses.KEY_UP, ord('k')):
            self.cursor = max(0, self.cursor - 1)
        elif k in (curses.KEY_DOWN, ord('j')):
            self.cursor = min(len(self.items) - 1, self.cursor + 1)
        else:
            return False
        return True

# =============================================================================
# SCREEN DISPLAYS
# =============================================================================

def copy_to_clipboard(text):
    """Copy text to clipboard using available system tools (Cross-platform)"""
    try:
        # macOS
        subprocess.run(["pbcopy"], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass

    try:
        # Windows (clip.exe)
        # 'clip' command reads from stdin
        subprocess.run(["clip"], input=text.encode('utf-16le'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
        
    try:
        # Wayland (Linux)
        subprocess.run(["wl-copy"], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
        
    try:
        # X11 (Linux - xclip)
        subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
        
    try:
        # X11 (Linux - xsel)
        subprocess.run(["xsel", "-b", "-i"], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
        
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
        h_raw, w_raw = scr.getmaxyx()
        h, w = h_raw - 2, w_raw - 2
        
        if view_log:
            header = "ERROR LOG (press 'v' to go back, 'c' to copy)"
            if copied:
                header = "ERROR LOG (copied to clipboard!)"
            TUI.safe_addstr(scr, 0, 2, header, curses.color_pair(6) | curses.A_BOLD)
            for i, line in enumerate(log.split('\n')[:h-3]):
                TUI.safe_addstr(scr, i + 2, 2, line, curses.color_pair(4))
        else:
            y = max(0, (h - len(SAD_FACE) - 8) // 2)
            for i, line in enumerate(SAD_FACE):
                TUI.safe_addstr(scr, y + i, (w - 9) // 2, line, curses.color_pair(6) | curses.A_BOLD)
            
            my = y + len(SAD_FACE) + 2
            TUI.safe_addstr(scr, my, (w - 12) // 2, "BUILD FAILED", curses.color_pair(6) | curses.A_BOLD)
            err = str(error)[:w-10]
            TUI.safe_addstr(scr, my + 2, (w - len(err)) // 2, err, curses.color_pair(4))
            TUI.safe_addstr(scr, my + 4, (w - 50) // 2, "Press 'v' to view log  |  Press any other key to exit", curses.color_pair(4) | curses.A_DIM)
        
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
    with open("debug_trace.log", "a") as f: f.write("Entered show_success_screen\n")
    view_log = False
    copied = False
    while True:
        scr.clear()
        h_raw, w_raw = scr.getmaxyx()
        h, w = h_raw - 2, w_raw - 2
        
        if view_log and typst_logs:
            header = "TYPST LOG (press 'v' to go back, 'c' to copy)"
            if copied:
                header = "TYPST LOG (copied to clipboard!)"
            TUI.safe_addstr(scr, 0, 2, header, curses.color_pair(3) | curses.A_BOLD)
            for i, line in enumerate(typst_logs[:h-3]):
                c = 6 if 'error:' in line.lower() else 3 if 'warning:' in line.lower() else 4
                TUI.safe_addstr(scr, i + 2, 2, line[:w-4], curses.color_pair(c))
        else:
            face = HMM_FACE if has_warnings else HAPPY_FACE
            color = curses.color_pair(3) if has_warnings else curses.color_pair(2)
            
            y = max(0, (h - len(face) - 8) // 2)
            for i, line in enumerate(face):
                TUI.safe_addstr(scr, y + i, (w - len(face[0])) // 2, line, color | curses.A_BOLD)
            
            my = y + len(face) + 2
            title = "BUILD SUCCEEDED (with warnings)" if has_warnings else "BUILD SUCCEEDED!"
            TUI.safe_addstr(scr, my, (w - len(title)) // 2, title, color | curses.A_BOLD)
            msg = f"Created: {OUTPUT_FILE} ({page_count} pages)"
            TUI.safe_addstr(scr, my + 2, (w - len(msg)) // 2, msg, curses.color_pair(4))
            
            if has_warnings:
                hint = "Press 'v' to view log  |  Press any other key to exit"
            else:
                hint = "Press any key to exit..."
            TUI.safe_addstr(scr, my + 4, (w - len(hint)) // 2, hint, curses.color_pair(4) | curses.A_DIM)
        
        scr.refresh()
        key = scr.getch()
        if key == -1: continue
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
        
        TUI.init_colors()
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
        # Calculate available chapter rows in vertical layout
        # Need: start_y + logo + title(2) + options(obh) + gap(1) + chapters + footer(3)
        vert_ch_rows = self.h - lh - 2 - obh - 1 - 5
        # Use vertical if we can fit at least 5 chapter rows, else try horizontal/compact
        if vert_ch_rows >= 7:  # 5 visible + 2 for box border
            layout = "vert"
        elif self.w >= 90:
            layout = "horz" if self.h >= lh + 3 + obh else "compact"
        else:
            layout = "vert"  # Fall back to vert even if cramped
        
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
                
                if cur: TUI.safe_addstr(self.scr, y, bx + 2, "▶", curses.color_pair(3) | curses.A_BOLD)
                
                if t == 'ch':
                    ch = self.hierarchy[ci]
                    cb = "[✓]" if self.ch_selected(ci) else "[~]" if self.ch_partial(ci) else "[ ]"
                    cc = 2 if self.ch_selected(ci) else 3 if self.ch_partial(ci) else 4
                    TUI.safe_addstr(self.scr, y, bx + 4, cb, curses.color_pair(cc))
                    ch_num = str(ci + 1)
                    TUI.safe_addstr(self.scr, y, bx + 7, f" Ch {ch_num}: {ch['title']}"[:bw-12], curses.color_pair(1))
                else:
                    p = self.hierarchy[ci]["pages"][ai]
                    sel = self.selected.get((ci, ai), False)
                    TUI.safe_addstr(self.scr, y, bx + 6, "[✓]" if sel else "[ ]", curses.color_pair(2 if sel else 4))
                    TUI.safe_addstr(self.scr, y, bx + 9, f" {str(ai+1)}: {p['title']}"[:bw-14], curses.color_pair(4))
        
        def opts(sy, bx, bw):
            for i, (lbl, val, key) in enumerate([
                ("Debug Mode:", self.debug, "d"), ("Frontmatter:", self.frontmatter, "f"), ("Leave PDFs:", self.leave_pdfs, "l")
            ]):
                TUI.safe_addstr(self.scr, sy + 1 + i, bx + 2, f"{lbl:14}", curses.color_pair(4))
                TUI.safe_addstr(self.scr, sy + 1 + i, bx + 16, "[ON] " if val else "[OFF]", curses.color_pair(2 if val else 6) | curses.A_BOLD)
                TUI.safe_addstr(self.scr, sy + 1 + i, bx + 22, f"({key})", curses.color_pair(4) | curses.A_DIM)
            
            flags = " ".join(self.typst_flags) or "(none)"
            TUI.safe_addstr(self.scr, sy + 4, bx + 2, "Typst Flags:  ", curses.color_pair(4))
            TUI.safe_addstr(self.scr, sy + 4, bx + 16, flags[:bw-20], curses.color_pair(5 if self.typst_flags else 4) | curses.A_DIM)
            TUI.safe_addstr(self.scr, sy + 5, bx + 16, "(c)", curses.color_pair(4) | curses.A_DIM)
        
        if layout == "compact":
            lw, rw = 20, min(50, self.w - 24)
            lx = (self.w - lw - rw - 2) // 2
            rx = lx + lw + 2
            ly = max(0, (self.h - lh) // 2 - 1)
            for i, line in enumerate(LOGO[:self.h-1]):
                TUI.safe_addstr(self.scr, ly + i, lx + 3, line, curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, ly + lh, lx + (lw - 10) // 2, "NOTEWORTHY", curses.color_pair(1) | curses.A_BOLD)
            TUI.draw_box(self.scr, 0, rx, obh, rw, "Options")
            opts(0, rx, rw)
            ch = max(3, self.h - obh - 3)
            TUI.draw_box(self.scr, obh + 1, rx, ch, rw, "Select Chapters")
            items(obh + 1, rx, rw, ch)
        elif layout == "horz":
            total_h = lh + 2 + obh
            start_y = max(0, (self.h - total_h - 2) // 2)
            lbw, rbw = min(40, (self.w - 6) // 2), min(50, (self.w - 6) // 2)
            lx = (self.w - lbw - rbw - 2) // 2
            rx = lx + lbw + 2
            lgx = lx + (lbw - 14) // 2
            for i, line in enumerate(LOGO[:self.h-2]):
                TUI.safe_addstr(self.scr, start_y + i, lgx, line, curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, start_y + lh, lx + (lbw - 10) // 2, "NOTEWORTHY", curses.color_pair(1) | curses.A_BOLD)
            TUI.draw_box(self.scr, start_y + lh + 2, lx, obh, lbw, "Options")
            opts(start_y + lh + 2, lx, lbw)
            ch = min(lh + 2 + obh, self.h - 2)
            TUI.draw_box(self.scr, start_y, rx, ch, rbw, "Select Chapters")
            items(start_y, rx, rbw, ch)
        else:
            ch_rows = min(len(self.items) + 2, 10)
            total_h = lh + 2 + obh + 1 + ch_rows + 2
            start_y = max(0, (self.h - total_h) // 2)
            lgx = (self.w - 14) // 2
            for i, line in enumerate(LOGO):
                TUI.safe_addstr(self.scr, start_y + i, lgx, line, curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, start_y + lh + 1, (self.w - 10) // 2, "NOTEWORTHY", curses.color_pair(1) | curses.A_BOLD)
            bw, bx = min(60, self.w - 4), (self.w - min(60, self.w - 4)) // 2
            TUI.draw_box(self.scr, start_y + lh + 3, bx, obh, bw, "Options")
            opts(start_y + lh + 3, bx, bw)
            cy = start_y + lh + 3 + obh + 1
            ch = max(4, min(len(self.items) + 2, self.h - cy - 3))
            TUI.draw_box(self.scr, cy, bx, ch, bw, "Select Chapters")
            items(cy, bx, bw, ch)
        
        footer = "Space: Toggle  a/n: All/None  Enter: Build  Esc: Back"
        TUI.safe_addstr(self.scr, self.h - 3, (self.w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
    
    def run(self):
        self.refresh()
        while True:
            if not TUI.check_terminal_size(self.scr): return None
            
            k = self.scr.getch()
            if k == 27: return None  # Esc
            elif k == ord('?'):
                show_keybindings_menu(self.scr)
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
    """Extract theme names from schemes.json"""
    try:
        schemes = json.loads(SCHEMES_FILE.read_text())
        return list(schemes.keys())
    except:
        return ["dark", "light", "rose-pine", "nord", "dracula", "gruvbox"]

def hex_to_curses_color(hex_color):
    """Convert hex color to curses color pair index (rough approximation)"""
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
    """Show menu to select which editor to open, returns immediately after editor closes"""
    TUI.init_colors()
    TUI.disable_flow_control()  # Allow Ctrl+S to work in editors
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
        if not TUI.check_terminal_size(scr): return
        h_raw, w_raw = scr.getmaxyx()
        h, w = h_raw - 2, w_raw - 2
        scr.clear()
        
        layout = "vert"
        # Use horizontal layout only if vertical space is tight but we have width
        # Vertical needs: Logo(15) + Title(2) + Menu(8) + Footer(1) + Spacing(4) ~= 30 lines
        min_vert_height = len(LOGO) + len(options) + 10
        if h < min_vert_height and w > 80: 
            layout = "horz"
        
        if layout == "horz":
            # Horizontal: Logo left, Menu right
            lh = len(LOGO)
            ly = max(0, (h - lh) // 2)
            lx = max(0, (w - 16 - 60) // 2)
            
            for i, line in enumerate(LOGO):
                if ly + i < h:
                    TUI.safe_addstr(scr, ly + i, lx, line, curses.color_pair(1) | curses.A_BOLD)
            
            # Menu
            mx = lx + 20 + 4
            mw = 55
            list_h = len(options) + 2
            my = max(0, (h - list_h) // 2)
            
            TUI.safe_addstr(scr, my - 2, mx + (mw - 14) // 2, "SELECT EDITOR", curses.color_pair(1) | curses.A_BOLD)
            TUI.draw_box(scr, my, mx, list_h, mw, "Editors")
            
            for i, (key, name, desc) in enumerate(options):
                y = my + 1 + i
                if i == cursor:
                    TUI.safe_addstr(scr, y, mx + 2, ">", curses.color_pair(3) | curses.A_BOLD)
                TUI.safe_addstr(scr, y, mx + 4, f"{key}. {name}", curses.color_pair(4) | (curses.A_BOLD if i == cursor else 0))
                TUI.safe_addstr(scr, y, mx + 26, desc[:mw-28], curses.color_pair(4) | curses.A_DIM)
                
        else:
            # Vertical (Standard)
            lh = len(LOGO)
            title_h = 2
            list_h = len(options) + 2
            total_h = lh + title_h + list_h + 2
            start_y = max(1, (h - total_h) // 2)
            
            lgx = (w - 14) // 2
            for i, line in enumerate(LOGO):
                TUI.safe_addstr(scr, start_y + i, lgx, line, curses.color_pair(1) | curses.A_BOLD)
            
            TUI.safe_addstr(scr, start_y + lh + 1, (w - 14) // 2, "SELECT EDITOR", curses.color_pair(1) | curses.A_BOLD)
            
            bw = min(55, w - 4)
            bx = (w - bw) // 2
            TUI.draw_box(scr, start_y + lh + 3, bx, list_h, bw, "Editors")
            
            for i, (key, name, desc) in enumerate(options):
                y = start_y + lh + 4 + i
                if i == cursor:
                    TUI.safe_addstr(scr, y, bx + 2, ">", curses.color_pair(3) | curses.A_BOLD)
                TUI.safe_addstr(scr, y, bx + 4, f"{key}. {name}", curses.color_pair(4) | (curses.A_BOLD if i == cursor else 0))
                TUI.safe_addstr(scr, y, bx + 26, desc[:bw-28], curses.color_pair(4) | curses.A_DIM)
        
        
        scr.refresh()
        
        k = scr.getch()
        if k == 27:  # Esc
            return
        elif k == ord('?'):
            show_keybindings_menu(scr)
        elif k in (curses.KEY_UP, ord('k')): cursor = max(0, cursor - 1)
        elif k in (curses.KEY_DOWN, ord('j')): cursor = min(len(options) - 1, cursor + 1)
        elif k in (ord('\n'), curses.KEY_ENTER, 10) or (ord('1') <= k <= ord('6')):
            idx = k - ord('1') if ord('1') <= k <= ord('6') else cursor
            if idx == 0: ConfigEditor(scr).run()
            elif idx == 1: HierarchyEditor(scr).run()
            elif idx == 2: SchemeEditor(scr).run()
            elif idx == 3: TextEditor(scr, PREFACE_FILE, title="Preface Editor").run()
            elif idx == 4: SnippetsEditor(scr).run()
            elif idx == 5: IndexignoreEditor(scr).run()


def show_keybindings_menu(scr):
    """Display keybindings help screen"""
    TUI.init_colors()
    
    sections = [
        ("Navigation", [
            ("↑/↓ or j/k", "Move up/down"),
            ("←/→", "Navigate options"),
            ("Enter", "Select/Confirm"),
            ("Space", "Toggle selection"),
        ]),
        ("General", [
            ("Esc", "Save & Exit"),
            ("s", "Save (editors)"),
            ("?", "Show this help"),
        ]),
        ("Build Menu", [
            ("a / n", "Select all / none"),
            ("d / f / l", "Toggle options"),
            ("e", "Open editor menu"),
        ]),
    ]
    
    h_raw, w_raw = scr.getmaxyx()
    h, w = h_raw - 2, w_raw - 2  # Safe margins like other menus
    scr.clear()
    
    # Calculate content size
    total_lines = sum(len(items) + 2 for _, items in sections)  # +2 for header + spacing
    bh = min(total_lines + 3, h - 2)
    bw = min(50, w - 4)
    by = max(1, (h - bh) // 2)
    bx = max(2, (w - bw) // 2)
    
    TUI.draw_box(scr, by, bx, bh, bw, " KEYBINDINGS ")
    
    y = by + 1
    for section_title, items in sections:
        if y >= by + bh - 2: break
        TUI.safe_addstr(scr, y, bx + 2, section_title, curses.color_pair(1) | curses.A_BOLD)
        y += 1
        for key, desc in items:
            if y >= by + bh - 2: break
            TUI.safe_addstr(scr, y, bx + 3, f"{key:12}", curses.color_pair(5))
            TUI.safe_addstr(scr, y, bx + 16, desc[:bw-18], curses.color_pair(4))
            y += 1
        y += 1  # Space between sections
    
    footer = "Press any key"
    TUI.safe_addstr(scr, by + bh - 1, bx + (bw - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
    scr.refresh()
    
    scr.getch()
    return


class TextEditor(BaseEditor):
    """Full-screen text editor with soft-wrapping"""
    def __init__(self, scr, filepath=None, initial_text=None, title="Text Editor"):
        super().__init__(scr, title)
        self.filepath = Path(filepath) if filepath else None
        if initial_text is not None:
            self.lines = initial_text.split('\n')
        elif self.filepath and self.filepath.exists():
            self.lines = self.filepath.read_text().split('\n')
        else:
            self.lines = [""]
        self.cy, self.cx = 0, 0
        self.scroll_y = 0
        self.preferred_x = 0
    
    def save(self):
        if self.filepath:
            try:
                self.filepath.write_text('\n'.join(self.lines))
                self.modified = False; return True
            except: return False
        return True
    
    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        # Title
        title_str = f"{self.title}{' *' if self.modified else ''}"
        TUI.safe_addstr(self.scr, 0, (w - len(title_str)) // 2, title_str, curses.color_pair(1) | curses.A_BOLD)
        
        # Calculate visual lines
        visual_lines = self._get_visual_lines(w - 5)
        
        # Adjust scroll
        vcy = 0
        for i, (text, l_idx, start_idx) in enumerate(visual_lines):
            if l_idx == self.cy:
                is_last_chunk = True
                if i + 1 < len(visual_lines) and visual_lines[i+1][1] == l_idx: is_last_chunk = False
                if self.cx >= start_idx and (self.cx < start_idx + len(text) or (self.cx == start_idx + len(text) and is_last_chunk)):
                    vcy = i; break
        
        if vcy < self.scroll_y: self.scroll_y = vcy
        elif vcy >= self.scroll_y + (h - 2): self.scroll_y = vcy - (h - 3)
        
        # Draw lines
        for i in range(h - 4):
            idx = self.scroll_y + i
            if idx >= len(visual_lines): break
            text, l_idx, start_idx = visual_lines[idx]
            y = i + 1
            if start_idx == 0:
                TUI.safe_addstr(self.scr, y, 0, f"{l_idx + 1:3d} ", curses.color_pair(4) | curses.A_DIM)
            else:
                TUI.safe_addstr(self.scr, y, 0, "    · ", curses.color_pair(4) | curses.A_DIM)
            TUI.safe_addstr(self.scr, y, 6, text)
        
        # Footer
        footer = "Esc: Save & Exit"
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        
        # Cursor
        curses.curs_set(1)  # Show cursor
        cur_y = vcy - self.scroll_y + 2
        cur_x = 6 + (self.cx - visual_lines[vcy][2])
        if 0 <= cur_y < h - 1 and 0 <= cur_x < w:
            self.scr.move(cur_y, cur_x)
        self.scr.refresh()

    def _get_visual_lines(self, width):
        visual_lines = []
        for l_idx, line in enumerate(self.lines):
            if not line:
                visual_lines.append(("", l_idx, 0))
                continue
            i = 0
            while i < len(line):
                chunk = line[i:i+width]
                if len(chunk) < width:
                    visual_lines.append((chunk, l_idx, i))
                    i += len(chunk)
                else:
                    last_space = chunk.rfind(' ')
                    if last_space != -1:
                        visual_lines.append((chunk[:last_space], l_idx, i))
                        i += last_space + 1
                    else:
                        visual_lines.append((chunk, l_idx, i))
                        i += width
        return visual_lines

    def run(self):
        TUI.disable_flow_control()
        self.refresh()
        self.refresh()
        while True:
            if not TUI.check_terminal_size(self.scr): return None
            k = self.scr.getch()
            if k == 27: # Esc
                curses.curs_set(0)  # Hide cursor before exit
                if self.modified: self.save()
                return '\n'.join(self.lines) if not self.filepath else None
            else:
                self._handle_input(k)
            self.refresh()

    def _handle_input(self, k):
        visual_lines = self._get_visual_lines(self.scr.getmaxyx()[1] - 5)
        if k == curses.KEY_UP:
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
        elif k == 9:
            self.lines[self.cy] = self.lines[self.cy][:self.cx] + "    " + self.lines[self.cy][self.cx:]
            self.cx += 4; self.modified = True
        elif 32 <= k <= 126:
            self.lines[self.cy] = self.lines[self.cy][:self.cx] + chr(k) + self.lines[self.cy][self.cx:]
            self.cx += 1; self.modified = True
        curses.curs_set(0)
        return True


class ConfigEditor(ListEditor):
    """Field-based config editor"""
    def __init__(self, scr):
        super().__init__(scr, "CONFIG EDITOR")
        self.config = json.loads(CONFIG_FILE.read_text())
        themes = extract_themes()
        
        # Metadata for known fields to ensure nice display and ordering
        # Key: (Label, Type, [Options])
        field_meta = {
            "title": ("Title", "str"),
            "subtitle": ("Subtitle", "str"),
            "authors": ("Authors", "list"),
            "affiliation": ("Affiliation", "str"),
            "font": ("Body Font", "str"),
            "title-font": ("Title Font", "str"),
            "display-mode": ("Theme", "choice", themes),
            "show-solution": ("Show Solutions", "bool"),
            "display-cover": ("Display Cover", "bool"),
            "display-outline": ("Display Outline", "bool"),
            "display-chap-cover": ("Chapter Covers", "bool"),
            "chapter-name": ("Chapter Label", "str"),
            "subchap-name": ("Section Label", "str"),
            "box-margin": ("Box Margin", "str"),
            "box-inset": ("Box Inset", "str"),
            "render-sample-count": ("Render Samples", "int"),
            "render-implicit-count": ("Implicit Samples", "int"),
            "pad-chapter-id": ("Pad Chapter ID", "bool"),
            "pad-page-id": ("Pad Page ID", "bool"),
        }

        self.fields = []
        processed_keys = set()

        # 1. Add known fields in order
        for key, meta in field_meta.items():
            if key in self.config:
                if len(meta) == 3:
                    self.fields.append((key, meta[0], meta[1], meta[2]))
                else:
                    self.fields.append((key, meta[0], meta[1]))
                processed_keys.add(key)
        
        # 2. Add any other fields found in config.json
        for key, val in self.config.items():
            if key not in processed_keys:
                # Infer type
                if isinstance(val, bool): ftype = "bool"
                elif isinstance(val, int): ftype = "int"
                elif isinstance(val, list): ftype = "list"
                else: ftype = "str"
                
                label = key.replace("-", " ").title()
                self.fields.append((key, label, ftype))

        self.items = self.fields
        self.box_title = "Settings"

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

    def _draw_item(self, y, x, item, width, selected):
        key, label, ftype = item[0], item[1], item[2]
        
        if selected: TUI.safe_addstr(self.scr, y, x + 2, ">", curses.color_pair(3) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, y, x + 4, f"{label}:", curses.color_pair(4))
        
        val_x = x + 22
        val = self.get_display(key)
        if ftype == "bool":
            c = curses.color_pair(2) if self.config.get(key) else curses.color_pair(6)
            TUI.safe_addstr(self.scr, y, val_x, val, c | curses.A_BOLD)
        elif ftype == "choice":
            TUI.safe_addstr(self.scr, y, val_x, val[:width-26], curses.color_pair(5) | curses.A_BOLD)
        else:
            TUI.safe_addstr(self.scr, y, val_x, val[:width-26], curses.color_pair(4))

    def _draw_footer(self, h, w):
        footer = "Enter/Space: Edit  Esc: Save & Exit"
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    def _handle_input(self, k):
        if super()._handle_input(k): return True
        
        f = self.items[self.cursor]; key, ftype = f[0], f[2]
        
        if k in (ord('\n'), 10):
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
                        cleaned_val = new_val.replace('\n', ',')
                        self.config[key] = [s.strip() for s in cleaned_val.split(",") if s.strip()]
                    elif new_val.lower() in ("none", "null", ""): self.config[key] = None
                    else: self.config[key] = new_val
                    self.modified = True
            return True
        elif k == ord(' '):
            if ftype == "bool": self.config[key] = not self.config.get(key, False); self.modified = True
            elif ftype == "choice":
                opts = f[3]; cur = self.config.get(key, opts[0])
                try: ni = (opts.index(cur) + 1) % len(opts)
                except: ni = 0
                self.config[key] = opts[ni]; self.modified = True
            return True
        elif k in (curses.KEY_LEFT, curses.KEY_RIGHT):
            if ftype == "choice":
                opts = f[3]; cur = self.config.get(key, opts[0])
                try: 
                    idx = opts.index(cur)
                    delta = -1 if k == curses.KEY_LEFT else 1
                    ni = (idx + delta) % len(opts)
                except: ni = 0
                self.config[key] = opts[ni]; self.modified = True
                return True
        
        return False


class HierarchyEditor(ListEditor):
    """Structured hierarchy editor"""
    def __init__(self, scr):
        super().__init__(scr, "HIERARCHY EDITOR")
        self.hierarchy = json.loads(HIERARCHY_FILE.read_text())
        self.config = load_config_safe()
        self._build_items()
        self.box_title = "Hierarchy"
        self.box_width = 75
    
    def _build_items(self):
        self.items = []
        for ci, ch in enumerate(self.hierarchy):
            self.items.append(("ch_title", ci, None, ch))
            self.items.append(("ch_summary", ci, None, ch))
            for pi, p in enumerate(ch.get("pages", [])):
                self.items.append(("pg_title", ci, pi, p))
            self.items.append(("add_page", ci, None, None))
        self.items.append(("add_chapter", None, None, None))
    
    def _get_value(self, item):
        t, ci, pi, _ = item
        if t == "ch_title": return self.hierarchy[ci]["title"]
        elif t == "ch_summary": return self.hierarchy[ci]["summary"]
        elif t == "pg_title": return self.hierarchy[ci]["pages"][pi]["title"]
        return ""
    
    def _set_value(self, val):
        t, ci, pi, _ = self.items[self.cursor]
        if t == "ch_title": self.hierarchy[ci]["title"] = val
        elif t == "ch_summary": self.hierarchy[ci]["summary"] = val
        elif t == "pg_title": self.hierarchy[ci]["pages"][pi]["title"] = val
        self.modified = True; self._build_items()
    
    def _add_chapter(self):
        new_ch = {"title": "New Chapter", "summary": "", "pages": []}
        self.hierarchy.append(new_ch)
        self.modified = True
        self._build_items()
        for i, item in enumerate(self.items):
            if item[0] == "ch_title" and item[1] == len(self.hierarchy) - 1:
                self.cursor = i; break
    
    def _add_page(self, ci):
        new_page = {"title": "New Page"}
        self.hierarchy[ci]["pages"].append(new_page)
        self.modified = True
        self._build_items()
    
    def _delete_current(self):
        t, ci, pi, _ = self.items[self.cursor]
        if t in ("ch_title", "ch_summary"):
            if len(self.hierarchy) > 1:
                del self.hierarchy[ci]
                self.modified = True
                self._build_items()
                self.cursor = min(self.cursor, len(self.items) - 1)
        elif t in ("pg_id", "pg_title"):
            del self.hierarchy[ci]["pages"][pi]
            self.modified = True
            self._build_items()
            self.cursor = min(self.cursor, len(self.items) - 1)
    
    def save(self):
        try:
            HIERARCHY_FILE.write_text(json.dumps(self.hierarchy, indent=4))
            self.modified = False; return True
        except: return False

    def _draw_item(self, y, x, item, width, selected):
        t, ci, pi, _ = item
        if selected: TUI.safe_addstr(self.scr, y, x + 2, ">", curses.color_pair(3) | curses.A_BOLD)
        
        if t == "ch_title":
            # Inline formatting
            ch_count = len(self.hierarchy)
            width = 3 if ch_count >= 100 else 2
            ch_num = str(ci + 1)
            if self.config.get("pad-chapter-id", True):
                ch_num = ch_num.zfill(width)
            label = self.config.get("chapter-name", "Chapter")
            # Truncate label if too long
            label = (label[:6] + "..") if len(label) > 8 else label
            TUI.safe_addstr(self.scr, y, x + 4, f"{label} {ch_num} Title:", curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, y, x + 18, str(self._get_value(item))[:width-22], curses.color_pair(4))
        elif t == "ch_summary":
            TUI.safe_addstr(self.scr, y, x + 6, "Summary:", curses.color_pair(4))
            TUI.safe_addstr(self.scr, y, x + 18, str(self._get_value(item))[:width-22], curses.color_pair(4))
        elif t == "pg_title":
            TUI.safe_addstr(self.scr, y, x + 6, "Title:", curses.color_pair(4))
            TUI.safe_addstr(self.scr, y, x + 18, str(self._get_value(item))[:width-22], curses.color_pair(4))
        elif t == "add_page":
            TUI.safe_addstr(self.scr, y, x + 6, "+ Add page to this chapter...", curses.color_pair(3 if selected else 4) | curses.A_DIM)
        elif t == "add_chapter":
            TUI.safe_addstr(self.scr, y, x + 4, "+ Add new chapter...", curses.color_pair(3 if selected else 4) | curses.A_DIM)

    def _draw_footer(self, h, w):
        footer = "Enter: Edit  d: Delete  Esc: Save & Exit"
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    def _handle_input(self, k):
        if super()._handle_input(k): return True
        
        if k in (ord('\n'), 10):
            item = self.items[self.cursor]; t, ci, pi, _ = item
            if t == "add_chapter": self._add_chapter()
            elif t == "add_page": self._add_page(ci)
            else:
                curr_val = self.hierarchy[ci].get("summary", "") if t == "ch_summary" else self._get_value(item)
                new_val = TextEditor(self.scr, initial_text=curr_val, title="Edit Value").run()
                if new_val is not None: self._set_value(new_val)
            return True
        elif k == ord('d'):
            item = self.items[self.cursor]; t = item[0]
            if t not in ("add_chapter", "add_page"): self._delete_current()
            return True
        
        return False


class SchemeEditor(ListEditor):
    """Color scheme editor"""
    def __init__(self, scr):
        super().__init__(scr, "SCHEME EDITOR")
        self.schemes = json.loads(SCHEMES_FILE.read_text())
        self.theme_names = list(self.schemes.keys())
        self.current_theme = 0
        self._build_items()
        self.box_title = "Colors"
        self.box_width = 70
    
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
            if parts[1] == "grid-opacity":
                try: theme["plot"][parts[1]] = float(val)
                except: theme["plot"][parts[1]] = val
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
    
    def _create_new_scheme(self):
        name = TextEditor(self.scr, initial_text="new-scheme", title="New Scheme Name").run()
        if name and name not in self.schemes:
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

    def refresh(self):
        # Override refresh to add theme selector and headers
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        list_h = min(len(self.items) + 3, h - 8)
        total_h = 3 + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        
        title_str = f"{self.title}{' *' if self.modified else ''}"
        TUI.safe_addstr(self.scr, start_y, (w - len(title_str)) // 2, title_str, curses.color_pair(1) | curses.A_BOLD)
        
        theme_text = f"< {self.theme_names[self.current_theme]} >"
        TUI.safe_addstr(self.scr, start_y + 1, (w - len(theme_text)) // 2, theme_text, curses.color_pair(5) | curses.A_BOLD)
        
        bw = min(self.box_width, w - 4)
        bx = (w - bw) // 2
        left_w = 22
        
        TUI.draw_box(self.scr, start_y + 3, bx, list_h, bw, self.box_title)
        
        TUI.safe_addstr(self.scr, start_y + 4, bx + 4, "Property", curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, start_y + 4, bx + left_w + 2, "Color", curses.color_pair(1) | curses.A_BOLD)
        
        for i in range(1, list_h - 1):
            TUI.safe_addstr(self.scr, start_y + 3 + i, bx + left_w, "│", curses.color_pair(4) | curses.A_DIM)
        
        vis = list_h - 3
        if self.cursor < self.scroll: self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis: self.scroll = self.cursor - vis + 1
        
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.items): break
            y = start_y + 5 + i
            self._draw_item(y, bx, self.items[idx], bw, idx == self.cursor)
            
        self._draw_footer(h, w)
        self.scr.refresh()

    def _draw_item(self, y, x, item, width, selected):
        key, _ = item
        left_w = 22
        
        if selected: TUI.safe_addstr(self.scr, y, x + 2, ">", curses.color_pair(3) | curses.A_BOLD)
        
        label = self._get_label(key)
        TUI.safe_addstr(self.scr, y, x + 4, label[:left_w - 6], curses.color_pair(5 if selected else 4))
        
        hex_val = self._get_value(key)
        color = hex_to_curses_color(hex_val)
        TUI.safe_addstr(self.scr, y, x + left_w + 2, "██", curses.color_pair(color))
        TUI.safe_addstr(self.scr, y, x + left_w + 5, hex_val[:width - left_w - 8], curses.color_pair(4))

    def _draw_footer(self, h, w):
        footer = "n: New  d: Delete  Enter: Edit  Esc: Save & Exit"
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    def _handle_input(self, k):
        if super()._handle_input(k): return True
        
        if k == curses.KEY_LEFT:
            self.current_theme = (self.current_theme - 1) % len(self.theme_names)
            self._build_items(); self.cursor = min(self.cursor, len(self.items) - 1)
            return True
        elif k == curses.KEY_RIGHT:
            self.current_theme = (self.current_theme + 1) % len(self.theme_names)
            self._build_items(); self.cursor = min(self.cursor, len(self.items) - 1)
            return True
        elif k in (ord('\n'), 10):
            key, _ = self.items[self.cursor]
            curr_val = self._get_value(key)
            new_val = TextEditor(self.scr, initial_text=curr_val, title="Edit Color").run()
            if new_val is not None:
                self._set_value(key, new_val)
                self._build_items()
            return True
        elif k == ord('n'): self._create_new_scheme(); return True
        elif k == ord('d'): self._delete_current_scheme(); return True
        
        return False


class SnippetsEditor(ListEditor):
    """Two-column snippet editor"""
    def __init__(self, scr):
        super().__init__(scr, "SNIPPETS EDITOR")
        self._load_snippets()
        self.box_title = "Snippets"
        self.box_width = 80
    
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
        except: pass
        if not self.snippets: self.snippets = [["example", "[example text]"]]
        self._update_items()

    def _update_items(self):
        self.items = self.snippets + [["+ Add new snippet...", ""]]

    def _save_snippets(self):
        lines = []
        for name, definition in self.snippets:
            lines.append(f"#let {name} = {definition}")
        SNIPPETS_FILE.write_text('\n'.join(lines) + '\n')
        self.modified = False
    
    def save(self):
        try: self._save_snippets(); return True
        except: return False

    def _draw_item(self, y, x, item, width, selected):
        name, definition = item
        left_w = 20
        
        if selected: TUI.safe_addstr(self.scr, y, x + 2, ">", curses.color_pair(3) | curses.A_BOLD)
        
        if name == "+ Add new snippet...":
            TUI.safe_addstr(self.scr, y, x + 4, name, curses.color_pair(3 if selected else 4) | curses.A_DIM)
        else:
            TUI.safe_addstr(self.scr, y, x + 4, name[:left_w - 6], curses.color_pair(5 if selected else 4))
            TUI.safe_addstr(self.scr, y, x + left_w + 2, definition[:width - left_w - 6], curses.color_pair(4))

    def refresh(self):
        # Override refresh to add headers
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        list_h = min(len(self.items) + 2, h - 8)
        total_h = 2 + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        
        title_str = f"{self.title}{' *' if self.modified else ''}"
        TUI.safe_addstr(self.scr, start_y, (w - len(title_str)) // 2, title_str, curses.color_pair(1) | curses.A_BOLD)
        
        bw = min(self.box_width, w - 4)
        bx = (w - bw) // 2
        left_w = 20
        
        TUI.draw_box(self.scr, start_y + 2, bx, list_h, bw, self.box_title)
        
        TUI.safe_addstr(self.scr, start_y + 3, bx + 4, "Name", curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, start_y + 3, bx + left_w + 2, "Definition", curses.color_pair(1) | curses.A_BOLD)
        
        for i in range(1, list_h - 1):
            TUI.safe_addstr(self.scr, start_y + 2 + i, bx + left_w, "│", curses.color_pair(4) | curses.A_DIM)
        
        vis = list_h - 3
        if self.cursor < self.scroll: self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis: self.scroll = self.cursor - vis + 1
        
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.items): break
            y = start_y + 4 + i
            self._draw_item(y, bx, self.items[idx], bw, idx == self.cursor)
            
        self._draw_footer(h, w)
        self.scr.refresh()

    def _draw_footer(self, h, w):
        footer = "n: New  d: Delete  Enter: Edit  Esc: Save & Exit"
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    def _handle_input(self, k):
        if super()._handle_input(k): return True
        
        if k in (ord('\n'), 10):
            if self.cursor >= len(self.snippets):
                # Add new
                self.snippets.append(["new_snippet", "[definition]"])
                self.cursor = len(self.snippets) - 1
                self.modified = True
                self._update_items()
                # Edit immediately
                name, definition = self.snippets[self.cursor]
                new_name = TextEditor(self.scr, initial_text=name, title="New Snippet Name").run()
                if new_name is not None: self.snippets[self.cursor][0] = new_name
                new_def = TextEditor(self.scr, initial_text=definition, title="New Definition").run()
                if new_def is not None: self.snippets[self.cursor][1] = new_def
            else:
                # Edit existing
                name, definition = self.snippets[self.cursor]
                new_name = TextEditor(self.scr, initial_text=name, title="Edit Snippet Name").run()
                if new_name is not None:
                    self.snippets[self.cursor][0] = new_name
                    self.modified = True
                new_def = TextEditor(self.scr, initial_text=definition, title="Edit Definition").run()
                if new_def is not None:
                    self.snippets[self.cursor][1] = new_def
                    self.modified = True
            return True
        elif k == ord('n'):
            self.snippets.append(["new_snippet", "[definition]"])
            self.cursor = len(self.snippets) - 1
            self.modified = True
            self._update_items()
            return True
        elif k == ord('d') and self.cursor < len(self.snippets) and self.snippets:
            del self.snippets[self.cursor]
            if self.cursor >= len(self.snippets): self.cursor = max(0, len(self.snippets) - 1)
            self.modified = True
            self._update_items()
            return True
        
        return False


class IndexignoreEditor(ListEditor):
    """Simple editor for .indexignore file - list of ignored file IDs."""
    def __init__(self, scr):
        super().__init__(scr, "INDEXIGNORE EDITOR")
        self.ignored = sorted(load_indexignore())
        self.items = self.ignored if self.ignored else []
        self.box_title = "Ignored Files"
        self.box_width = 50
    
    def save(self):
        save_indexignore(set(self.ignored))
        self.modified = False
        return True
    
    def _draw_item(self, y, x, item, width, selected):
        if selected:
            TUI.safe_addstr(self.scr, y, x + 2, ">", curses.color_pair(3) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, y, x + 4, item, curses.color_pair(1) | curses.A_BOLD)
        else:
            TUI.safe_addstr(self.scr, y, x + 4, item, curses.color_pair(4))
    
    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        bw = min(self.box_width, w - 4)
        bh = min(h - 8, 20)
        bx = (w - bw) // 2
        by = (h - bh) // 2
        
        TUI.draw_box(self.scr, by, bx, bh, bw, f" {self.title} ")
        TUI.safe_addstr(self.scr, by + 1, bx + 2, f"Ignored files: {len(self.ignored)}", curses.color_pair(4) | curses.A_DIM)
        
        visible = bh - 5
        if self.cursor < self.scroll: self.scroll = self.cursor
        elif self.cursor >= self.scroll + visible: self.scroll = self.cursor - visible + 1
        
        if not self.ignored:
            TUI.safe_addstr(self.scr, by + 3, bx + 4, "(no ignored files)", curses.color_pair(4) | curses.A_DIM)
        else:
            for i in range(visible):
                idx = self.scroll + i
                if idx >= len(self.ignored): break
                y = by + 3 + i
                self._draw_item(y, bx, self.ignored[idx], bw, idx == self.cursor)
        
        self._draw_footer(h, w)
        self.scr.refresh()

    def _draw_footer(self, h, w):
        footer = "a: Add  d: Delete  Esc: Save & Exit"
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
    
    def _handle_input(self, k):
        if k in (curses.KEY_UP, ord('k')) and self.ignored:
            self.cursor = max(0, self.cursor - 1)
            return True
        elif k in (curses.KEY_DOWN, ord('j')) and self.ignored:
            self.cursor = min(len(self.ignored) - 1, self.cursor + 1)
            return True
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
                if new_id and new_id not in self.ignored:
                    self.ignored.append(new_id)
                    self.ignored.sort()
                    self.items = self.ignored
                    self.modified = True
            except: pass
            curses.noecho()
            curses.curs_set(0)
            return True
        elif k == ord('d') and self.ignored:
            del self.ignored[self.cursor]
            self.items = self.ignored
            self.cursor = min(self.cursor, len(self.ignored) - 1) if self.ignored else 0
            self.modified = True
            return True
        return False


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
        TUI.init_colors()
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
        """Check for user input during build."""
        try:
            k = self.scr.getch()
            if k == -1: return True
            if k == 27: return False # Esc to cancel
            if k == ord('v'):
                self.view = "typst" if self.view == "normal" else "normal"
                self.scroll = 0
            elif self.view == "typst":
                if k in (curses.KEY_UP, ord('k')):
                    self.scroll = max(0, self.scroll - 1)
                elif k in (curses.KEY_DOWN, ord('j')):
                    self.scroll = min(max(0, len(self.typst_logs) - 1), self.scroll + 1)
        except: pass
        return True
    
    def refresh(self):
        if not self.check_input(): return False
        
        self.h, self.w = self.scr.getmaxyx()
        self.scr.clear()
        
        lh = min(15, self.h - 12)
        total_h = 1 + 5 + 1 + lh + 1  # title + progress box + gap + log box + footer
        start_y = max(0, (self.h - total_h) // 2)
        
        title = "NOTEWORTHY BUILD SYSTEM" + (" [DEBUG]" if self.debug_mode else "")
        TUI.safe_addstr(self.scr, start_y, (self.w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
        
        bw, bx = min(60, self.w - 4), (self.w - min(60, self.w - 4)) // 2
        TUI.draw_box(self.scr, start_y + 2, bx, 5, bw, "Progress")
        if self.phase: TUI.safe_addstr(self.scr, start_y + 3, bx + 2, self.phase[:bw-4], curses.color_pair(5))
        if self.task: TUI.safe_addstr(self.scr, start_y + 4, bx + 2, f"→ {self.task}"[:bw-4], curses.color_pair(4))
        if self.total:
            filled = int((bw - 12) * self.progress / self.total)
            TUI.safe_addstr(self.scr, start_y + 5, bx + 2, "█" * filled + "░" * (bw - 12 - filled), curses.color_pair(3))
            TUI.safe_addstr(self.scr, start_y + 5, bx + bw - 8, f"{100*self.progress//self.total:3d}%", curses.color_pair(3) | curses.A_BOLD)
        
        if self.view == "typst":
            TUI.draw_box(self.scr, start_y + 8, bx, lh, bw, "Typst Output (↑↓ scroll)")
            if self.typst_logs:
                for i, line in enumerate(self.typst_logs[self.scroll:self.scroll + lh - 2]):
                    c = 6 if 'error:' in line.lower() else 3 if 'warning:' in line.lower() else 4
                    TUI.safe_addstr(self.scr, start_y + 9 + i, bx + 2, line[:bw-4], curses.color_pair(c))
            else:
                TUI.safe_addstr(self.scr, start_y + 9, bx + 2, "(no output yet)", curses.color_pair(4) | curses.A_DIM)
        else:
            TUI.draw_box(self.scr, start_y + 8, bx, lh, bw, "Build Log")
            for i, (msg, ok) in enumerate(self.logs[-(lh-2):]):
                TUI.safe_addstr(self.scr, start_y + 9 + i, bx + 2, ("✓ " if ok else "  ") + msg[:bw-6], curses.color_pair(2 if ok else 4))
        
        TUI.safe_addstr(self.scr, self.h - 1, (self.w - 50) // 2, "Esc: Cancel  |  v: Toggle Typst Log", curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
        return True

# =============================================================================
# BUILD LOGIC
# =============================================================================

def auto_fix_config():
    """No longer needed - folder structure is now purely numeric."""
    pass

def run_build(scr, args, hierarchy, opts):
    if opts['debug']:
        # Enable file logging if Debug Mode was toggled in TUI
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        logging.basicConfig(filename='build_debug.log', level=logging.DEBUG, format='%(asctime)s - %(message)s')
        logging.info("Debug mode enabled via TUI")

    logging.info("Starting run_build")
    auto_fix_config() # Run auto-fix before build
    ui = BuildUI(scr, opts['debug'])
    scr.keypad(True)   # Enable keypad for special keys
    scr.nodelay(False) # Disable nodelay
    scr.timeout(0)     # timeout(0) = non-blocking getch, returns -1 immediately if no key
    
    ui.log("Checking dependencies...")
    check_dependencies()
    ui.log("Dependencies OK", True)
    
    if BUILD_DIR.exists(): shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir()
    ui.log("Build directory prepared", True)
    
    pages = opts.get('selected_pages', [])
    by_ch = {}
    for ci, ai in pages:
        by_ch.setdefault(ci, []).append(ai)
    
    chapters = [(i, hierarchy[i]) for i in sorted(by_ch.keys())]
    ui.log(f"Building {len(pages)} pages from {len(chapters)} chapters", True)
    
    total = (3 if opts['frontmatter'] else 0) + sum(1 + len(by_ch[ci]) for ci, _ in chapters)
    ui.set_phase("Compiling Sections")
    ui.set_progress(0, total + 1)
    
    page_map, current, pdfs, prog = {}, 1, [], 0
    flags = opts.get('typst_flags', [])
    
    if opts['frontmatter']:
        for target, name, label in [("cover", "00_cover.pdf", "Cover"), ("preface", "01_preface.pdf", "Preface"), ("outline", "02_outline.pdf", "TOC")]:
            ui.set_task(label)
            out = BUILD_DIR / name
            compile_target(target, out, extra_flags=flags, callback=ui.refresh, log_callback=ui.log_typst)
            pdfs.append(out); page_map[target] = current; current += get_pdf_page_count(out)
            prog += 1; ui.set_progress(prog, total + 1)
            ui.log(f"{label} compiled", True)
    
    for ci, ch in chapters:
        ch_id = str(ci + 1)
        ui.set_task(f"Chapter {ch_id}: {ch['title']}")
        out = BUILD_DIR / f"10_chapter_{ci}_cover.pdf"
        page_map[f"chapter-{ch_id}"] = current
        compile_target(f"chapter-{ci}", out, page_offset=current, extra_flags=flags, callback=ui.refresh, log_callback=ui.log_typst)
        pdfs.append(out); current += get_pdf_page_count(out)
        prog += 1; ui.set_progress(prog, total + 1)
        
        for ai in sorted(by_ch[ci]):
            p = ch["pages"][ai]
            pg_id = str(ai + 1)
            ui.set_task(f"Section {pg_id}: {p['title']}")
            out = BUILD_DIR / f"20_page_{ci}_{ai}.pdf"
            page_map[f"{ci}/{ai}"] = current
            compile_target(f"{ci}/{ai}", out, page_offset=current, extra_flags=flags, callback=ui.refresh, log_callback=ui.log_typst)
            pdfs.append(out); current += get_pdf_page_count(out)
            prog += 1; ui.set_progress(prog, total + 1)
        
        ui.log(f"Chapter {ch_id} compiled", True)
    
    if opts['frontmatter']:
        ui.set_task("Regenerating TOC")
        out = BUILD_DIR / "02_outline.pdf"
        compile_target("outline", out, page_offset=page_map["outline"], page_map=page_map, extra_flags=flags, callback=ui.refresh, log_callback=ui.log_typst)
        ui.log("TOC regenerated", True)
    
    ui.log(f"Total pages: {current - 1}", True)
    
    ui.set_phase("Merging PDFs")
    logging.info(f"Merging {len(pdfs)} PDFs to {OUTPUT_FILE}")
    method = merge_pdfs(pdfs, OUTPUT_FILE)
    logging.info(f"Merge method: {method}, Success: {bool(method)}")
    
    if not method or not OUTPUT_FILE.exists():
        ui.log("Merge failed!", False)
        ui.set_phase("Failed")
        scr.nodelay(False)
        show_error_screen(scr, "Failed to merge PDFs. Individual files left in " + str(BUILD_DIR))
        return

    ui.log(f"Merged with {method}", True)
    
    ui.set_phase("Adding Metadata")
    bm = BUILD_DIR / "bookmarks.txt"
    create_pdf_metadata(chapters, page_map, bm)
    apply_pdf_metadata(OUTPUT_FILE, bm, "Noteworthy Framework", "Sihoo Lee, Lee Hojun")
    ui.log("PDF metadata applied", True)
    
    if opts['leave_individual']:
        zip_build_directory(BUILD_DIR)
        ui.log("Individual PDFs archived", True)
    
    if OUTPUT_FILE.exists() and BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        ui.log("Build directory cleaned", True)
    
    ui.set_phase("BUILD COMPLETE!")
    ui.set_progress(total + 1, total + 1)
    ui.log(f"Created {OUTPUT_FILE} ({current - 1} pages)", True)
    
    scr.nodelay(False)
    scr.timeout(-1) # Reset to blocking mode
    curses.flushinp() # Clear input buffer
    with open("debug_trace.log", "a") as f: f.write("Calling show_success_screen\n")
    show_success_screen(scr, current - 1, ui.has_warnings, ui.typst_logs)

# =============================================================================
# INIT WIZARD
# =============================================================================

class InitWizard:
    """First-time setup wizard for config.json"""
    def __init__(self, scr):
        self.scr = scr
        
        themes = ["rose-pine", "dark", "light", "nord", "dracula", "gruvbox", "catppuccin-mocha", "catppuccin-latte", "solarized-dark", "solarized-light", "tokyo-night", "everforest", "moonlight", "print"] # Fallback
        if SCHEMES_FILE.exists():
             try:
                 schemes = json.loads(SCHEMES_FILE.read_text())
                 if schemes: themes = list(schemes.keys())
             except: pass

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
            "render-sample-count": 5000,
            "render-implicit-count": 100,
            "display-mode": "rose-pine",
            "pad-chapter-id": True,
            "pad-page-id": True,
        }
        self.steps = [
            ("title", "Document Title", "Enter the main title of your document:", "str"),
            ("subtitle", "Subtitle", "Enter a subtitle (optional, press Enter to skip):", "str"),
            ("authors", "Authors", "Enter author names (comma-separated):", "list"),
            ("affiliation", "Affiliation", "Enter your organization/affiliation:", "str"),
            ("display-mode", "Color Theme", "Use ←/→ to select, Enter to confirm:", "choice", themes),
            ("font", "Body Font", "Enter body font name:", "str"),
            ("title-font", "Title Font", "Enter title font name:", "str"),
            ("chapter-name", "Chapter Label", "What to call chapters (e.g., 'Chapter', 'Unit'):", "str"),
            ("subchap-name", "Section Label", "What to call sections (e.g., 'Section', 'Lesson'):", "str"),
        ]
        self.current_step = 0
        self.choice_index = 0  # For choice type slider
        # Input position tracking for responsive layout
        self.input_y = 0
        self.input_x = 0
        self.input_w = 50
        TUI.init_colors()
    
    def refresh(self):
        h_raw, w_raw = self.scr.getmaxyx()
        h, w = h_raw - 2, w_raw - 2
        self.scr.clear()
        
        layout = "vert"
        if w > 100: layout = "horz"
        
        if layout == "horz":
            lh = len(LOGO)
            ly = max(0, (h - lh) // 2)
            lx = max(0, (w - 16 - 60) // 2)
            
            for i, line in enumerate(LOGO):
                if ly + i < h:
                    TUI.safe_addstr(self.scr, ly + i, lx, line, curses.color_pair(1) | curses.A_BOLD)
            
            sy = ly + lh + 2
            for i, step in enumerate(self.steps):
                if sy + i >= h - 1: break
                marker = ">" if i == self.current_step else " "
                style = curses.color_pair(3) | curses.A_BOLD if i == self.current_step else curses.color_pair(4)
                TUI.safe_addstr(self.scr, sy + i, lx + 2, f"{marker} {step[1]}", style)

            dx = lx + 20 + 4
            dw = 55
            dy = max(0, (h - 16) // 2)
            
            TUI.draw_box(self.scr, dy, dx, 16, dw, "Setup Wizard")
            
            step = self.steps[self.current_step]
            key, label, prompt, stype = step[0], step[1], step[2], step[3]
            
            TUI.safe_addstr(self.scr, dy + 2, dx + 2, f"Step {self.current_step + 1}/{len(self.steps)}: {label}", curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, dy + 4, dx + 2, prompt[:dw-4], curses.color_pair(4))
            
            if stype == "choice":
                choices = step[4]
                choice_text = f"◀  {choices[self.choice_index]}  ▶"
                TUI.safe_addstr(self.scr, dy + 7, dx + (dw - len(choice_text)) // 2, choice_text, curses.color_pair(5) | curses.A_BOLD)
                dots = "".join("●" if i == self.choice_index else "○" for i in range(len(choices)))
                TUI.safe_addstr(self.scr, dy + 8, dx + (dw - len(dots)) // 2, dots, curses.color_pair(4) | curses.A_DIM)
            else:
                curr_val = self.config.get(key, "")
                if isinstance(curr_val, list): curr_val = ", ".join(curr_val)
                if curr_val:
                     TUI.safe_addstr(self.scr, dy + 7, dx + 2, f"Default: {str(curr_val)[:dw-12]}", curses.color_pair(4) | curses.A_DIM)
            
            # Store input position for horizontal layout
            self.input_y = dy + 10
            self.input_x = dx + 2
            self.input_w = dw - 4
            
            footer = "Enter:Next  Back:Prev  Esc:Cancel"
            TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

        else:
            total_h = 16
            start_y = max(1, (h - total_h) // 2)
            
            TUI.safe_addstr(self.scr, start_y, (w - 22) // 2, "NOTEWORTHY SETUP WIZARD", curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, start_y + 1, (w - 40) // 2, "Let's set up your document configuration", curses.color_pair(4) | curses.A_DIM)
            
            prog = f"Step {self.current_step + 1} of {len(self.steps)}"
            TUI.safe_addstr(self.scr, start_y + 3, (w - len(prog)) // 2, prog, curses.color_pair(5))
            
            step = self.steps[self.current_step]
            key, label, prompt, stype = step[0], step[1], step[2], step[3]
            
            bw = min(60, w - 4)
            bx = (w - bw) // 2
            TUI.draw_box(self.scr, start_y + 5, bx, 7, bw, label)
            
            TUI.safe_addstr(self.scr, start_y + 6, bx + 2, prompt[:bw-4], curses.color_pair(4))
            
            if stype == "choice":
                choices = step[4]
                choice_text = f"◀  {choices[self.choice_index]}  ▶"
                TUI.safe_addstr(self.scr, start_y + 8, (w - len(choice_text)) // 2, choice_text, curses.color_pair(5) | curses.A_BOLD)
                dots = "".join("●" if i == self.choice_index else "○" for i in range(len(choices)))
                TUI.safe_addstr(self.scr, start_y + 9, (w - len(dots)) // 2, dots, curses.color_pair(4) | curses.A_DIM)
                footer = "←→:Select  Enter:Confirm  Backspace:Back  Esc:Cancel"
            else:
                curr_val = self.config.get(key, "")
                if isinstance(curr_val, list):
                    curr_val = ", ".join(curr_val)
                if curr_val:
                    TUI.safe_addstr(self.scr, start_y + 8, bx + 2, f"Default: {str(curr_val)[:bw-12]}", curses.color_pair(4) | curses.A_DIM)
                footer = "Enter:Input  Backspace:Back  Esc:Cancel"
            
            # Store input position for vertical layout
            self.input_y = start_y + 10
            self.input_x = bx + 2
            self.input_w = bw - 4
            
            TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
            
        self.scr.refresh()
    
    def get_input(self):
        curses.echo()
        curses.curs_set(1)
        
        # Ensure we are using the latest calculated position
        y, x = self.input_y, self.input_x
        
        # Clear the input area first to prevent ghosting
        try:
            self.scr.move(y, x)
            self.scr.clrtoeol()
            TUI.safe_addstr(self.scr, y, x, "> ", curses.color_pair(3) | curses.A_BOLD)
            self.scr.refresh()
            
            # Explicitly move cursor to input start position for getstr
            # Note: getstr(y, x, n) reads from (y,x), so we must pass the shifted coordinate
            value = self.scr.getstr(y, x + 2, self.input_w - 4).decode('utf-8').strip()
        except:
            value = ""
        
        curses.noecho()
        curses.curs_set(0)
        return value
    
    def run(self):
        # Welcome Screen
        while True:
            if not TUI.check_terminal_size(self.scr): return None
            h, w = self.scr.getmaxyx()
            self.scr.clear()
            
            bh, bw = 8, min(60, w - 4)
            bx, by = (w - bw) // 2, (h - bh) // 2
            
            TUI.draw_box(self.scr, by, bx, bh, bw, " Welcome ")
            TUI.safe_addstr(self.scr, by + 2, bx + 2, "welcome to noteworthy!", curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, by + 3, bx + 2, "We will guide you to initializing your project.", curses.color_pair(4))
            
            footer = "Press Enter to begin..."
            TUI.safe_addstr(self.scr, by + 6, bx + (bw - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
            
            self.scr.refresh()
            k = self.scr.getch()
            if k == 27: return None
            if k in (ord('\n'), 10, curses.KEY_ENTER): break
            
        while self.current_step < len(self.steps):
            if not TUI.check_terminal_size(self.scr): return None
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
                    TUI.safe_addstr(self.scr, h - 2, (w - 20) // 2, "Title is required!", curses.color_pair(6) | curses.A_BOLD)
                    self.scr.refresh()
                    curses.napms(1000)
        
        try:
            CONFIG_FILE.write_text(json.dumps(self.config, indent=4))
            return True
        except:
            return None

class HierarchyWizard:
    """Wizard for initializing hierarchy.json automatically"""
    def __init__(self, scr):
        self.scr = scr

    def run(self):
        # Non-interactive: Auto-scan or create default
        try:
            hierarchy = []
            content_dir = Path("content")
            
            # Option 1: Scan 'content' folder if it exists and has chapters
            has_content = False
            if content_dir.exists():
                chapters = {}
                # Scan numeric-only folders (01, 02, etc.)
                for ch_dir in sorted(content_dir.iterdir()):
                    if not ch_dir.is_dir() or not ch_dir.name.isdigit():
                        continue
                    try:
                        ch_num = int(ch_dir.name)
                        pages = []
                        for p in sorted(ch_dir.glob("*.typ")):
                            pages.append({"id": p.stem, "title": "Untitled Section"})
                        if pages:
                            # Get chapter-name from config for title display
                            try:
                                config = json.loads(CONFIG_FILE.read_text())
                                chap_name = config.get("chapter-name", "Chapter")
                            except:
                                chap_name = "Chapter"
                            chapters[ch_num] = {
                                "title": f"{chap_name} {ch_num}",
                                "summary": "",
                                "pages": pages
                            }
                            has_content = True
                    except: pass
                if has_content:
                    hierarchy = [chapters[k] for k in sorted(chapters.keys())]
            
            # Option 2: Create default structure if no content found
            if not has_content:
                # Get chapter/section names from config if available
                try:
                    config = json.loads(CONFIG_FILE.read_text())
                    chap_name = config.get("chapter-name", "Chapter")
                    sect_name = config.get("subchap-name", "Section")
                except:
                    chap_name = "Chapter"
                    sect_name = "Section"
                    
                hierarchy = [
                    {
                        "title": f"First {chap_name}",
                        "summary": "Getting started",
                        "pages": [{"id": "01.01", "title": f"First {sect_name}"}]
                    }
                ]
            
            HIERARCHY_FILE.parent.mkdir(parents=True, exist_ok=True)
            HIERARCHY_FILE.write_text(json.dumps(hierarchy, indent=4))
            
            # Show notice
            h, w = self.scr.getmaxyx()
            self.scr.clear()
            msg = "Hierarchy auto-generated from content" if has_content else "Created default hierarchy structure"
            TUI.safe_addstr(self.scr, h // 2, (w - len(msg)) // 2, msg, curses.color_pair(1) | curses.A_BOLD)
            self.scr.refresh()
            curses.napms(1000)
            
            # Return 'edit' to signal that we should open the editor
            return 'edit'
        except: return None

class SchemesWizard:
    """Wizard for initializing schemes.json"""
    def __init__(self, scr):
        self.scr = scr
    
    def run(self):
        # For now, just auto-restore default schemes as it's complex to build from scratch
        # But show a confirmation dialog
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        bw = min(60, w - 4)
        bh = 8
        bx = (w - bw) // 2
        by = (h - bh) // 2
        
        TUI.draw_box(self.scr, by, bx, bh, bw, "SCHEMES SETUP")
        TUI.safe_addstr(self.scr, by + 2, bx + 2, "Schemes configuration is missing.", curses.color_pair(4))
        TUI.safe_addstr(self.scr, by + 3, bx + 2, "Restore default color themes?", curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, by + 5, bx + 2, "Press Enter to Restore  |  Esc to Cancel", curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
        
        while True:
            if not TUI.check_terminal_size(self.scr): return None
            k = self.scr.getch()
            if k == 27: return None
            elif k in (ord('\n'), 10, curses.KEY_ENTER):
                break
        
        try:
             # Use a minimal embedded default scheme if source is missing
            minimal_schemes = {
                "dark": {
                    "page-fill": "#262323",
                    "text-main": "#d8d0cc",
                    "text-heading": "#ddbfa1",
                    "text-muted": "#8f8582",
                    "text-accent": "#d49c93",
                    "blocks": {},
                    "plot": {"stroke": "#ddbfa1", "highlight": "#d4aa8e", "grid-opacity": 0.15}
                }
            }
            
            # Try to find better defaults from backup or templates if possible
            # Ideally we'd have the full JSON embedded, but for brevity we use minimal or copy
            default_src = Path("templates/config/schemes.json")
            if default_src.exists() and default_src != SCHEMES_FILE:
                shutil.copy(default_src, SCHEMES_FILE)
            else:
                SCHEMES_FILE.parent.mkdir(parents=True, exist_ok=True)
                SCHEMES_FILE.write_text(json.dumps(minimal_schemes, indent=4))
            return True
        except: return None

def needs_init():
    """Check if we need to run any init wizard"""
    return not (CONFIG_FILE.exists() and HIERARCHY_FILE.exists() and SCHEMES_FILE.exists())

# =============================================================================
# ENTRY POINTS
# =============================================================================

class SyncWizard:
    """Wizard for resolving hierarchy vs content discrepancies"""
    def __init__(self, scr, missing_files, new_files):
        self.scr = scr
        self.missing_files = missing_files
        self.new_files = new_files
        self.config = load_config_safe()
        try: self.hierarchy = json.loads(HIERARCHY_FILE.read_text())
        except: self.hierarchy = []
        
    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        TUI.safe_addstr(self.scr, 2, (w - 25) // 2, "HIERARCHY SYNC REQUIRED", curses.color_pair(6) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, 3, (w - 45) // 2, "The hierarchy.json does not match your content folder.", curses.color_pair(4))
        
        # Calculate layout
        col_w = (w - 8) // 2
        left_x = 2
        right_x = left_x + col_w + 4
        list_h = h - 13
        
        # Left Column: Missing on Disk (Only in Hierarchy)
        TUI.draw_box(self.scr, 5, left_x, list_h + 2, col_w, f" Missing on Disk ({len(self.missing_files)}) ")
        for i, f in enumerate(self.missing_files[:list_h]):
            name = get_formatted_name(f, self.hierarchy, self.config)
            TUI.safe_addstr(self.scr, 6 + i, left_x + 2, f"- {name} ({f})", curses.color_pair(4))
            
        # Right Column: New on Disk (Only in Content)
        TUI.draw_box(self.scr, 5, right_x, list_h + 2, col_w, f" New on Disk ({len(self.new_files)}) ")
        for i, f in enumerate(self.new_files[:list_h]):
            name = get_formatted_name(f, self.hierarchy, self.config)
            TUI.safe_addstr(self.scr, 6 + i, right_x + 2, f"+ {name} ({f})", curses.color_pair(2))
            
        # Options
        opts_y = h - 5
        TUI.safe_addstr(self.scr, opts_y, 4, "[A] Adopt Disk State (Update Hierarchy)", curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, opts_y + 1, 8, "Removes missing, Adds new", curses.color_pair(4))
        
        TUI.safe_addstr(self.scr, opts_y, w // 2 + 4, "[B] Create Missing Files", curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, opts_y + 1, w // 2 + 8, "Creates scaffold for missing files", curses.color_pair(4))
        
        TUI.safe_addstr(self.scr, opts_y + 3, 4, "[D] Delete Extra Files", curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, opts_y + 4, 8, "Deletes files not in hierarchy", curses.color_pair(4))
        
        TUI.safe_addstr(self.scr, h - 3, (w - 20) // 2, "Esc: Cancel  Q: Quit", curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()

    def run(self):
        while True:
            if not TUI.check_terminal_size(self.scr): return None
            self.refresh()
            k = self.scr.getch()
            
            if k == 27 or k == ord('q'): return None
            
            if k in (ord('a'), ord('A')):
                return self.adopt_disk()
            elif k in (ord('b'), ord('B')):
                return self.adopt_hierarchy()
            elif k in (ord('d'), ord('D')):
                return self.delete_extra()
                
    def adopt_disk(self):
        """Update hierarchy.json to match content on disk (index-based)"""
        try:
            # Scan content/0, content/1...
            new_hierarchy = []
            content_dir = Path("content")
            if not content_dir.exists(): return False
            
            # Find max chapter index
            ch_idxs = []
            for d in content_dir.iterdir():
                if d.is_dir() and d.name.isdigit():
                    ch_idxs.append(int(d.name))
            ch_idxs.sort()
            
            for i in ch_idxs:
                # Try to preserve titles from old hierarchy if indices match
                old_ch = self.hierarchy[i] if i < len(self.hierarchy) else {}
                title = old_ch.get("title", f"Chapter {i+1}")
                summary = old_ch.get("summary", "")
                
                pages = []
                ch_dir = content_dir / str(i)
                pg_idxs = []
                for f in ch_dir.glob("*.typ"):
                    if f.stem.isdigit():
                        pg_idxs.append(int(f.stem))
                pg_idxs.sort()
                
                for j in pg_idxs:
                    old_pg = old_ch.get("pages", [])[j] if "pages" in old_ch and j < len(old_ch["pages"]) else {}
                    pg_title = old_pg.get("title", "Untitled Section")
                    pages.append({"title": pg_title})
                    
                new_hierarchy.append({"title": title, "summary": summary, "pages": pages})
                
            HIERARCHY_FILE.write_text(json.dumps(new_hierarchy, indent=4))
            return True
        except Exception as e:
            return False

    def adopt_hierarchy(self):
        """Create missing files on disk to match hierarchy (index-based)"""
        try:
            for missing in self.missing_files:
                path = Path(missing)
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    path.write_text(f'#import "../../templates/templater.typ": *\n\nWrite your content here.')
            return True

        except:
            return False

    def delete_extra(self):
        """Delete extra files on disk"""
        try:
            for f in self.new_files:
                path = Path(f)
                if path.exists(): path.unlink()
                # Remove empty chapter dir if empty
                try:
                    if path.parent.exists() and not any(path.parent.iterdir()):
                        path.parent.rmdir()
                except: pass
            return True
        except:
            return False

def restore_templates(scr):
    """Check and restore missing template files from GitHub"""
    # List of files to exclude from auto-restore (handled by specific wizards)
    EXCLUDE_FILES = {
        "templates/config/config.json",
        "templates/config/hierarchy.json",
        #"templates/config/schemes.json" # Schemes wizard handles this, but restoring from repo is also a valid strategy. Let's exclude to keep wizard.
    }
    
    try:
        # Fetch file list from GitHub API (lightweight JSON)
        api_url = "https://api.github.com/repos/sihooleebd/noteworthy/git/trees/master?recursive=1"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Noteworthy-Builder'})
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
        if 'tree' not in data: return

        # Identify missing files
        missing_files = []
        for item in data['tree']:
            if item['type'] == 'blob' and item['path'].startswith('templates/'):
                path_str = item['path']
                if path_str in EXCLUDE_FILES: continue
                
                if path_str == "templates/config/preface.typ":
                    local_path = Path(path_str)
                    if not local_path.exists():
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                        local_path.write_text("")
                    continue
                
                local_path = Path(path_str)
                if not local_path.exists():
                    missing_files.append(path_str)
        
        if not missing_files: return

        # Download only missing files
        scr.clear()
        h, w = scr.getmaxyx()
        msg = f"Restoring {len(missing_files)} missing templates..."
        TUI.safe_addstr(scr, h // 2 + 2, (w - len(msg)) // 2, msg, curses.color_pair(4))
        scr.refresh()
        
        base_raw_url = "https://raw.githubusercontent.com/sihooleebd/noteworthy/master/"
        
        for fpath in missing_files:
            local_path = Path(fpath)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download individual file
            safe_path = urllib.parse.quote(fpath)
            file_url = f"{base_raw_url}{safe_path}"
            
            with urllib.request.urlopen(file_url, timeout=10) as response, open(local_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
                            
        msg = "Restoration complete!"
        TUI.safe_addstr(scr, h // 2 + 3, (w - len(msg)) // 2, msg, curses.color_pair(2))
        scr.refresh()
        curses.napms(1000)
                    
    except Exception:
        pass

class MainMenu:
    def __init__(self, scr):
        self.scr = scr
        self.options = [
            ("e", "Editor", "Edit configuration and content"),
            ("b", "Builder", "Build PDF document")
        ]
        self.selected = 1 # Default to Builder

    def run(self):
        self.scr.timeout(-1) # Ensure blocking mode
        while True:
            if not TUI.check_terminal_size(self.scr): return None
            h_raw, w_raw = self.scr.getmaxyx()
            h, w = h_raw - 2, w_raw - 2
            self.scr.clear()
            
            lh = len(LOGO)
            layout = "vert" 
            # Need: logo(16) + title(2) + gap(2) + buttons(5) + labels(1) + margin(2) ~ 28 lines
            # With footer at h-3, valid height is h-4.
            # If h < 34, switch to horizontal to be safe.
            if h < lh + 18 and w > 80: layout = "horz"
            
            if layout == "vert":
                # Vertical Layout (Centered)
                start_y = max(1, (h - lh - 10) // 2)
                lgx = (w - 14) // 2
                
                for i, line in enumerate(LOGO):
                    TUI.safe_addstr(self.scr, start_y + i, lgx, line, curses.color_pair(1) | curses.A_BOLD)
                TUI.safe_addstr(self.scr, start_y + lh + 1, (w - 10) // 2, "NOTEWORTHY", curses.color_pair(1) | curses.A_BOLD)

                btn_y = start_y + lh + 4
                btn_w = 20
                total_w = (btn_w * 2) + 4
                start_x = (w - total_w) // 2
                
                for i, (key, label, desc) in enumerate(self.options):
                    bx = start_x + (i * (btn_w + 4))
                    style = curses.color_pair(2) | curses.A_BOLD if i == self.selected else curses.color_pair(4)
                    TUI.draw_box(self.scr, btn_y, bx, 5, btn_w, "")
                    TUI.safe_addstr(self.scr, btn_y + 2, bx + (btn_w - len(label)) // 2, label, style)
                    TUI.safe_addstr(self.scr, btn_y + 5, bx + (btn_w - 3) // 2, f"({key.upper()})", curses.color_pair(4) | curses.A_DIM)
            else:
                # Horizontal Layout (Logo Left, Buttons Right)
                total_w = 16 + 8 + 30 # Logo width + gap + Button width
                start_x = (w - total_w) // 2
                start_y = (h - lh) // 2
                
                # Logo Left
                for i, line in enumerate(LOGO):
                    TUI.safe_addstr(self.scr, start_y + i, start_x, line, curses.color_pair(1) | curses.A_BOLD)
                TUI.safe_addstr(self.scr, start_y + lh + 1, start_x + 2, "NOTEWORTHY", curses.color_pair(1) | curses.A_BOLD)
                
                # Buttons Right (Vertical stack)
                btn_x = start_x + 24
                btn_start_y = start_y + (lh - 10) // 2
                btn_w = 20
                
                for i, (key, label, desc) in enumerate(self.options):
                    by = btn_start_y + (i * 6)
                    style = curses.color_pair(2) | curses.A_BOLD if i == self.selected else curses.color_pair(4)
                    TUI.draw_box(self.scr, by, btn_x, 5, btn_w, "")
                    TUI.safe_addstr(self.scr, by + 2, btn_x + (btn_w - len(label)) // 2, label, style)
                    TUI.safe_addstr(self.scr, by + 2, btn_x + btn_w + 2, f"({key.upper()})", curses.color_pair(4) | curses.A_DIM)

            # Responsive adjustments
            footer = "Arrows: Select  Enter: Confirm  Esc: Quit"
            if layout == "vert":
                footer_y = btn_y + 7
                # If content pushes into footer area, shift up or hide logo text
                if footer_y > h - 4:
                    start_y = max(0, start_y - (footer_y - (h - 4)))
            
            TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
            
            self.scr.refresh()
            
            k = self.scr.getch()
            if k == 27: return None  # Esc
            elif k == ord('?'):
                show_keybindings_menu(self.scr)
            elif k in (curses.KEY_LEFT, curses.KEY_UP): self.selected = max(0, self.selected - 1)
            elif k in (curses.KEY_RIGHT, curses.KEY_DOWN): self.selected = min(len(self.options) - 1, self.selected + 1)
            elif k == ord('e'): return "editor"
            elif k == ord('b'): return "builder"
            elif k in (curses.KEY_ENTER, 10):
                return self.options[self.selected][1].lower()

def run_app(scr, args):
    TUI.init_colors()
    if not TUI.check_terminal_size(scr): return
    
    # Restore missing templates from remote
    restore_templates(scr)
    
    # Check if we need to run the init wizard
    if needs_init():
        # Check config.json
        if not CONFIG_FILE.exists():
            wizard = InitWizard(scr)
            if wizard.run() is None:
                return  # User cancelled
        
        # Check hierarchy.json
        if not HIERARCHY_FILE.exists():
             wizard = HierarchyWizard(scr)
             res = wizard.run()
             if res is None:
                 return # User cancelled
             elif res == 'edit':
                 # Open hierarchy editor immediately to let user customize
                 editor = HierarchyEditor(scr)
                 editor.run()

        # Check schemes.json
        if not SCHEMES_FILE.exists():
            wizard = SchemesWizard(scr)
            if wizard.run() is None:
                return # User cancelled
    
    scr.clear()
    
    # Show Main Menu loop - Esc from Editor/Builder returns here
    while True:
        menu = MainMenu(scr)
        choice = menu.run()
        
        if choice is None: 
            return  # User quit from MainMenu
        elif choice == "editor":
            show_editor_menu(scr)
            # After editor menu closes (Esc), loop back to MainMenu
        elif choice == "builder":
            # Run build flow, but return to MainMenu on Esc
            h_raw, w_raw = scr.getmaxyx()
            h, w = h_raw - 2, w_raw - 2
            
            # Load ignored files
            ignored_files = load_indexignore()
            
            # Check for discrepancies (sync wizard flow)
            scr.clear()
            TUI.safe_addstr(scr, h // 2, (w - 24) // 2, "Syncing content files...", curses.color_pair(1) | curses.A_BOLD)
            scr.refresh()
            
            missing_files, new_files = sync_hierarchy_with_content()
            new_files = [f for f in new_files if f not in ignored_files]
            
            if missing_files or new_files:
                wizard = SyncWizard(scr, missing_files, new_files)
                if not wizard.run():
                    continue  # Cancelled - return to MainMenu
                    
                # Re-sync after changes to ensure clean state
                missing_files, new_files = sync_hierarchy_with_content()
                new_files = [f for f in new_files if f not in ignored_files]
                if missing_files or new_files:
                     # Should not happen if sync succeeded
                     pass

                # Open hierarchy editor to review changes
                editor = HierarchyEditor(scr)
                editor.run()
                    
            # Build menu
            scr.clear()
            TUI.safe_addstr(scr, h // 2, (w - 11) // 2, "Indexing...", curses.color_pair(1) | curses.A_BOLD)
            scr.refresh()
            
            hierarchy = extract_hierarchy()
            build_menu = BuildMenu(scr, hierarchy)
            opts = build_menu.run()
            
            if opts is None: 
                continue  # Esc - return to MainMenu
            if not opts.get('selected_pages'):
                show_error_screen(scr, "No pages selected")
                continue  # Return to MainMenu
            
            try:
                run_build(scr, args, hierarchy, opts)
            except Exception as e:
                if str(e) == "Build cancelled": 
                    scr.timeout(-1)
                    scr.nodelay(False)
                    continue
                show_error_screen(scr, e)

def main():
    parser = argparse.ArgumentParser(description="Build Noteworthy documentation")
    args = parser.parse_args()
    
    # Initialize with NullHandler to suppress logs until configured
    logging.basicConfig(level=logging.CRITICAL)
    
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

