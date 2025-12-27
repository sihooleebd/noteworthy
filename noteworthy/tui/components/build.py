import curses
import logging
import shutil
import json
from pathlib import Path
from ..base import TUI
from ...config import LOGO, BUILD_DIR, OUTPUT_FILE, SAD_FACE, HAPPY_FACE, HMM_FACE
from ...utils import load_settings, save_settings, load_config_safe, check_dependencies
from .common import show_success_screen, copy_to_clipboard, show_error_screen
from ...core.build import compile_target, merge_pdfs, create_pdf_metadata, apply_pdf_metadata, zip_build_directory, get_pdf_page_count

class BuildMenu:

    def __init__(self, scr, hierarchy):
        self.scr, self.hierarchy = (scr, hierarchy)
        self.typst_flags, self.scroll, self.cursor = ([], 0, 0)
        settings = load_settings()
        self.debug = settings.get('debug', False)
        self.frontmatter = settings.get('frontmatter', True)
        self.leave_pdfs = settings.get('leave_pdfs', False)
        import os
        default_threads = max(1, (os.cpu_count() or 1) // 2)
        self.threads = settings.get('threads', default_threads)
        self.typst_flags = settings.get('typst_flags', [])
        saved_pages = set((tuple(p) for p in settings.get('selected_pages', [])))
        
        # Scan content/ folder to get sorted folder/file names
        from pathlib import Path
        content_dir = Path('content')
        self.ch_folders = []
        self.pg_folders = {}
        self.mismatch_error = None  # Error message if hierarchy doesn't match content/
        
        if content_dir.exists():
            ch_dirs = sorted([d for d in content_dir.iterdir() if d.is_dir() and d.name.isdigit()], key=lambda d: int(d.name))
            idx = 0
            for ch_dir in ch_dirs:
                pg_files = sorted([f.stem for f in ch_dir.glob('*.typ') if f.stem.isdigit()], key=lambda s: int(s))
                if pg_files:  # Only include folders with .typ files
                    self.ch_folders.append(ch_dir.name)
                    self.pg_folders[idx] = pg_files
                    idx += 1
        
        # Check for hierarchy/content mismatch
        if len(hierarchy) != len(self.ch_folders):
            self.mismatch_error = f"MISMATCH: hierarchy.json has {len(hierarchy)} chapters but content/ has {len(self.ch_folders)} folders ({', '.join(self.ch_folders)})"
        else:
            for ci, ch in enumerate(hierarchy):
                expected_pages = len(ch.get('pages', []))
                actual_pages = len(self.pg_folders.get(ci, []))
                if expected_pages != actual_pages:
                    ch_folder = self.ch_folders[ci] if ci < len(self.ch_folders) else str(ci)
                    self.mismatch_error = f"MISMATCH: Chapter {ch_folder} has {expected_pages} pages in hierarchy but {actual_pages} files in content/{ch_folder}/"
                    break
        
        self.items, self.selected = ([], {})
        for ci, ch in enumerate(hierarchy):
            self.items.append(('ch', ci, None))
            for ai in range(len(ch['pages'])):
                self.items.append(('art', ci, ai))
                self.selected[ci, ai] = (ci, ai) in saved_pages if saved_pages else True
        TUI.init_colors()
        self.h, self.w = scr.getmaxyx()

    def ch_selected(self, ci):
        return all((self.selected.get((ci, ai), False) for ai in range(len(self.hierarchy[ci]['pages']))))

    def ch_partial(self, ci):
        cnt = sum((1 for ai in range(len(self.hierarchy[ci]['pages'])) if self.selected.get((ci, ai))))
        return 0 < cnt < len(self.hierarchy[ci]['pages'])

    def toggle_ch(self, ci):
        v = not self.ch_selected(ci)
        [self.selected.update({(ci, ai): v}) for ai in range(len(self.hierarchy[ci]['pages']))]

    def refresh(self):
        self.h, self.w = TUI.get_dims(self.scr)
        self.scr.clear()
        lh, obh = (len(LOGO), 8) 
        vert_ch_rows = self.h - lh - 2 - obh - 1 - 5
        layout = 'vert'
        if vert_ch_rows < 7 and self.w >= 90:
            layout = 'horz' if self.h >= lh + 3 + obh else 'compact'

        def items(by, bx, bw, rows):
            vr = rows - 2
            if self.cursor < self.scroll:
                self.scroll = self.cursor
            elif self.cursor >= self.scroll + vr:
                self.scroll = self.cursor - vr + 1
            for r in range(vr):
                idx = self.scroll + r
                if idx >= len(self.items):
                    break
                t, ci, ai = self.items[idx]
                y, cur = (by + 1 + r, idx == self.cursor)
                if cur:
                    TUI.safe_addstr(self.scr, y, bx + 2, '▶', curses.color_pair(3) | curses.A_BOLD)
                if t == 'ch':
                    ch = self.hierarchy[ci]
                    cb = '[✓]' if self.ch_selected(ci) else '[~]' if self.ch_partial(ci) else '[ ]'
                    TUI.safe_addstr(self.scr, y, bx + 4, cb, curses.color_pair(2 if self.ch_selected(ci) else 3 if self.ch_partial(ci) else 4))
                    ch_folder = self.ch_folders[ci] if ci < len(self.ch_folders) else str(ci)
                    TUI.safe_addstr(self.scr, y, bx + 7, f" Ch {ch_folder}: {ch['title']}"[:bw - 12], curses.color_pair(1) | (curses.A_BOLD if cur else 0))
                else:
                    p = self.hierarchy[ci]['pages'][ai]
                    sel = self.selected.get((ci, ai), False)
                    TUI.safe_addstr(self.scr, y, bx + 6, '[✓]' if sel else '[ ]', curses.color_pair(2 if sel else 4))
                    pg_files = self.pg_folders.get(ci, [])
                    pg_folder = pg_files[ai] if ai < len(pg_files) else str(ai)
                    TUI.safe_addstr(self.scr, y, bx + 9, f" {pg_folder}: {p['title']}"[:bw - 14], curses.color_pair(4) | (curses.A_BOLD if cur else 0))

        def opts(sy, bx, bw):
            for i, (l, v, k) in enumerate([('Debug Mode:', self.debug, 'd'), ('Frontmatter:', self.frontmatter, 'f'), ('Leave PDFs:', self.leave_pdfs, 'l')]):
                TUI.safe_addstr(self.scr, sy + 1 + i, bx + 2, f'{l:14}', curses.color_pair(4))
                TUI.safe_addstr(self.scr, sy + 1 + i, bx + 16, '[ON] ' if v else '[OFF]', curses.color_pair(2 if v else 6) | curses.A_BOLD)
                TUI.safe_addstr(self.scr, sy + 1 + i, bx + 22, f'({k})', curses.color_pair(4) | curses.A_DIM)
            
            TUI.safe_addstr(self.scr, sy + 4, bx + 2, 'Threads:', curses.color_pair(4))
            TUI.safe_addstr(self.scr, sy + 4, bx + 16, f'{self.threads}', curses.color_pair(5) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, sy + 4, bx + 22, '(t)', curses.color_pair(4) | curses.A_DIM)

            flags = ' '.join(self.typst_flags) or '(none)'
            TUI.safe_addstr(self.scr, sy + 5, bx + 2, 'Typst Flags:', curses.color_pair(4))
            TUI.safe_addstr(self.scr, sy + 5, bx + 16, flags[:bw - 20], curses.color_pair(5 if self.typst_flags else 4) | curses.A_DIM)
            TUI.safe_addstr(self.scr, sy + 6, bx + 16, '(c)', curses.color_pair(4) | curses.A_DIM)

        if layout == 'compact':
            lw, rw = (20, min(50, self.w - 24))
            lx, rx = ((self.w - lw - rw - 2) // 2, (self.w - lw - rw - 2) // 2 + lw + 2)
            for i, l in enumerate(LOGO[:self.h - 1]):
                TUI.safe_addstr(self.scr, max(0, (self.h - lh) // 2 - 1) + i, lx + 3, l, curses.color_pair(1) | curses.A_BOLD)
            TUI.draw_box(self.scr, 0, rx, obh, rw, 'Options')
            opts(0, rx, rw)
            TUI.draw_box(self.scr, obh + 1, rx, max(3, self.h - obh - 3), rw, 'Select Chapters')
            items(obh + 1, rx, rw, max(3, self.h - obh - 3))
        elif layout == 'horz':
            start_y, lbw, rbw = (max(0, (self.h - (lh + 2 + obh) - 2) // 2), min(40, (self.w - 6) // 2), min(50, (self.w - 6) // 2))
            lx, rx = ((self.w - lbw - rbw - 2) // 2, (self.w - lbw - rbw - 2) // 2 + lbw + 2)
            
            if self.h >= lh + 2 + obh:
                for i, l in enumerate(LOGO[:self.h - 2]):
                    TUI.safe_addstr(self.scr, start_y + i, lx + (lbw - 14) // 2, l, curses.color_pair(1) | curses.A_BOLD)
            
            TUI.draw_box(self.scr, start_y + lh + 2 if self.h >= lh + 2 + obh else start_y, lx, obh, lbw, 'Options')
            opts(start_y + lh + 2 if self.h >= lh + 2 + obh else start_y, lx, lbw)
            
            TUI.draw_box(self.scr, start_y, rx, min(lh + 2 + obh, self.h - 2), rbw, 'Select Chapters')
            items(start_y, rx, rbw, min(lh + 2 + obh, self.h - 2))
        else:
            obh = 8 
            hide_logo = self.h < 36
            real_lh = len(LOGO) if not hide_logo else 0
            
            total_content_h = (real_lh + 2 if not hide_logo else 0) + obh + 1 + 6 + 2
            start_y = max(0, (self.h - total_content_h) // 2)
            
            if not hide_logo:
                for i, l in enumerate(LOGO):
                    TUI.safe_addstr(self.scr, start_y + i, (self.w - 14) // 2, l, curses.color_pair(1) | curses.A_BOLD)
            
            bw, bx = (min(60, self.w - 4), (self.w - min(60, self.w - 4)) // 2)
            
            spacing = 2 if not hide_logo else 0
            opts_y = start_y + real_lh + spacing
            if opts_y < 0: opts_y = 0
            
            TUI.draw_box(self.scr, opts_y, bx, obh, bw, 'Options')
            opts(opts_y, bx, bw)
            
            cy = opts_y + obh + 1
            rem_h = self.h - cy - 2
            
            list_h = max(4, rem_h)
            
            TUI.draw_box(self.scr, cy, bx, list_h, bw, 'Select Chapters')
            items(cy, bx, bw, list_h)
            
        # Display mismatch error if present
        if self.mismatch_error:
            err_msg = self.mismatch_error[:self.w - 4]
            TUI.safe_addstr(self.scr, self.h - 3, (self.w - len(err_msg)) // 2, err_msg, curses.color_pair(6) | curses.A_BOLD)
            footer = 'ERROR: Fix hierarchy.json or content/ to proceed  Esc: Back'
        else:
            footer = 'Space: Toggle  a/n: All/None  Enter: Build  Esc: Back'
        TUI.safe_addstr(self.scr, self.h - 1, (self.w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()

    def run(self):
        from ..editors import show_editor_menu
        from ..menus import show_keybindings_menu
        from .common import show_error_screen
        
        # Show error screen immediately if there's a mismatch
        if self.mismatch_error:
            show_error_screen(self.scr, self.mismatch_error)
            return None
            
        self.refresh()
        while True:
            if not TUI.check_terminal_size(self.scr):
                return None
            k = self.scr.getch()
            if k == 27:
                return None
            elif k == ord('?'):
                show_keybindings_menu(self.scr)
            elif k in (ord('\n'), curses.KEY_ENTER, 10):
                if self.mismatch_error:
                    # Don't allow build when there's a mismatch
                    continue
                res = {'selected_pages': [(ci, ai) for ci in range(len(self.hierarchy)) for ai in range(len(self.hierarchy[ci]['pages'])) if self.selected.get((ci, ai))], 'debug': self.debug, 'frontmatter': self.frontmatter, 'leave_individual': self.leave_pdfs, 'typst_flags': self.typst_flags, 'threads': self.threads, 'ch_folders': self.ch_folders, 'pg_folders': self.pg_folders}
                save_settings({'debug': self.debug, 'frontmatter': self.frontmatter, 'leave_pdfs': self.leave_pdfs, 'typst_flags': self.typst_flags, 'selected_pages': res['selected_pages'], 'threads': self.threads})
                return res
            elif k in (curses.KEY_UP, ord('k')):
                self.cursor = max(0, self.cursor - 1)
            elif k in (curses.KEY_DOWN, ord('j')):
                self.cursor = min(len(self.items) - 1, self.cursor + 1)
            elif k == ord(' '):
                t, ci, ai = self.items[self.cursor]
                if t == 'ch':
                    self.toggle_ch(ci)
                else:
                    self.selected[ci, ai] = not self.selected.get((ci, ai), False)
            elif k == ord('a'):
                [self.selected.update({(ci, ai): True}) for ci in range(len(self.hierarchy)) for ai in range(len(self.hierarchy[ci]['pages']))]
            elif k == ord('n'):
                [self.selected.update({(ci, ai): False}) for ci in range(len(self.hierarchy)) for ai in range(len(self.hierarchy[ci]['pages']))]
            elif k == ord('d'):
                self.debug = not self.debug
            elif k == ord('f'):
                self.frontmatter = not self.frontmatter
            elif k == ord('l'):
                self.leave_pdfs = not self.leave_pdfs
            elif k == ord('t'):
                self.configure_threads()
            elif k == ord('c'):
                self.configure_flags()
            elif k == ord('e'):
                show_editor_menu(self.scr)
            self.refresh()
            
    def configure_threads(self):
        curses.echo()
        curses.curs_set(1)
        dh, dw = (8, 40)
        d = curses.newwin(dh, dw, (self.h - dh) // 2, (self.w - dw) // 2)
        d.box()
        d.addstr(0, 2, ' Set Thread Count ', curses.color_pair(1) | curses.A_BOLD)
        d.addstr(2, 2, f'Current: {self.threads}')
        import os
        d.addstr(3, 2, f'Recommended (50% CPU): {os.cpu_count() // 2}')
        d.addstr(5, 2, 'New count: ')
        d.refresh()
        try:
            s = d.getstr(5, 13, 10).decode('utf-8').strip()
            if s and s.isdigit():
                val = int(s)
                if val > 0:
                    self.threads = val
        except:
            pass
        curses.noecho()
        curses.curs_set(0)

    def configure_flags(self):
        curses.echo()
        curses.curs_set(1)
        dh, dw = (10, min(60, self.w - 4))
        d = curses.newwin(dh, dw, (self.h - dh) // 2, (self.w - dw) // 2)
        d.box()
        d.addstr(0, 2, ' Typst Flags ', curses.color_pair(1) | curses.A_BOLD)
        d.addstr(2, 2, 'Current: ' + (' '.join(self.typst_flags) or '(none)')[:dw - 12])
        d.addstr(4, 2, '1. --font-path /path  2. --ppi 144  3. Clear')
        d.addstr(6, 2, 'Enter flags or preset: ')
        d.refresh()
        s = d.getstr(6, 25, dw - 27).decode('utf-8').strip()
        if s == '1':
            d.addstr(7, 2, 'Font path: ')
            d.refresh()
            p = d.getstr(7, 13, dw - 15).decode('utf-8').strip()
            if p:
                self.typst_flags = ['--font-path', p]
        elif s == '2':
            self.typst_flags = ['--ppi', '144']
        elif s == '3':
            self.typst_flags = []
        elif s:
            self.typst_flags = s.split()
        curses.noecho()
        curses.curs_set(0)

class BuildUI:

    def __init__(self, scr, debug=False):
        self.scr, self.debug_mode = (scr, debug)
        self.logs, self.typst_logs, self.task, self.phase, self.progress, self.total = ([], [], '', '', 0, 0)
        self.view, self.scroll, self.has_warnings = ('normal', 0, False)
        TUI.init_colors()
        self.h, self.w = scr.getmaxyx()
        self.base_total = 0

    def log(self, msg, ok=False):
        self.logs.append((msg, ok))
        self.logs = self.logs[-20:]
        self.refresh()

    def debug(self, msg):
        if self.debug_mode:
            self.log(f'[DEBUG] {msg}')

    def log_typst(self, out):
        if out:
            self.typst_logs.extend([l for l in out.split('\n') if l.strip()])
            self.typst_logs = self.typst_logs[-200:] 
            if 'warning:' in out.lower():
                self.has_warnings = True

    def set_phase(self, p):
        self.phase = p
        self.refresh()

    def set_task(self, t):
        self.task = t
        self.refresh()

    def set_progress(self, p, t, visual_percent=None):
        self.progress, self.total = (p, t)
        if not self.base_total and t > 0:
            self.base_total = t
        self.visual_percent = visual_percent
        return self.refresh()

    def check_input(self):
        try:
            k = self.scr.getch()
            if k == -1:
                return True
            if k == 27:
                return False
            if k == ord('v'):
                self.view = 'typst' if self.view == 'normal' else 'normal'
                self.scroll = 0
            elif self.view == 'typst':
                if k in (curses.KEY_UP, ord('k')):
                    self.scroll = max(0, self.scroll - 1)
                elif k in (curses.KEY_DOWN, ord('j')):
                    self.scroll = min(max(0, len(self.typst_logs) - 1), self.scroll + 1)
        except:
            pass
        return True

    def refresh(self):
        if not self.check_input():
            return False
        self.h, self.w = TUI.get_dims(self.scr)
        self.scr.clear()
        lh = min(15, self.h - 12)
        total_h = lh + 8
        start_y = max(0, (self.h - total_h) // 2)
        title = 'NOTEWORTHY BUILD SYSTEM' + (' [DEBUG]' if self.debug_mode else '')
        TUI.safe_addstr(self.scr, start_y, (self.w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
        bw, bx = (min(60, self.w - 4), (self.w - min(60, self.w - 4)) // 2)
        TUI.draw_box(self.scr, start_y + 2, bx, 5, bw, 'Progress')
        if self.phase:
            TUI.safe_addstr(self.scr, start_y + 3, bx + 2, self.phase[:bw - 4], curses.color_pair(5))
        if self.task:
            TUI.safe_addstr(self.scr, start_y + 4, bx + 2, f'→ {self.task}'[:bw - 4], curses.color_pair(4))
        if getattr(self, 'visual_percent', None) is not None or self.total:
            if getattr(self, 'visual_percent', None) is not None:
                effective_pct = max(0, min(100, self.visual_percent))
            else:
                effective_prog = min(self.progress, self.total)
                effective_pct = 100 * effective_prog // self.total
                
            filled = int((bw - 12) * effective_pct / 100)
            TUI.safe_addstr(self.scr, start_y + 5, bx + 2, '█' * filled + '░' * (bw - 12 - filled), curses.color_pair(3))
            TUI.safe_addstr(self.scr, start_y + 5, bx + bw - 8, f'{effective_pct:3d}%', curses.color_pair(3) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, start_y + 5, bx + bw - 8, f'{effective_pct:3d}%', curses.color_pair(3) | curses.A_BOLD)
            
            if self.total > self.base_total > 0:
                retries = self.total - self.base_total
                count_str = f'({self.progress}/{self.base_total} + {retries})'
            else:
                count_str = f'({self.progress}/{self.total})'
                
            # Move from box border (y+2) to inside line (y+3) to avoid truncation issues
            TUI.safe_addstr(self.scr, start_y + 3, bx + bw - 2 - len(count_str), count_str, curses.color_pair(4) | curses.A_DIM)
            
        if self.view == 'typst':
            TUI.draw_box(self.scr, start_y + 8, bx, lh, bw, 'Typst Output (↑↓ scroll)')
            if self.typst_logs:
                for i, line in enumerate(self.typst_logs[self.scroll:self.scroll + lh - 2]):
                    c = 6 if 'error:' in line.lower() else 3 if 'warning:' in line.lower() else 4
                    TUI.safe_addstr(self.scr, start_y + 9 + i, bx + 2, line[:bw - 4], curses.color_pair(c))
            else:
                TUI.safe_addstr(self.scr, start_y + 9, bx + 2, '(no output yet)', curses.color_pair(4) | curses.A_DIM)
        else:
            TUI.draw_box(self.scr, start_y + 8, bx, lh, bw, 'Build Log')
            for i, (msg, ok) in enumerate(self.logs[-(lh - 2):]):
                TUI.safe_addstr(self.scr, start_y + 9 + i, bx + 2, ('✓ ' if ok else '  ') + msg[:bw - 6], curses.color_pair(2 if ok else 4))
        footer = 'Esc: Cancel  |  v: Toggle Typst Log'
        TUI.safe_addstr(self.scr, self.h - 1, (self.w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
        return True

def run_build_process(scr, hierarchy, opts):
    from ...core.build import BuildManager
    if opts['debug']:
        logging.basicConfig(filename='build_debug.log', level=logging.DEBUG, format='%(asctime)s - %(message)s')
        logging.info('Debug mode enabled')
    config = load_config_safe()
    ui = BuildUI(scr, opts['debug'])
    scr.keypad(True)
    scr.nodelay(False)
    scr.timeout(0)
    ui.log('Checking dependencies...')
    try:
        check_dependencies()
    except SystemExit:
        ui.log('Missing dependencies!', False)
        curses.napms(2000)
        return
    ui.log('Dependencies OK', True)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir()
    ui.log('Build directory prepared', True)
    
    pages = opts.get('selected_pages', [])
    by_ch = {}
    for ci, ai in pages:
        by_ch.setdefault(ci, []).append(ai)
    chapters = [(i, hierarchy[i]) for i in sorted(by_ch.keys())]
    ui.log(f'Building {len(pages)} pages from {len(chapters)} chapters', True)
    
    # Total includes: compile tasks + post-compile (toc regen, merge, metadata)
    compile_tasks = (3 if opts['frontmatter'] else 0) + sum((1 + len(by_ch[ci]) for ci, _ in chapters))
    post_compile_tasks = 3  # TOC regen, merge, metadata
    total = compile_tasks + post_compile_tasks
    ui.set_phase('Compiling')
    ui.set_progress(0, total)
    
    bm = BuildManager(BUILD_DIR)
    
    progress_counter = 0
    
    def on_progress():
        nonlocal progress_counter, total
        progress_counter += 1
        if progress_counter > total:
            total = progress_counter
        # Linear progress: each task is equal weight
        pct = int(100 * progress_counter / total)
        if not ui.set_progress(progress_counter, total, visual_percent=pct):
            return False
        ui.set_task(f"Completed {progress_counter} compilation tasks") 
        return True 
        
    def on_log(msg, ok=True):
        ui.log(msg, ok)
    
    flags = opts.get('typst_flags', [])
    pdfs = []
    current_page_count = 0
    
    try:
        pdfs = bm.build_parallel(chapters, config, opts, {'on_progress': on_progress, 'on_log': on_log})
        
        current_page_count = sum([get_pdf_page_count(p) for p in pdfs]) + 1
        
        page_map = bm.page_map
        
        if opts['frontmatter'] and config.get('display-outline', True):
            ui.set_task('Regenerating TOC')
            out = BUILD_DIR / '02_outline.pdf'
            
            # Build folder_flags to pass chapter/page folder data
            ch_folders = opts.get('ch_folders', [])
            pg_folders = opts.get('pg_folders', {})
            folder_flags = list(flags)
            folder_flags.extend(['--input', f'chapter-folders={json.dumps(ch_folders)}'])
            folder_flags.extend(['--input', f'page-folders={json.dumps(pg_folders)}'])
            
            compile_target(
                'outline', 
                out, 
                page_offset=page_map.get('outline', 0), 
                page_map=page_map, 
                extra_flags=folder_flags, 
                callback=ui.refresh, 
                log_callback=ui.log_typst
            )
            progress_counter += 1
            if progress_counter > total: total = progress_counter
            ui.set_progress(progress_counter, total, visual_percent=int(100 * progress_counter / total))
            ui.log('TOC regenerated', True)
        else:
            pass
            
        ui.log(f'Total pages: {current_page_count - 1}', True)
        
        ui.set_phase('Merging PDFs')
        ui.set_task('Merging...')
        
        method = merge_pdfs(pdfs, OUTPUT_FILE)
        progress_counter += 1
        if progress_counter > total: total = progress_counter
        ui.set_progress(progress_counter, total, visual_percent=int(100 * progress_counter / total))
        
        if not method or not OUTPUT_FILE.exists():
            ui.log('Merge failed!', False)
            ui.set_phase('Failed')
            scr.nodelay(False)
            show_error_screen(scr, 'Failed to merge PDFs. Individual files left in ' + str(BUILD_DIR))
            return
            
        ui.log(f'Merged with {method}', True)
        ui.set_phase('Adding Metadata')
        
        bm_file = BUILD_DIR / 'bookmarks.txt'
        bookmarks_list = create_pdf_metadata(chapters, page_map, bm_file)
        apply_pdf_metadata(OUTPUT_FILE, bm_file, 'Noteworthy Framework', 'Sihoo Lee, Lee Hojun', bookmarks_list)
        progress_counter += 1
        if progress_counter > total: total = progress_counter
        ui.set_progress(progress_counter, total, visual_percent=100)
        ui.log('PDF metadata applied', True)
        
        if opts['leave_individual']:
            zip_build_directory(BUILD_DIR)
            ui.log('Individual PDFs archived', True)
            
        if OUTPUT_FILE.exists() and BUILD_DIR.exists():
            shutil.rmtree(BUILD_DIR)
            ui.log('Build directory cleaned', True)
            
        ui.set_phase('BUILD COMPLETE!')
        ui.log(f'Created {OUTPUT_FILE} ({current_page_count - 1} pages)', True)
        
        scr.nodelay(False)
        scr.timeout(-1)
        curses.flushinp()
        show_success_screen(scr, current_page_count - 1, ui.has_warnings, ui.typst_logs)
        
    except Exception as e:
        scr.nodelay(False)
        scr.timeout(-1)
        show_error_screen(scr, e)