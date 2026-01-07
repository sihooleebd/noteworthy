import curses
import sys
import termios

from pathlib import Path
from ..core.config_mgmt import export_file, import_file, list_exports_for
from ..utils import register_key, handle_key_event
from .keybinds import SaveBind, ExitBind, NavigationBind, KeyBind

# Layout constants
LEFT_PAD = 4
TOP_PAD = 2
MIN_HEIGHT = 30
MIN_WIDTH = 100


class TUI:
    """Core TUI utilities with left-aligned, borderless design."""

    @staticmethod
    def init_colors():
        curses.start_color()
        curses.use_default_colors()
        for i, color in enumerate([curses.COLOR_CYAN, curses.COLOR_GREEN, curses.COLOR_YELLOW, curses.COLOR_WHITE, curses.COLOR_MAGENTA, curses.COLOR_RED], 1):
            curses.init_pair(i, color, -1)
        if curses.COLORS >= 256:
            for i in range(16, 256):
                curses.init_pair(i, i, -1)
        curses.curs_set(0)

    @staticmethod
    def disable_flow_control():
        try:
            fd = sys.stdin.fileno()
            attrs = termios.tcgetattr(fd)
            attrs[0] &= ~(termios.IXON | termios.IXOFF)
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
        except:
            pass

    @staticmethod
    def safe_addstr(scr, y, x, text, attr=0):
        """Write text at position with bounds checking."""
        try:
            h, w = scr.getmaxyx()
            if 0 <= y < h and 0 <= x < w:
                scr.addstr(y, x, text[:w - x - 1], attr)
        except curses.error:
            pass

    @staticmethod
    def get_dims(scr):
        """Get usable dimensions (full screen)."""
        return scr.getmaxyx()

    @staticmethod
    def get_content_area(scr):
        """Get content area with padding applied."""
        h, w = scr.getmaxyx()
        return h - TOP_PAD, w - LEFT_PAD

    @staticmethod
    def center(scr, content_h=1, content_w=1):
        """Calculate start coordinates to center content."""
        h, w = scr.getmaxyx()
        start_y = max(0, (h - content_h) // 2)
        start_x = max(0, (w - content_w) // 2)
        return start_y, start_x

    @staticmethod
    def prompt_save(scr):
        h, w = scr.getmaxyx()
        msg = 'Save? (y/n/c): '
        TUI.safe_addstr(scr, h - 2, LEFT_PAD, msg, curses.color_pair(3) | curses.A_BOLD)
        scr.refresh()
        c = scr.getch()
        return chr(c) if c in (ord('y'), ord('n'), ord('c')) else 'c'

    @staticmethod
    def prompt_confirm(scr, message='Are you sure? (y/n): '):
        h, w = scr.getmaxyx()
        scr.clear()
        
        TUI.safe_addstr(scr, TOP_PAD, LEFT_PAD, message, curses.color_pair(3) | curses.A_BOLD)
        TUI.safe_addstr(scr, TOP_PAD + 2, LEFT_PAD, '[y] Yes    [n] No', curses.color_pair(4))
        
        scr.refresh()
        while True:
            c = scr.getch()
            if c in (ord('y'), ord('Y')):
                return True
            if c in (ord('n'), ord('N'), 27):
                return False

    @staticmethod
    def show_saved(scr):
        h, w = scr.getmaxyx()
        TUI.safe_addstr(scr, h - 2, LEFT_PAD, 'Saved!', curses.color_pair(2) | curses.A_BOLD)
        scr.refresh()
        curses.napms(500)

    @staticmethod
    def show_message(scr, title, message):
        h, w = scr.getmaxyx()
        scr.clear()
        
        TUI.safe_addstr(scr, TOP_PAD, LEFT_PAD, title, curses.color_pair(1) | curses.A_BOLD)
        
        lines = message.split('\n')
        for i, line in enumerate(lines):
            TUI.safe_addstr(scr, TOP_PAD + 2 + i, LEFT_PAD, line, curses.color_pair(4))
        
        hint = "Press any key to continue"
        TUI.safe_addstr(scr, TOP_PAD + 3 + len(lines), LEFT_PAD, hint, curses.color_pair(4) | curses.A_DIM)
        
        scr.refresh()
        scr.getch()

    @staticmethod
    def check_terminal_size(scr, min_h=MIN_HEIGHT, min_w=MIN_WIDTH):
        was_error = False
        while True:
            h, w = scr.getmaxyx()
            if h >= min_h and w >= min_w:
                if was_error:
                    scr.clear()
                    scr.refresh()
                return True
            
            was_error = True
            scr.clear()
            
            TUI.safe_addstr(scr, TOP_PAD, LEFT_PAD, 'Terminal too small!', curses.color_pair(6) | curses.A_BOLD)
            TUI.safe_addstr(scr, TOP_PAD + 1, LEFT_PAD, f'Current: {h}×{w}', curses.color_pair(4))
            TUI.safe_addstr(scr, TOP_PAD + 2, LEFT_PAD, f'Required: {min_h}×{min_w}', curses.color_pair(4) | curses.A_DIM)
            
            scr.refresh()
            curses.napms(100)
            curses.flushinp()
            
            if scr.getch() in (ord('q'), 27):
                return False

    # Keep draw_box for backwards compatibility but deprecate
    @staticmethod
    def draw_box(scr, y, x, h, w, title=''):
        """Deprecated: Use borderless design instead."""
        pass  # No-op - borderless design


class BaseEditor:
    """Base class for all editors with left-aligned design."""

    def do_export(self, ctx=None):
        from .components.common import LineEditor, show_error_screen
        if not hasattr(self, 'filepath') or not self.filepath:
            return
        suf = LineEditor(self.scr, title='Export Suffix (Optional)', initial_value='').run()
        if suf is None:
            return
        res = export_file(self.filepath, suf)
        if res:
            from ..config import BASE_DIR
            try:
                relative_path = Path(res).relative_to(BASE_DIR)
            except:
                relative_path = Path(res).name
            msg = f"Saved to: {relative_path}"
            TUI.show_message(self.scr, "Export Successful", msg)
        else:
            show_error_screen(self.scr, 'Export failed')

    def do_import(self, ctx=None):
        from .components.common import show_error_screen
        if not hasattr(self, 'filepath') or not self.filepath:
            return
        backups = list_exports_for(self.filepath.name)
        if not backups:
            show_error_screen(self.scr, 'No backups found')
            return
        
        h, w = self.scr.getmaxyx()
        sel = 0
        max_visible = h - TOP_PAD - 6
        
        while True:
            self.scr.clear()
            TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, 'Select Backup', curses.color_pair(1) | curses.A_BOLD)
            
            for i, b in enumerate(backups[:max_visible]):
                y = TOP_PAD + 2 + i
                if i == sel:
                    TUI.safe_addstr(self.scr, y, LEFT_PAD, f'▶ {b}', curses.color_pair(3) | curses.A_BOLD)
                else:
                    TUI.safe_addstr(self.scr, y, LEFT_PAD + 2, b, curses.color_pair(4))
            
            TUI.safe_addstr(self.scr, h - 3, LEFT_PAD, "Enter Select  Esc Back", curses.color_pair(4) | curses.A_DIM)
            
            self.scr.refresh()
            k = self.scr.getch()
            if k == 27:
                return
            elif k in (curses.KEY_UP, ord('k')):
                sel = max(0, sel - 1)
            elif k in (curses.KEY_DOWN, ord('j')):
                sel = min(len(backups) - 1, sel + 1)
            elif k in (ord('\n'), 10):
                if TUI.prompt_confirm(self.scr, 'Overwrite current file?'):
                    from ..config import BASE_DIR
                    src = BASE_DIR / 'exports' / backups[sel]
                    if import_file(src, self.filepath):
                        TUI.show_message(self.scr, "Import Successful", "File imported. Editor will reload.")
                        if hasattr(self, '_load'):
                            self._load()
                        return
                    else:
                        show_error_screen(self.scr, 'Import failed')
                return

    def __init__(self, scr, title='Editor'):
        self.scr = scr
        self.title = title
        self.modified = False
        self.keymap = {}
        self.content_width = 70
        TUI.init_colors()
        
        register_key(self.keymap, ExitBind(self.do_exit))
        register_key(self.keymap, SaveBind())
        
    def do_exit(self, ctx=None):
        if self.modified:
            self.save()
        return 'EXIT'

    def refresh(self):
        raise NotImplementedError

    def save(self):
        raise NotImplementedError

    def run(self):
        self.refresh()
        while True:
            if not TUI.check_terminal_size(self.scr):
                return
            
            k = self.scr.getch()
            handled, res = self.handle_input(k)
            if handled:
                if res == 'EXIT': return res
                if res is not None: return res
            
            self.refresh()

    def handle_input(self, k):
        handled, res = handle_key_event(k, self.keymap, self)
        if handled:
            return True, res
        
        if k == ord('x'): 
            self.do_export()
            return True, None
        elif k == ord('l'): 
            self.do_import()
            return True, None
        
        self._handle_input(k)
        return False, None

    def _handle_input(self, k):
        pass


class ListEditor(BaseEditor):
    """Base editor for list-based content with left-aligned design."""

    def __init__(self, scr, title='List Editor'):
        super().__init__(scr, title)
        self.items = []
        self.cursor = 0
        self.scroll = 0
        self.section_title = 'Items'
        
        register_key(self.keymap, NavigationBind('UP', self.cursor_up))
        register_key(self.keymap, NavigationBind('DOWN', self.cursor_down))
        register_key(self.keymap, NavigationBind('PGUP', self.cursor_pgup))
        register_key(self.keymap, NavigationBind('PGDN', self.cursor_pgdn))
        register_key(self.keymap, NavigationBind('HOME', self.cursor_home))
        register_key(self.keymap, NavigationBind('END', self.cursor_end))

    def _draw_item(self, y, x, item, width, selected):
        """Override to customize item rendering."""
        raise NotImplementedError

    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        # Title
        title_str = f"{self.title}{' *' if self.modified else ''}"
        TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, title_str, curses.color_pair(1) | curses.A_BOLD)
        
        # Section header
        TUI.safe_addstr(self.scr, TOP_PAD + 2, LEFT_PAD, self.section_title, curses.color_pair(4) | curses.A_DIM)
        
        # Calculate visible area
        list_start_y = TOP_PAD + 3
        visible_rows = h - list_start_y - 3
        content_w = min(self.content_width, w - LEFT_PAD - 2)
        
        # Scroll adjustment
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + visible_rows:
            self.scroll = self.cursor - visible_rows + 1
        
        # Draw items
        for i in range(visible_rows):
            idx = self.scroll + i
            if idx >= len(self.items):
                break
            y = list_start_y + i
            self._draw_item(y, LEFT_PAD, self.items[idx], content_w, idx == self.cursor)
        
        # Footer
        self._draw_footer(h, w)
        self.scr.refresh()

    def _draw_footer(self, h, w):
        footer = 'Esc Save & Exit'
        count_str = f"Item {self.cursor + 1}/{len(self.items)}"
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, footer, curses.color_pair(4) | curses.A_DIM)
        # Draw count aligned right
        TUI.safe_addstr(self.scr, h - 2, w - len(count_str) - 2, count_str, curses.color_pair(4) | curses.A_DIM)

    def cursor_up(self, ctx):
        self.cursor = max(0, self.cursor - 1)
        
    def cursor_down(self, ctx):
        self.cursor = min(len(self.items) - 1, self.cursor + 1)
        
    def cursor_pgup(self, ctx):
        h, _ = self.scr.getmaxyx()
        jump = h - TOP_PAD - 6
        if jump < 1: jump = 1
        self.cursor = max(0, self.cursor - jump)

    def cursor_pgdn(self, ctx):
        h, _ = self.scr.getmaxyx()
        jump = h - TOP_PAD - 6
        if jump < 1: jump = 1
        self.cursor = min(len(self.items) - 1, self.cursor + jump)
        
    def cursor_home(self, ctx):
        self.cursor = 0
        
    def cursor_end(self, ctx):
        self.cursor = len(self.items) - 1