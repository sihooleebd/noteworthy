
import curses
import json
import logging
import shutil
import time
from pathlib import Path
from ..base import BaseEditor, TUI, LEFT_PAD, TOP_PAD
from ...config import BUILD_DIR, OUTPUT_FILE, HIERARCHY_FILE
from ...utils import load_settings, save_settings, load_config_safe, check_dependencies, scan_content
from ...core.build import BuildManager, get_pdf_page_count, compile_target, merge_pdfs, create_pdf_metadata, apply_pdf_metadata, zip_build_directory
from ..components.common import show_success_screen, copy_to_clipboard, show_error_screen, LineEditor
from ..keybinds import NavigationBind, KeyBind
from ...assets import LOGO, HAPPY_FACE, HMM_FACE

class BuildWizard(BaseEditor):
    """
    Unified Build Wizard with sidebar steps: Configuration -> Building -> Result.
    Sidebar is purely informational (static).
    """
    def __init__(self, scr, hierarchy):
        super().__init__(scr, "Builder")
        self.scr = scr
        self.hierarchy = hierarchy
        self.sidebar_width = 25
        self.active_pane = 'content' # Always content
        self.steps = ["Configuration", "Building", "Result"]
        self.current_step_idx = 0
        
        # --- State ---
        self.config_editor = None # Initialized in first draw or dedicated init
        self.progress_ui = None
        self.result_ui = None
        self.build_opts = {}
        self.build_result = None # {page_count, has_warnings, logs}
        
        # Load settings
        settings = load_settings()
        self.debug = settings.get('debug', False)
        self.frontmatter = settings.get('frontmatter', True)
        self.leave_pdfs = settings.get('leave_pdfs', False)
        import os
        default_threads = max(1, (os.cpu_count() or 1) // 2)
        self.threads = settings.get('threads', default_threads)
        self.typst_flags = settings.get('typst_flags', [])
        saved_pages = set((tuple(p) for p in settings.get('selected_pages', [])))
        
        # Scan content
        self.ch_folders, self.pg_folders = scan_content()
        self.check_mismatch()
        
        # Selection Grid State
        self.num_chapters = len(hierarchy)
        self.max_pages = max((len(ch.get('pages', [])) for ch in hierarchy), default=0)
        self.selected = {}
        for ci, ch in enumerate(hierarchy):
            for pi in range(len(ch['pages'])):
                self.selected[(ci, pi)] = (ci, pi) in saved_pages if saved_pages else True
        
        # If nothing is selected at all (and we had saved pages that might be stale), revert to Select All
        if not any(self.selected.values()):
            for k in self.selected:
                self.selected[k] = True
        
        self.cursor_col = 0
        self.cursor_row = 0
        self.scroll_col = 0
        self.scroll_row = 0

        # Building State
        self.build_started = False
        self.build_done = False
        self.logs = []
        self.typst_logs = []
        self.task = ''
        self.phase = ''
        self.progress = 0
        self.total = 0
        self.build_view_mode = 'normal'
        self.build_scroll = 0
        self.has_warnings = False
        self.visual_percent = None

        # Keybinds
        register_key = lambda k, f: self.keymap.update({k: f})
        # Standard Navigation
        self.keymap[curses.KEY_UP] = self.nav_up
        self.keymap[curses.KEY_DOWN] = self.nav_down
        self.keymap[curses.KEY_RIGHT] = self.nav_right
        self.keymap[curses.KEY_LEFT] = self.nav_left
        self.keymap[27] = self.on_escape # ESC
        self.keymap[ord('\n')] = self.on_enter
        self.keymap[curses.KEY_ENTER] = self.on_enter

    def check_mismatch(self):
        self.mismatch_error = None
        if len(self.hierarchy) != len(self.ch_folders):
            self.mismatch_error = f"Mismatch: hierarchy has {len(self.hierarchy)} chapters, content/ has {len(self.ch_folders)}"
            return
        for ci, ch in enumerate(self.hierarchy):
            expected = len(ch.get('pages', []))
            actual = len(self.pg_folders.get(str(ci), []))
            if expected != actual:
                self.mismatch_error = f"Mismatch: Ch {ci} has {expected} pages in hierarchy, {actual} files"
                return

    def nav_up(self):
        if self.current_step_idx == 0:
             self.grid_nav_up()
        elif self.current_step_idx == 1 and self.build_view_mode == 'typst':
             self.build_scroll = max(0, self.build_scroll - 1)

    def nav_down(self):
        if self.current_step_idx == 0:
             self.grid_nav_down()
        elif self.current_step_idx == 1 and self.build_view_mode == 'typst':
             self.build_scroll += 1

    def nav_left(self):
         if self.current_step_idx == 0:
             # Regular gridnav, but if we exceed left, we return EXIT
             # Actually, since sidebar is disallowed, maybe return EXIT?
             # Let's keep grid traversing but if user wants to exit, ESC is preferred.
             # But user explicitly said "Left arrow in specific menu still not working".
             if self.cursor_col > 0:
                 self.cursor_col -= 1
             else:
                 return True, 'EXIT'
         else:
             # In other steps, LEFT might not do much, usually ESC is exit
             return True, 'EXIT'

    def nav_right(self):
        if self.current_step_idx == 0:
             self.grid_nav_right()

    def on_escape(self):
         return True, 'EXIT'

    def on_enter(self):
        if self.current_step_idx == 0: # Configuration
             # Start Build
             self.start_build()

    def handle_input(self, k):
        # Direct routing based on step
        handled = False
        if self.current_step_idx == 0:
            handled = self.handle_config_input(k)
        elif self.current_step_idx == 1:
            handled = self.handle_build_input(k)
        elif self.current_step_idx == 2:
            if k in (ord('\n'), curses.KEY_ENTER):
                 return True, 'EXIT'
        
        if handled:
            return True, None
            
        # Fallback to keymap
        if k in self.keymap:
            res = self.keymap[k]()
            if res: # e.g. (True, 'EXIT')
                return res
            return True, None
        return False, None

    # --- Configuration Step (Grid) Logic ---
    
    def grid_nav_up(self):
        self.cursor_row = (self.cursor_row - 1) % self.num_chapters
        while self.cursor_col >= len(self.hierarchy[self.cursor_row]['pages']) and self.cursor_col > 0:
             self.cursor_col -= 1

    def grid_nav_down(self):
        self.cursor_row = (self.cursor_row + 1) % self.num_chapters
        while self.cursor_col >= len(self.hierarchy[self.cursor_row]['pages']) and self.cursor_col > 0:
             self.cursor_col -= 1
    
    def grid_nav_left(self):
        if self.cursor_col > 0:
             self.cursor_col -= 1
        elif self.cursor_row > 0:
             self.cursor_row -= 1
             # Move to last page of previous chapter
             cnt_prev = len(self.hierarchy[self.cursor_row]['pages'])
             self.cursor_col = max(0, cnt_prev - 1)

    def grid_nav_right(self):
        cnt = len(self.hierarchy[self.cursor_row]['pages'])
        if self.cursor_col < cnt - 1:
             self.cursor_col += 1
        elif self.cursor_row < self.num_chapters - 1:
             self.cursor_row += 1
             self.cursor_col = 0
             
    def handle_config_input(self, k):
        if k == ord(' '):
            ci, pi = self.cursor_row, self.cursor_col
            if pi < len(self.hierarchy[ci]['pages']):
                self.selected[(ci, pi)] = not self.selected.get((ci, pi), False)
            return True
        elif k == ord('c'): # Col
            pi = self.cursor_col
            val = not all(self.selected.get((ci, pi), False) for ci in range(self.num_chapters) if pi < len(self.hierarchy[ci]['pages']))
            for ci in range(self.num_chapters):
                 if pi < len(self.hierarchy[ci]['pages']): self.selected[(ci, pi)] = val
            return True
        elif k == ord('r'): # Row
            ci = self.cursor_row
            val = not all(self.selected.get((ci, pi), False) for pi in range(len(self.hierarchy[ci]['pages'])))
            for pi in range(len(self.hierarchy[ci]['pages'])):
                 self.selected[(ci, pi)] = val
            return True
        elif k == ord('a'): # Toggle All
            # If all currently valid pages are selected, deselect all. Otherwise select all.
            all_selected = True
            for ci in range(self.num_chapters):
                for pi in range(len(self.hierarchy[ci]['pages'])):
                    if not self.selected.get((ci, pi), False):
                        all_selected = False
                        break
                if not all_selected: break
            
            new_val = not all_selected
            for ci in range(self.num_chapters):
                for pi in range(len(self.hierarchy[ci]['pages'])):
                    self.selected[(ci, pi)] = new_val
            return True
        elif k == ord('n'): # Deprecated/Merged into 'a', duplicate behavior or ignore
            return True
        elif k == ord('d'): self.debug = not self.debug; return True
        elif k == ord('f'): self.frontmatter = not self.frontmatter; return True
        elif k == ord('p'): self.leave_pdfs = not self.leave_pdfs; return True
        return False
    
    # ... (skipping build logic) ...

    # --- Draw --- (Updated in previous step, need to update footer text in _draw_content)


    # --- Build Logic ---

    def start_build(self):
        selected_pages = [(ci, pi) for (ci, pi), v in self.selected.items() if v]
        self.log(f"Starting build with {len(selected_pages)} pages selected", True)
        if not selected_pages and not self.frontmatter:
            self.log("No pages selected and no frontmatter - aborting", False)
            return # Nothing to do

        save_settings({
            'debug': self.debug,
            'frontmatter': self.frontmatter,
            'leave_pdfs': self.leave_pdfs,
            'typst_flags': self.typst_flags,
            'selected_pages': selected_pages,
            'threads': self.threads
        })
        
        self.build_opts = {
            'selected_pages': selected_pages,
            'debug': self.debug,
            'frontmatter': self.frontmatter,
            'leave_individual': self.leave_pdfs,
            'typst_flags': self.typst_flags,
            'threads': self.threads,
            'ch_folders': self.ch_folders,
            'pg_folders': self.pg_folders
        }
        
        self.current_step_idx = 1 # Move to Building
        self.build_started = True
        self.run_build_process()

    def handle_build_input(self, k):
        if k == ord('v'):
             self.build_view_mode = 'typst' if self.build_view_mode == 'normal' else 'normal'
             self.build_scroll = 0
             return True
        return False
        
    def log(self, msg, ok=False):
        self.logs.append((msg, ok))
        self.logs = self.logs[-15:]
        self.refresh() # Trigger redraw
        
    def log_typst(self, out):
        if out:
            self.typst_logs.extend([l for l in out.split('\n') if l.strip()])
            self.typst_logs = self.typst_logs[-200:]
            if 'warning:' in out.lower():
                self.has_warnings = True

    def set_progress(self, p, t, visual_percent=None):
        self.progress = p
        self.total = t
        self.visual_percent = visual_percent
        self.refresh()
        return True # Continue building

    def run_build_process(self):
        # Adapted from components/build.py
        if self.build_opts['debug']:
            logging.basicConfig(filename='build_debug.log', level=logging.DEBUG, format='%(asctime)s - %(message)s')
        
        config = load_config_safe()
        self.scr.nodelay(True) # Non-blocking for UI updates during build if possible
        # Actually, since BuildManager is running synchronously (or managing processes), 
        # we need to be careful. The original code used callbacks.
        
        self.log('Checking dependencies...')
        try:
             check_dependencies()
        except SystemExit:
             self.log('Missing dependencies!', False)
             return

        if BUILD_DIR.exists(): shutil.rmtree(BUILD_DIR)
        BUILD_DIR.mkdir()
        self.log('Build directory prepared', True)
        
        pages = self.build_opts.get('selected_pages', [])
        by_ch = {}
        for ci, ai in pages:
             by_ch.setdefault(ci, []).append(ai)
        chapters = [(i, self.hierarchy[i]) for i in sorted(by_ch.keys())]
        
        compile_tasks = (3 if self.build_opts['frontmatter'] else 0) + sum(1 + len(by_ch[ci]) for ci, _ in chapters)
        total = compile_tasks + 3
        self.phase = 'Compiling'
        self.set_progress(0, total)
        
        bm = BuildManager(BUILD_DIR)
        progress_counter = 0
        
        # Callbacks
        def on_progress():
             nonlocal progress_counter, total
             progress_counter += 1
             if progress_counter > total: total = progress_counter
             pct = int(100 * progress_counter / total)
             self.set_progress(progress_counter, total, visual_percent=pct)
             # Handle input to keep UI alive/cancellable
             try:
                 k = self.scr.getch()
                 if k == 27: return False # Cancel
                 self.handle_input(k)
             except: pass
             return True

        def on_log(msg, ok=True):
             self.log(msg, ok)

        try:
             pdfs = bm.build_parallel(chapters, config, self.build_opts, {'on_progress': on_progress, 'on_log': on_log})
             current_page_count = sum(get_pdf_page_count(p) for p in pdfs) + 1
             page_map = bm.page_map
             
             if self.build_opts['frontmatter'] and config.get('display-outline', True):
                 self.task = 'Regenerating TOC'
                 out = BUILD_DIR / '02_outline.pdf'
                 flags = self.build_opts.get('typst_flags', [])
                 folder_flags = list(flags)
                 folder_flags.extend(['--input', f'chapter-folders={json.dumps(self.build_opts["ch_folders"])}'])
                 folder_flags.extend(['--input', f'page-folders={json.dumps(self.build_opts["pg_folders"])}'])
                 compile_target('outline', out, page_offset=page_map.get('outline', 0),
                               page_map=page_map, extra_flags=folder_flags,
                               callback=self.refresh, log_callback=self.log_typst)
                 progress_counter += 1
                 self.set_progress(progress_counter, total, 100 * progress_counter // total)
             
             self.phase = 'Merging PDFs'
             method = merge_pdfs(pdfs, OUTPUT_FILE)
             progress_counter += 1
             self.set_progress(progress_counter, total, 100 * progress_counter // total)
             
             if not method or not OUTPUT_FILE.exists():
                 self.log('Merge failed!', False)
                 return

             self.phase = 'Adding Metadata'
             bm_file = BUILD_DIR / 'bookmarks.txt'
             bookmarks_list = create_pdf_metadata(chapters, page_map, bm_file)
             apply_pdf_metadata(OUTPUT_FILE, bm_file, 'Noteworthy', 'Noteworthy', bookmarks_list)
             progress_counter += 1
             self.set_progress(progress_counter, total, 100)
             
             if self.build_opts['leave_individual']:
                 zip_build_directory(BUILD_DIR)
                 self.log('PDFs archived', True)
                 
             if OUTPUT_FILE.exists() and BUILD_DIR.exists():
                 shutil.rmtree(BUILD_DIR)

             self.phase = 'COMPLETE'
             self.build_result = {'page_count': current_page_count - 1, 'has_warnings': self.has_warnings, 'typst_logs': self.typst_logs}
             self.scr.nodelay(False) # Stop non-blocking mode to prevent flickering
             self.current_step_idx = 2 # Result
             
        except Exception as e:
             self.log(f"Error: {str(e)}", False)

    # --- Draw ---

    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        # Increase top pad slightly (User Request)
        header_pad = TOP_PAD + 1

        # Draw Sidebar
        self._draw_sidebar(h, w, header_pad)
        
        # Separator
        for y in range(h):
            TUI.safe_addstr(self.scr, y, self.sidebar_width, "│", curses.color_pair(4)|curses.A_DIM)
            
        # Draw Content
        self._draw_content(h, w, header_pad)
        self.scr.refresh()

    def _draw_sidebar(self, h, w, y_offset):
        TUI.safe_addstr(self.scr, y_offset, LEFT_PAD, "Build Wizard", curses.color_pair(1)|curses.A_BOLD)
        list_y = y_offset + 3
        for i, label in enumerate(self.steps):
             y = list_y + i
             style = curses.color_pair(4)
             prefix = "  "
             if i == self.current_step_idx:
                 style = curses.color_pair(3)|curses.A_BOLD
                 prefix = "● " # Static indicator
             elif i < self.current_step_idx:
                 style = curses.color_pair(2)
                 prefix = "✓ "
             
             TUI.safe_addstr(self.scr, y, LEFT_PAD, prefix + label, style)

    def _draw_content(self, h, w, y_offset):
        content_x = self.sidebar_width + 1
        content_w = w - content_x
        y = y_offset
        x = content_x + 2
        
        if self.current_step_idx == 0:
            # Configuration Screen
            if self.mismatch_error:
                TUI.safe_addstr(self.scr, y, x, self.mismatch_error, curses.color_pair(6))
                return

            TUI.safe_addstr(self.scr, y, x, "Run Config", curses.color_pair(1)|curses.A_BOLD)
            
            # Options with improved margin (dfpt)
            opts_y = y + 2
            opts = [
                (f"Debug: {'ON' if self.debug else 'OFF'}", 'd', self.debug),
                (f"Frontmatter: {'ON' if self.frontmatter else 'OFF'}", 'f', self.frontmatter),
                (f"Keep PDFs: {'ON' if self.leave_pdfs else 'OFF'}", 'p', self.leave_pdfs),
                (f"Threads: {self.threads}", 't', None),
            ]
            opt_x = x
            for label, key, val in opts:
                color = curses.color_pair(2 if val else 4)
                TUI.safe_addstr(self.scr, opts_y, opt_x, f"[{key}] {label}", color)
                opt_x += len(label) + 6 # Increased margin
            
            # Grid
            # Calculate visible based on moving title to top
            current_hover_title = None
            if 0 <= self.cursor_row < self.num_chapters:
                ch = self.hierarchy[self.cursor_row]
                if 0 <= self.cursor_col < len(ch.get('pages', [])):
                     current_hover_title = ch['pages'][self.cursor_col].get('title', 'Untitled')

            if current_hover_title:
                 TUI.safe_addstr(self.scr, opts_y + 2, x, f"Selected: {current_hover_title}", curses.color_pair(3)|curses.A_BOLD)
            else:
                 TUI.safe_addstr(self.scr, opts_y + 2, x, " ", curses.color_pair(4))

            grid_y = opts_y + 4
            visible_rows = h - grid_y - 2
            start_row = self.scroll_row
            
            for i in range(visible_rows):
                ci = start_row + i
                if ci >= self.num_chapters: break
                
                curr_y = grid_y + i
                ch = self.hierarchy[ci]
                pages = ch.get('pages', [])
                
                # Chapter Label
                ch_title = ch.get('title', f'Ch{ci}')[:20]
                TUI.safe_addstr(self.scr, curr_y, x, f"{ch_title}", curses.color_pair(4)|curses.A_BOLD)
                
                # Pages
                pg_x = x + 22
                for pi in range(self.max_pages):
                    if pg_x > w - 4: break
                    
                    is_void = (pi >= len(pages))
                    selected = False if is_void else self.selected.get((ci, pi), False)
                    is_cursor = (ci == self.cursor_row and pi == self.cursor_col)
                    
                    actual_files = self.pg_folders.get(str(ci), [])
                    file_exists = (pi < len(actual_files))
                    
                    if is_cursor and not is_void:
                        current_hover_title = pages[pi].get('title', 'Untitled')
                    
                    # Char determination
                    if is_void:
                        char = 'X'
                    elif not file_exists:
                        char = 'X' # Missing file also X per previous request
                    else:
                        char = '✓' if selected else '·'
                    
                    # Style determination with Crosshair logic
                    is_row_highlight = (ci == self.cursor_row)
                    is_col_highlight = (pi == self.cursor_col)
                    
                    style = curses.color_pair(4) # Default grey
                    
                    if is_void:
                         style = curses.color_pair(4)|curses.A_DIM # Dimmed for void padding
                    elif is_cursor:
                        # Cursor Logic
                        if not file_exists:
                             style = curses.color_pair(6)|curses.A_BOLD|curses.A_REVERSE # Red Reverse
                        elif selected:
                             style = curses.color_pair(5)|curses.A_BOLD|curses.A_REVERSE # Magenta Reverse (Standard cursor)
                        else:
                             style = curses.color_pair(5)|curses.A_REVERSE # Magenta Reverse 
                    
                    else:
                        # Non-cursor Logic
                        if not file_exists:
                             style = curses.color_pair(6)|curses.A_DIM # Red dim
                        elif selected:
                             if is_row_highlight or is_col_highlight:
                                  style = curses.color_pair(8)|curses.A_BOLD # Cyan Bold (Highlighted)
                             else:
                                  style = curses.color_pair(2) # Green
                        else:
                             # Unselected existing
                             if is_row_highlight or is_col_highlight:
                                  style = curses.color_pair(8) # Cyan for crosshair trace
                             else:
                                  style = curses.color_pair(4)|curses.A_DIM

                    TUI.safe_addstr(self.scr, curr_y, pg_x, f"[{char}]", style)
                    pg_x += 4
                    
            # Footer
            footer_text = "Space:Toggle  c:Col  r:Row  a:All  Enter:Build"
            TUI.safe_addstr(self.scr, h-2, x, footer_text, curses.color_pair(4)|curses.A_DIM)

        elif self.current_step_idx == 1:
            # Building Screen
            TUI.safe_addstr(self.scr, y, x, "Building...", curses.color_pair(1)|curses.A_BOLD)
            y += 2
             
            if self.total > 0:
                pct = max(0, min(100, self.visual_percent)) if self.visual_percent is not None else 0
                bar_w = min(40, content_w - 10)
                filled = int(bar_w * pct / 100)
                bar = '█' * filled + '░' * (bar_w - filled)
                TUI.safe_addstr(self.scr, y, x, bar, curses.color_pair(3))
                TUI.safe_addstr(self.scr, y, x + bar_w + 1, f'{pct}%', curses.color_pair(3)|curses.A_BOLD)
            y += 2
            
            if self.task:
                TUI.safe_addstr(self.scr, y, x, f"→ {self.task}", curses.color_pair(4))
            y += 2
            
            log_h = h - y - 3
            if self.build_view_mode == 'typst':
                TUI.safe_addstr(self.scr, y, x, "Typst Output", curses.color_pair(4)|curses.A_DIM)
                y += 1
                for i, line in enumerate(self.typst_logs[self.build_scroll:self.build_scroll+log_h]):
                    TUI.safe_addstr(self.scr, y+i, x, line[:content_w-4], curses.color_pair(4))
            else:
                 TUI.safe_addstr(self.scr, y, x, "Build Log", curses.color_pair(4)|curses.A_DIM)
                 y += 1
                 for i, (msg, ok) in enumerate(self.logs[-log_h:]):
                     prefix = "✓ " if ok else "  "
                     TUI.safe_addstr(self.scr, y+i, x, prefix + msg[:content_w-6], curses.color_pair(2 if ok else 4))

        elif self.current_step_idx == 2:
            # Result Screen
            if self.build_result:
                res = self.build_result
                has_warnings = res['has_warnings']
                
                # Draw Face
                face = HMM_FACE if has_warnings else HAPPY_FACE
                color = curses.color_pair(3) if has_warnings else curses.color_pair(2)
                
                for i, line in enumerate(face):
                    TUI.safe_addstr(self.scr, y + i, x, line, color | curses.A_BOLD)
                y += len(face) + 1
                
                # Title
                title = "Build Complete!" if not has_warnings else "Build Completed (with warnings)"
                TUI.safe_addstr(self.scr, y, x, title, color|curses.A_BOLD)
                y += 2
                
                TUI.safe_addstr(self.scr, y, x, f"Pages Generated: {res['page_count']}", curses.color_pair(4))
                y += 1
                if has_warnings:
                    TUI.safe_addstr(self.scr, y, x, "Warnings were detected during build.", curses.color_pair(6))
                else:
                    TUI.safe_addstr(self.scr, y, x, "No warnings.", curses.color_pair(2))
                y += 2
                TUI.safe_addstr(self.scr, y, x, f"Output: {OUTPUT_FILE.name}", curses.color_pair(4)|curses.A_DIM)
                
            TUI.safe_addstr(self.scr, h-2, x, "Press Enter to Exit", curses.color_pair(4)|curses.A_DIM)

