#!/usr/bin/env python3

import os, sys, json, subprocess, shutil, argparse, zipfile, curses, time
from pathlib import Path

# CONSTANTS

BUILD_DIR = Path("build")
OUTPUT_FILE = Path("output.pdf")
RENDERER_FILE = "templates/parser.typ"
MIN_TERM_HEIGHT, MIN_TERM_WIDTH = 20, 50

LOGO = [
    "         ,--. ", "       ,--.'| ", "   ,--,:  : | ", ",`--.'`|  ' : ",
    "|   :  :  | | ", ":   |   \\ | : ", "|   : '  '; | ", "'   ' ;.    ; ",
    "|   | | \\   | ", "'   : |  ; .' ", "|   | '`--'   ", "'   : |       ",
    ";   |.'       ", "'---'         ",
]

CONFETTI = [
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀", "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡈⠀⡠⠀⠀⣤⡄⠀⠀",
    "⠀⠀⠀⠀⠒⢀⣴⠟⠛⠓⠀⠀⠓⠀⠀⠀⢠⠉⠡⠀⠀", "⠀⠀⠀⣴⡆⠘⠧⠶⠶⢦⠀⠀⠰⠇⠀⠀⣀⠀⠀⣀⠀",
    "⠀⠀⠀⠀⠀⡠⠤⢀⣀⣼⠀⠀⣀⣀⡀⣦⠉⠳⠆⠋⠀", "⠀⠀⠀⢀⠄⡁⠀⣠⠿⠃⢤⡀⢽⠈⠉⠁⣀⣀⠀⠀⠀",
    "⠀⠀⠀⣾⠜⢐⠀⠁⠀⠀⠙⠻⣎⠀⠀⠀⠙⠉⠀⡀⢄", "⠀⠀⠜⠋⣎⠀⠀⠠⠀⢀⣠⣤⣼⣦⣤⣤⣀⠀⠀⠐⠈",
    "⠀⣌⠎⠘⢿⣦⡀⠀⠈⠙⠥⢀⣀⠄⠀⠈⠉⠃⠀⣴⡀", "⢠⢿⣦⡀⠈⠻⣿⣦⣔⢀⠠⠂⠀⠀⠠⣾⠗⠀⠀⠈⠀",
    "⣏⠀⠙⣿⣦⡂⠄⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀", "⠈⠓⠂⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
]

SAD_FACE = ["       __", "  _   / /", " (_) | | ", "     | | ", "  _  | | ", " (_) | | ", "      \\_\\"]

# UTILITY FUNCTIONS

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

def compile_target(target, output, page_offset=None, page_map=None, extra_flags=None, callback=None):
    cmd = ["typst", "compile", RENDERER_FILE, str(output), "--root", ".", "--input", f"target={target}"]
    if page_offset: cmd.extend(["--input", f"page-offset={page_offset}"])
    if page_map: cmd.extend(["--input", f"page-map={json.dumps(page_map)}"])
    if extra_flags: cmd.extend(extra_flags)
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    while proc.poll() is None:
        if callback: callback()
        time.sleep(0.05)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=stdout, stderr=stderr)
    return stderr or ""

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

# CURSES HELPERS

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    for i, color in enumerate([curses.COLOR_CYAN, curses.COLOR_GREEN, curses.COLOR_YELLOW, 
                               curses.COLOR_WHITE, curses.COLOR_MAGENTA, curses.COLOR_RED], 1):
        curses.init_pair(i, color, -1)
    curses.curs_set(0)

def safe_addstr(scr, y, x, text, attr=0):
    try:
        h, w = scr.getmaxyx()
        if 0 <= y < h and 0 <= x < w:
            scr.addstr(y, x, text[:w - x - 1], attr)
    except curses.error:
        pass

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

# SCREEN DISPLAYS

def show_error_screen(scr, error):
    import traceback
    log = traceback.format_exc()
    if log.strip() == "NoneType: None":
        log = str(error)
    
    view_log = False
    while True:
        scr.clear()
        h, w = scr.getmaxyx()
        
        if view_log:
            safe_addstr(scr, 0, 2, "ERROR LOG (press 'v' to go back)", curses.color_pair(6) | curses.A_BOLD)
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
        elif not view_log:
            break

def show_success_screen(scr, page_count):
    scr.clear()
    h, w = scr.getmaxyx()
    y = max(0, (h - len(CONFETTI) - 8) // 2)
    
    for i, line in enumerate(CONFETTI):
        safe_addstr(scr, y + i, (w - 17) // 2, line, curses.color_pair(2))
    
    my = y + len(CONFETTI) + 2
    safe_addstr(scr, my, (w - 16) // 2, "BUILD SUCCEEDED!", curses.color_pair(2) | curses.A_BOLD)
    msg = f"Created: {OUTPUT_FILE} ({page_count} pages)"
    safe_addstr(scr, my + 2, (w - len(msg)) // 2, msg, curses.color_pair(4))
    safe_addstr(scr, my + 4, (w - 24) // 2, "Press any key to exit...", curses.color_pair(4) | curses.A_DIM)
    scr.refresh()
    scr.getch()

# BUILD MENU (Selection TUI)

class BuildMenu:
    def __init__(self, scr, hierarchy):
        self.scr, self.hierarchy = scr, hierarchy
        self.debug, self.frontmatter, self.leave_pdfs = False, True, False
        self.typst_flags, self.scroll, self.cursor = [], 0, 0
        
        self.items, self.selected = [], {}
        for ci, ch in enumerate(hierarchy):
            self.items.append(('ch', ci, None))
            for ai in range(len(ch["pages"])):
                self.items.append(('art', ci, ai))
                self.selected[(ci, ai)] = True
        
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
                    safe_addstr(self.scr, y, bx + 7, f" Ch {ch['pages'][0]['id'][:2]}: {ch['title']}"[:bw-12], curses.color_pair(1))
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
            lbw, rbw = min(40, (self.w - 6) // 2), min(50, (self.w - 6) // 2)
            lx = (self.w - lbw - rbw - 2) // 2
            rx = lx + lbw + 2
            lgx = lx + (lbw - 14) // 2
            for i, line in enumerate(LOGO[:self.h-2]):
                safe_addstr(self.scr, i, lgx, line, curses.color_pair(1) | curses.A_BOLD)
            safe_addstr(self.scr, lh, lx + (lbw - 10) // 2, "NOTEWORTHY", curses.color_pair(1) | curses.A_BOLD)
            draw_box(self.scr, lh + 2, lx, obh, lbw, "Options")
            opts(lh + 2, lx, lbw)
            ch = min(lh + 2 + obh, self.h - 2)
            draw_box(self.scr, 0, rx, ch, rbw, "Select Chapters")
            items(0, rx, rbw, ch)
        else:
            lgx = (self.w - 14) // 2
            for i, line in enumerate(LOGO):
                safe_addstr(self.scr, i, lgx, line, curses.color_pair(1) | curses.A_BOLD)
            safe_addstr(self.scr, lh + 1, (self.w - 10) // 2, "NOTEWORTHY", curses.color_pair(1) | curses.A_BOLD)
            bw, bx = min(60, self.w - 4), (self.w - min(60, self.w - 4)) // 2
            draw_box(self.scr, lh + 3, bx, obh, bw, "Options")
            opts(lh + 3, bx, bw)
            cy = lh + 3 + obh + 1
            ch = min(len(self.items) + 2, self.h - cy - 3)
            draw_box(self.scr, cy, bx, ch, bw, "Select Chapters")
            items(cy, bx, bw, ch)
        
        safe_addstr(self.scr, self.h - 1, (self.w - 58) // 2, "↑↓:Nav  Space:Toggle  a:All  n:None  Enter:Build  q:Quit", curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
    
    def run(self):
        self.refresh()
        while True:
            if not check_terminal_size(self.scr): return None
            
            k = self.scr.getch()
            if k == ord('q'): return None
            elif k in (ord('\n'), curses.KEY_ENTER, 10):
                return {'selected_pages': [(ci, ai) for ci in range(len(self.hierarchy)) for ai in range(len(self.hierarchy[ci]["pages"])) if self.selected.get((ci, ai))],
                        'debug': self.debug, 'frontmatter': self.frontmatter, 'leave_individual': self.leave_pdfs, 'typst_flags': self.typst_flags}
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

# BUILD UI (Progress Display)

class BuildUI:
    def __init__(self, scr, debug=False):
        self.scr, self.debug_mode = scr, debug
        self.logs, self.typst_logs = [], []
        self.task, self.phase, self.progress, self.total = "", "", 0, 0
        self.view, self.scroll = "normal", 0
        init_colors()
        self.h, self.w = scr.getmaxyx()
    
    def log(self, msg, ok=False): self.logs.append((msg, ok)); self.logs = self.logs[-20:]; self.refresh()
    def debug(self, msg):
        if self.debug_mode: self.log(f"[DEBUG] {msg}")
    def log_typst(self, out):
        if out: self.typst_logs.extend([l for l in out.split('\n') if l.strip()]); self.typst_logs = self.typst_logs[-100:]
    def set_phase(self, p): self.phase = p; self.refresh()
    def set_task(self, t): self.task = t; self.refresh()
    def set_progress(self, p, t): self.progress, self.total = p, t; self.refresh()
    
    def refresh(self):
        try:
            k = self.scr.getch()
            if k == ord('v'): self.view = "typst" if self.view == "normal" else "normal"; self.scroll = 0
            elif self.view == "typst" and k in (curses.KEY_UP, ord('k')): self.scroll = max(0, self.scroll - 1)
            elif self.view == "typst" and k in (curses.KEY_DOWN, ord('j')): self.scroll = min(len(self.typst_logs) - 1, self.scroll + 1)
        except: pass
        
        self.h, self.w = self.scr.getmaxyx()
        self.scr.clear()
        
        title = "NOTEWORTHY BUILD SYSTEM" + (" [DEBUG]" if self.debug_mode else "")
        safe_addstr(self.scr, 1, (self.w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
        
        bw, bx = min(60, self.w - 4), (self.w - min(60, self.w - 4)) // 2
        draw_box(self.scr, 3, bx, 5, bw, "Progress")
        if self.phase: safe_addstr(self.scr, 4, bx + 2, self.phase[:bw-4], curses.color_pair(5))
        if self.task: safe_addstr(self.scr, 5, bx + 2, f"→ {self.task}"[:bw-4], curses.color_pair(4))
        if self.total:
            filled = int((bw - 12) * self.progress / self.total)
            safe_addstr(self.scr, 6, bx + 2, "█" * filled + "░" * (bw - 12 - filled), curses.color_pair(3))
            safe_addstr(self.scr, 6, bx + bw - 8, f"{100*self.progress//self.total:3d}%", curses.color_pair(3) | curses.A_BOLD)
        
        lh = min(15, self.h - 12)
        if self.view == "typst" and self.typst_logs:
            draw_box(self.scr, 9, bx, lh, bw, "Typst Output (↑↓ scroll)")
            for i, line in enumerate(self.typst_logs[self.scroll:self.scroll + lh - 2]):
                c = 6 if 'error:' in line.lower() else 3 if 'warning:' in line.lower() else 4
                safe_addstr(self.scr, 10 + i, bx + 2, line[:bw-4], curses.color_pair(c))
        else:
            draw_box(self.scr, 9, bx, lh, bw, "Build Log")
            for i, (msg, ok) in enumerate(self.logs[-(lh-2):]):
                safe_addstr(self.scr, 10 + i, bx + 2, ("✓ " if ok else "  ") + msg[:bw-6], curses.color_pair(2 if ok else 4))
        
        safe_addstr(self.scr, self.h - 1, (self.w - 50) // 2, "Press Ctrl+C to cancel  |  Press 'v' to toggle view", curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()

# BUILD LOGIC

def run_build(scr, args, hierarchy, opts):
    ui = BuildUI(scr, opts['debug'])
    scr.nodelay(True)
    
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
            ui.log_typst(compile_target(target, out, extra_flags=flags, callback=ui.refresh))
            pdfs.append(out); page_map[target] = current; current += get_pdf_page_count(out)
            prog += 1; ui.set_progress(prog, total + 1)
            ui.log(f"{label} compiled", True)
    
    for ci, ch in chapters:
        ch_id = ch["pages"][0]["id"][:2]
        ui.set_task(f"Chapter {ch_id}: {ch['title']}")
        out = BUILD_DIR / f"10_chapter_{ch_id}_cover.pdf"
        page_map[f"chapter-{ch_id}"] = current
        ui.log_typst(compile_target(f"chapter-{ch_id}", out, page_offset=current, extra_flags=flags, callback=ui.refresh))
        pdfs.append(out); current += get_pdf_page_count(out)
        prog += 1; ui.set_progress(prog, total + 1)
        
        for ai in sorted(by_ch[ci]):
            p = ch["pages"][ai]
            ui.set_task(f"Section {p['id']}: {p['title']}")
            out = BUILD_DIR / f"20_page_{p['id']}.pdf"
            page_map[p["id"]] = current
            ui.log_typst(compile_target(p["id"], out, page_offset=current, extra_flags=flags, callback=ui.refresh))
            pdfs.append(out); current += get_pdf_page_count(out)
            prog += 1; ui.set_progress(prog, total + 1)
        
        ui.log(f"Chapter {ch_id} compiled", True)
    
    if opts['frontmatter']:
        ui.set_task("Regenerating TOC")
        out = BUILD_DIR / "02_outline.pdf"
        ui.log_typst(compile_target("outline", out, page_offset=page_map["outline"], page_map=page_map, extra_flags=flags, callback=ui.refresh))
        ui.log("TOC regenerated", True)
    
    ui.log(f"Total pages: {current - 1}", True)
    
    ui.set_phase("Merging PDFs")
    method = merge_pdfs(pdfs, OUTPUT_FILE)
    if method: ui.log(f"Merged with {method}", True)
    
    ui.set_phase("Adding Metadata")
    bm = BUILD_DIR / "bookmarks.txt"
    create_pdf_metadata([ch for _, ch in chapters], page_map, bm)
    apply_pdf_metadata(OUTPUT_FILE, bm, "Noteworthy Framework", "Sihoo Lee, Lee Hojun")
    ui.log("PDF metadata applied", True)
    
    if opts['leave_individual']:
        zip_build_directory(BUILD_DIR)
        ui.log("Individual PDFs archived", True)
    
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        ui.log("Build directory cleaned", True)
    
    ui.set_phase("BUILD COMPLETE!")
    ui.set_progress(total + 1, total + 1)
    ui.log(f"Created {OUTPUT_FILE} ({current - 1} pages)", True)
    
    scr.nodelay(False)
    show_success_screen(scr, current - 1)

# ENTRY POINTS

def run_app(scr, args):
    init_colors()
    if not check_terminal_size(scr): return
    
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
