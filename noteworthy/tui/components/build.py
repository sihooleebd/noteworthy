import curses
import logging
import shutil
import json
from pathlib import Path
from ..base import TUI, LEFT_PAD, TOP_PAD
from ...config import BUILD_DIR, OUTPUT_FILE
from ...assets import LOGO, SAD_FACE, HAPPY_FACE, HMM_FACE
from ...utils import load_settings, save_settings, load_config_safe, check_dependencies, scan_content
from .common import show_success_screen, copy_to_clipboard, show_error_screen, LineEditor


class BuildMenu:
    """Build configuration with grid layout: chapters=columns, pages=rows."""

    def __init__(self, scr, hierarchy):
        self.scr = scr
        self.hierarchy = hierarchy
        self.typst_flags = []
        
        settings = load_settings()
        self.debug = settings.get('debug', False)
        self.frontmatter = settings.get('frontmatter', True)
        self.leave_pdfs = settings.get('leave_pdfs', False)
        import os
        default_threads = max(1, (os.cpu_count() or 1) // 2)
        self.threads = settings.get('threads', default_threads)
        self.typst_flags = settings.get('typst_flags', [])
        saved_pages = set((tuple(p) for p in settings.get('selected_pages', [])))
        
        # Scan content folder
        self.ch_folders, self.pg_folders = scan_content()
        self.mismatch_error = self._check_mismatch()
        
        # Build grid data
        self.num_chapters = len(hierarchy)
        self.max_pages = max((len(ch.get('pages', [])) for ch in hierarchy), default=0)
        
        # Selection grid: selected[ci][pi] = True/False
        self.selected = {}
        for ci, ch in enumerate(hierarchy):
            for pi in range(len(ch['pages'])):
                self.selected[(ci, pi)] = (ci, pi) in saved_pages if saved_pages else True
        
        # Grid cursor position
        self.cursor_col = 0  # Chapter
        self.cursor_row = 0  # Page
        self.scroll_col = 0
        self.scroll_row = 0
        
        TUI.init_colors()

    def _check_mismatch(self):
        """Check for hierarchy/content mismatch."""
        if len(self.hierarchy) != len(self.ch_folders):
            return f"Mismatch: hierarchy has {len(self.hierarchy)} chapters, content/ has {len(self.ch_folders)}"
        for ci, ch in enumerate(self.hierarchy):
            expected = len(ch.get('pages', []))
            actual = len(self.pg_folders.get(str(ci), []))
            if expected != actual:
                return f"Mismatch: Ch {ci} has {expected} pages in hierarchy, {actual} files"
        return None

    def _get_page_count(self, ci):
        return len(self.hierarchy[ci].get('pages', []))

    def _col_all_selected(self, ci):
        return all(self.selected.get((ci, pi), False) for pi in range(self._get_page_count(ci)))

    def _row_all_selected(self, pi):
        return all(self.selected.get((ci, pi), False) for ci in range(self.num_chapters) 
                   if pi < self._get_page_count(ci))

    def _toggle_col(self, ci):
        new_val = not self._col_all_selected(ci)
        for pi in range(self._get_page_count(ci)):
            self.selected[(ci, pi)] = new_val

    def _toggle_row(self, pi):
        new_val = not self._row_all_selected(pi)
        for ci in range(self.num_chapters):
            if pi < self._get_page_count(ci):
                self.selected[(ci, pi)] = new_val

    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        y = TOP_PAD
        
        # Full logo
        for i, line in enumerate(LOGO):
            if y + i >= h - 20:
                break
            TUI.safe_addstr(self.scr, y + i, LEFT_PAD, line, curses.color_pair(1) | curses.A_BOLD)
        y += len(LOGO) + 1
        
        # Title
        TUI.safe_addstr(self.scr, y, LEFT_PAD, 'Build Configuration', curses.color_pair(1) | curses.A_BOLD)
        y += 2
        
        # Options row
        opts = [
            (f"Debug: {'ON' if self.debug else 'OFF'}", 'd', self.debug),
            (f"Frontmatter: {'ON' if self.frontmatter else 'OFF'}", 'f', self.frontmatter),
            (f"Keep PDFs: {'ON' if self.leave_pdfs else 'OFF'}", 'p', self.leave_pdfs),
            (f"Threads: {self.threads}", 't', None),
        ]
        x = LEFT_PAD
        for label, key, val in opts:
            color = curses.color_pair(2 if val else 4)
            TUI.safe_addstr(self.scr, y, x, f"[{key}] {label}", color)
            x += len(label) + 6
        y += 2
        
        # Grid settings
        # INVERTED AXES: Rows=Chapters, Columns=Pages
        col_width = 4  # Narrow columns for pages
        header_col_width = 30  # Wide row header for chapter titles
        
        # Calculate visible columns (pages) and rows (chapters)
        # Note: cursor_col is now PAGE, cursor_row is now CHAPTER
        # So horizontal scroll = page scroll, vertical scroll = chapter scroll
        
        # Use num_chapters for rows, max_pages for columns
        visible_cols = min(self.max_pages, (w - LEFT_PAD - header_col_width) // col_width)
        visible_rows = min(self.num_chapters, h - y - 6)
        
        if visible_cols < 1: visible_cols = 1
        if visible_rows < 1: visible_rows = 1
        
        # Scroll adjustment (col=page, row=chapter)
        if self.cursor_col < self.scroll_col:
            self.scroll_col = self.cursor_col
        elif self.cursor_col >= self.scroll_col + visible_cols:
            self.scroll_col = self.cursor_col - visible_cols + 1
        
        if self.cursor_row < self.scroll_row:
            self.scroll_row = self.cursor_row
        elif self.cursor_row >= self.scroll_row + visible_rows:
            self.scroll_row = self.cursor_row - visible_rows + 1
        
        # Display Selected Page Title
        # cursor_row=Chapter, cursor_col=Page
        cur_ch_title = self.hierarchy[self.cursor_row].get('title', f'Ch{self.cursor_row}')
        
        if self.cursor_col < self._get_page_count(self.cursor_row):
            cur_pg_title = self.hierarchy[self.cursor_row]['pages'][self.cursor_col].get('title', f'P{self.cursor_col}')
            sel_info = f"Selecting: {cur_ch_title} > {cur_pg_title}"
        else:
            sel_info = f"Selecting: {cur_ch_title} > [Empty]"
            
        TUI.safe_addstr(self.scr, y, LEFT_PAD, sel_info, curses.color_pair(3) | curses.A_BOLD)
        y += 2

        # Content Selector Title
        TUI.safe_addstr(self.scr, y, LEFT_PAD, 'Content Selector', curses.color_pair(1) | curses.A_BOLD)
        y += 2

        # Column headers (Page numbers)
        TUI.safe_addstr(self.scr, y, LEFT_PAD, 'Chapter', curses.color_pair(4) | curses.A_DIM)
        for i in range(visible_cols):
            pi = self.scroll_col + i
            if pi >= self.max_pages: break
            
            x = LEFT_PAD + header_col_width + i * col_width
            is_cur_col = pi == self.cursor_col
            
            # Use color 3 for current column header
            style = curses.color_pair(3 if is_cur_col else 4) | (curses.A_BOLD if is_cur_col else 0)
            pg_label = f"P{pi}"
            TUI.safe_addstr(self.scr, y, x, pg_label.center(col_width - 1), style)
        y += 1
        
        # Grid rows (Chapters)
        for ri in range(visible_rows):
            ci = self.scroll_row + ri
            if ci >= self.num_chapters: break
            
            row_y = y + ri
            is_cur_row = ci == self.cursor_row
            
            # Row header (Chapter Title)
            # Use color 3 for current row header
            style = curses.color_pair(3 if is_cur_row else 4) | (curses.A_BOLD if is_cur_row else 0)
            
            ch_folder = self.ch_folders[ci] if ci < len(self.ch_folders) else str(ci)
            ch_name = self.hierarchy[ci].get('title', f'Ch{ci}')
            label = f"{ch_folder}. {ch_name}"[:header_col_width - 2]
            TUI.safe_addstr(self.scr, row_y, LEFT_PAD, label.ljust(header_col_width - 1), style)
            
            # Cells (Pages for this chapter)
            for i in range(visible_cols):
                pi = self.scroll_col + i
                if pi >= self.max_pages: break
                
                x = LEFT_PAD + header_col_width + i * col_width
                is_cursor = ci == self.cursor_row and pi == self.cursor_col
                is_cur_col = pi == self.cursor_col
                
                # Check if page exists in this chapter
                if pi < self._get_page_count(ci):
                    sel = self.selected.get((ci, pi), False)
                    
                    if is_cursor:
                        # 1. CURSOR: Yellow (Color 3) Reverse
                        # Distinct high-contrast look for the active cell
                        char = '✓' if sel else ' '
                        draw_char = f"[{char}]"
                        draw_color = curses.color_pair(3) | curses.A_REVERSE | curses.A_BOLD
                        
                    elif is_cur_row or is_cur_col:
                        # 2. CROSSHAIR: Cyan (Color 1)
                        # Highlights the full row/column in a second color
                        draw_char = " ✓ " if sel else " · "
                        draw_color = curses.color_pair(1) | curses.A_BOLD
                        
                    else:
                        # 3. REST: Standard
                        # Green (Color 2) for selected, Dim (Color 4) for empty
                        if sel:
                            draw_char = " ✓ "
                            draw_color = curses.color_pair(2)
                        else:
                            draw_char = " · "
                            draw_color = curses.color_pair(4) | curses.A_DIM
                        
                    TUI.safe_addstr(self.scr, row_y, x, draw_char, draw_color)
                else:
                    # Empty cell (no page)
                    TUI.safe_addstr(self.scr, row_y, x, ' - ', curses.color_pair(4) | curses.A_DIM)
        
        y += visible_rows + 1
        
        # Error or info
        if self.mismatch_error:
            TUI.safe_addstr(self.scr, y, LEFT_PAD, self.mismatch_error[:w - LEFT_PAD - 2], 
                           curses.color_pair(6) | curses.A_BOLD)
            y += 1
        
        # Count selected
        total = sum(1 for (ci, pi), v in self.selected.items() if v)
        TUI.safe_addstr(self.scr, y, LEFT_PAD, f'{total} pages selected', curses.color_pair(4))
        
        # Footer
        footer = 'Arrows:Move  Space:Toggle  r:Row  c:Col  a:All  n:None  Enter:Build'
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, footer, curses.color_pair(4) | curses.A_DIM)
        
        self.scr.refresh()

    def run(self):
        if self.mismatch_error:
            show_error_screen(self.scr, self.mismatch_error)
            return None
        
        self.refresh()
        while True:
            if not TUI.check_terminal_size(self.scr):
                return None
            
            k = self.scr.getch()
            
            if k == 27:  # Esc
                return None
            elif k in (ord('\n'), curses.KEY_ENTER, 10):
                res = {
                    'selected_pages': [(ci, pi) for (ci, pi), v in self.selected.items() if v],
                    'debug': self.debug,
                    'frontmatter': self.frontmatter,
                    'leave_individual': self.leave_pdfs,
                    'typst_flags': self.typst_flags,
                    'threads': self.threads,
                    'ch_folders': self.ch_folders,
                    'pg_folders': self.pg_folders
                }
                save_settings({
                    'debug': self.debug,
                    'frontmatter': self.frontmatter,
                    'leave_pdfs': self.leave_pdfs,
                    'typst_flags': self.typst_flags,
                    'selected_pages': res['selected_pages'],
                    'threads': self.threads
                })
                return res
            
            # Navigation
            # Navigation with skipping/cycling
            elif k in (curses.KEY_LEFT, ord('h')):
                # Move PREV (Z-pattern: Left -> Up to Prev Chapter End -> ...)
                if self.cursor_col > 0:
                     self.cursor_col -= 1
                else:
                     # Go to previous chapter, last page
                     self.cursor_row = (self.cursor_row - 1) % self.num_chapters
                     cnt = self._get_page_count(self.cursor_row)
                     self.cursor_col = max(0, cnt - 1)
                    
            elif k in (curses.KEY_RIGHT, ord('l')):
                # Move NEXT (Z-pattern: Right -> Down to Next Chapter Start -> ...)
                cnt = self._get_page_count(self.cursor_row)
                if self.cursor_col < cnt - 1:
                     self.cursor_col += 1
                else:
                     # Go to next chapter, first page
                     self.cursor_row = (self.cursor_row + 1) % self.num_chapters
                     self.cursor_col = 0

            elif k in (curses.KEY_UP, ord('k')):
                # Move up (prev chapter) - standard cycle
                self.cursor_row = (self.cursor_row - 1) % self.num_chapters
                # After moving row, check if current col is valid in new row
                # If invalid, find nearest valid column (left)
                while self.cursor_col >= self._get_page_count(self.cursor_row) and self.cursor_col > 0:
                     self.cursor_col -= 1
                     
            elif k in (curses.KEY_DOWN, ord('j')):
                # Move down (next chapter) - standard cycle
                self.cursor_row = (self.cursor_row + 1) % self.num_chapters
                # Adjust column if needed
                while self.cursor_col >= self._get_page_count(self.cursor_row) and self.cursor_col > 0:
                     self.cursor_col -= 1
            
            # Toggle current cell (row=chapter, col=page)
            elif k == ord(' '):
                ci, pi = self.cursor_row, self.cursor_col
                if pi < self._get_page_count(ci):
                    self.selected[(ci, pi)] = not self.selected.get((ci, pi), False)
            
            # Toggle entire column (Page) - corresponds to 'c' (Col)
            elif k == ord('c'):
                self._toggle_row(self.cursor_col) # Vertical column in UI = Page index
            
            # Toggle entire row (Chapter) - corresponds to 'r' (Row)
            elif k == ord('r'):
                self._toggle_col(self.cursor_row) # Horizontal row in UI = Chapter
            
            # Select all
            elif k == ord('a'):
                for ci in range(self.num_chapters):
                    for pi in range(self._get_page_count(ci)):
                        self.selected[(ci, pi)] = True
            
            # Select none
            elif k == ord('n'):
                for ci in range(self.num_chapters):
                    for pi in range(self._get_page_count(ci)):
                        self.selected[(ci, pi)] = False
            
            # Options
            elif k == ord('d'):
                self.debug = not self.debug
            elif k == ord('f'):
                self.frontmatter = not self.frontmatter
            elif k == ord('p'):
                self.leave_pdfs = not self.leave_pdfs
            elif k == ord('t'):
                self._configure_threads()
            
            self.refresh()

    def _configure_threads(self):
        import os
        val = LineEditor(self.scr, title=f'Thread Count', initial_value=str(self.threads)).run()
        if val and val.isdigit() and int(val) > 0:
            self.threads = int(val)


class BuildUI:
    """Build progress display with left-aligned design."""

    def __init__(self, scr, debug=False):
        self.scr = scr
        self.debug_mode = debug
        self.logs = []
        self.typst_logs = []
        self.task = ''
        self.phase = ''
        self.progress = 0
        self.total = 0
        self.view = 'normal'
        self.scroll = 0
        self.has_warnings = False
        self.base_total = 0
        self.visual_percent = None
        TUI.init_colors()

    def log(self, msg, ok=False):
        self.logs.append((msg, ok))
        self.logs = self.logs[-15:]
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
        self.progress = p
        self.total = t
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
                    self.scroll += 1
        except:
            pass
        return True

    def refresh(self):
        if not self.check_input():
            return False
        
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        y = TOP_PAD
        
        title = 'BUILDING' + (' [DEBUG]' if self.debug_mode else '')
        TUI.safe_addstr(self.scr, y, LEFT_PAD, title, curses.color_pair(1) | curses.A_BOLD)
        y += 2
        
        if self.phase:
            TUI.safe_addstr(self.scr, y, LEFT_PAD, self.phase, curses.color_pair(5) | curses.A_BOLD)
        y += 1
        if self.task:
            TUI.safe_addstr(self.scr, y, LEFT_PAD, f'→ {self.task}'[:w - LEFT_PAD - 2], curses.color_pair(4))
        y += 2
        
        if self.total > 0:
            if self.visual_percent is not None:
                pct = max(0, min(100, self.visual_percent))
            else:
                pct = int(100 * min(self.progress, self.total) / self.total)
            
            bar_w = min(50, w - LEFT_PAD - 10)
            filled = int(bar_w * pct / 100)
            bar = '█' * filled + '░' * (bar_w - filled)
            TUI.safe_addstr(self.scr, y, LEFT_PAD, bar, curses.color_pair(3))
            TUI.safe_addstr(self.scr, y, LEFT_PAD + bar_w + 1, f'{pct}%', curses.color_pair(3) | curses.A_BOLD)
        y += 2
        
        log_h = h - y - 3
        
        if self.view == 'typst':
            TUI.safe_addstr(self.scr, y, LEFT_PAD, 'Typst Output', curses.color_pair(4) | curses.A_DIM)
            y += 1
            for i, line in enumerate(self.typst_logs[self.scroll:self.scroll + log_h]):
                color = 6 if 'error:' in line.lower() else 3 if 'warning:' in line.lower() else 4
                TUI.safe_addstr(self.scr, y + i, LEFT_PAD, line[:w - LEFT_PAD - 2], curses.color_pair(color))
        else:
            TUI.safe_addstr(self.scr, y, LEFT_PAD, 'Build Log', curses.color_pair(4) | curses.A_DIM)
            y += 1
            for i, (msg, ok) in enumerate(self.logs[-log_h:]):
                prefix = '✓ ' if ok else '  '
                TUI.safe_addstr(self.scr, y + i, LEFT_PAD, prefix + msg[:w - LEFT_PAD - 4], 
                               curses.color_pair(2 if ok else 4))
        
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, 'Esc Cancel  v Toggle Log', curses.color_pair(4) | curses.A_DIM)
        
        self.scr.refresh()
        return True


def run_build_process(scr, hierarchy, opts):
    """Execute build process with progress UI."""
    from ...core.build import BuildManager, get_pdf_page_count, compile_target, merge_pdfs, create_pdf_metadata, apply_pdf_metadata, zip_build_directory
    
    if opts['debug']:
        logging.basicConfig(filename='build_debug.log', level=logging.DEBUG, format='%(asctime)s - %(message)s')
    
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
    
    compile_tasks = (3 if opts['frontmatter'] else 0) + sum(1 + len(by_ch[ci]) for ci, _ in chapters)
    total = compile_tasks + 3
    ui.set_phase('Compiling')
    ui.set_progress(0, total)
    
    bm = BuildManager(BUILD_DIR)
    progress_counter = 0
    
    def on_progress():
        nonlocal progress_counter, total
        progress_counter += 1
        if progress_counter > total:
            total = progress_counter
        pct = int(100 * progress_counter / total)
        if not ui.set_progress(progress_counter, total, visual_percent=pct):
            return False
        ui.set_task(f"Completed {progress_counter} tasks")
        return True
    
    def on_log(msg, ok=True):
        ui.log(msg, ok)
    
    try:
        pdfs = bm.build_parallel(chapters, config, opts, {'on_progress': on_progress, 'on_log': on_log})
        current_page_count = sum(get_pdf_page_count(p) for p in pdfs) + 1
        page_map = bm.page_map
        
        if opts['frontmatter'] and config.get('display-outline', True):
            ui.set_task('Regenerating TOC')
            out = BUILD_DIR / '02_outline.pdf'
            flags = opts.get('typst_flags', [])
            ch_folders = opts.get('ch_folders', [])
            pg_folders = opts.get('pg_folders', {})
            folder_flags = list(flags)
            folder_flags.extend(['--input', f'chapter-folders={json.dumps(ch_folders)}'])
            folder_flags.extend(['--input', f'page-folders={json.dumps(pg_folders)}'])
            compile_target('outline', out, page_offset=page_map.get('outline', 0), 
                          page_map=page_map, extra_flags=folder_flags,
                          callback=ui.refresh, log_callback=ui.log_typst)
            progress_counter += 1
            ui.set_progress(progress_counter, total, visual_percent=int(100 * progress_counter / total))
            ui.log('TOC regenerated', True)
        
        ui.set_phase('Merging PDFs')
        method = merge_pdfs(pdfs, OUTPUT_FILE)
        progress_counter += 1
        ui.set_progress(progress_counter, total, visual_percent=int(100 * progress_counter / total))
        
        if not method or not OUTPUT_FILE.exists():
            ui.log('Merge failed!', False)
            scr.nodelay(False)
            show_error_screen(scr, 'Failed to merge PDFs')
            return
        
        ui.log(f'Merged with {method}', True)
        ui.set_phase('Adding Metadata')
        
        bm_file = BUILD_DIR / 'bookmarks.txt'
        bookmarks_list = create_pdf_metadata(chapters, page_map, bm_file)
        apply_pdf_metadata(OUTPUT_FILE, bm_file, 'Noteworthy', 'Noteworthy', bookmarks_list)
        progress_counter += 1
        ui.set_progress(progress_counter, total, visual_percent=100)
        ui.log('Metadata applied', True)
        
        if opts['leave_individual']:
            zip_build_directory(BUILD_DIR)
            ui.log('PDFs archived', True)
        
        if OUTPUT_FILE.exists() and BUILD_DIR.exists():
            shutil.rmtree(BUILD_DIR)
        
        ui.set_phase('COMPLETE')
        ui.log(f'Created {OUTPUT_FILE.name} ({current_page_count - 1} pages)', True)
        
        scr.nodelay(False)
        scr.timeout(-1)
        curses.flushinp()
        show_success_screen(scr, current_page_count - 1, ui.has_warnings, ui.typst_logs)
        
    except Exception as e:
        scr.nodelay(False)
        scr.timeout(-1)
        show_error_screen(scr, e)
