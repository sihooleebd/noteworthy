import curses
import subprocess
from ...config import OUTPUT_FILE
from ...assets import SAD_FACE, HAPPY_FACE, HMM_FACE
from ...utils import register_key, handle_key_event
from ..base import TUI, LEFT_PAD, TOP_PAD
from ..keybinds import KeyBind, ConfirmBind, NavigationBind


class LineEditor:
    """Single-line text input with left-aligned design."""

    def __init__(self, scr, title='Edit', initial_value=''):
        self.scr = scr
        self.title = title
        self.value = initial_value
        self.cursor_pos = len(initial_value)
        
        self.keymap = {}
        register_key(self.keymap, KeyBind(27, self.action_cancel, "Cancel"))
        register_key(self.keymap, ConfirmBind(self.action_confirm))
        register_key(self.keymap, KeyBind([curses.KEY_BACKSPACE, 127, 8], self.action_backspace, "Backspace"))
        register_key(self.keymap, KeyBind(curses.KEY_LEFT, self.action_left, "Left"))
        register_key(self.keymap, KeyBind(curses.KEY_RIGHT, self.action_right, "Right"))
        register_key(self.keymap, KeyBind([curses.KEY_DC, 330], self.action_delete, "Delete"))

    def action_cancel(self, ctx):
        return 'EXIT_CANCEL'

    def action_confirm(self, ctx):
        return 'EXIT_CONFIRM'

    def action_backspace(self, ctx):
        if self.cursor_pos > 0:
            self.value = self.value[:self.cursor_pos - 1] + self.value[self.cursor_pos:]
            self.cursor_pos -= 1
            
    def action_delete(self, ctx):
        if self.cursor_pos < len(self.value):
            self.value = self.value[:self.cursor_pos] + self.value[self.cursor_pos + 1:]

    def action_left(self, ctx):
        self.cursor_pos = max(0, self.cursor_pos - 1)
        
    def action_right(self, ctx):
        self.cursor_pos = min(len(self.value), self.cursor_pos + 1)

    def handle_char(self, char):
        self.value = self.value[:self.cursor_pos] + char + self.value[self.cursor_pos:]
        self.cursor_pos += 1
        return True

    def run(self):
        h, w = self.scr.getmaxyx()
        curses.curs_set(1)
        scroll_off = 0
        max_input_w = w - LEFT_PAD - 4
        
        while True:
            if not TUI.check_terminal_size(self.scr):
                curses.curs_set(0)
                return None
            
            self.scr.clear()
            
            # Title
            TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, self.title, curses.color_pair(1) | curses.A_BOLD)
            
            # Input field
            input_y = TOP_PAD + 2
            
            if self.cursor_pos < scroll_off:
                scroll_off = self.cursor_pos
            if self.cursor_pos >= scroll_off + max_input_w:
                scroll_off = self.cursor_pos - max_input_w + 1
            
            disp_val = self.value[scroll_off:scroll_off + max_input_w]
            TUI.safe_addstr(self.scr, input_y, LEFT_PAD, disp_val, curses.color_pair(4) | curses.A_BOLD)
            
            # Underline effect
            TUI.safe_addstr(self.scr, input_y + 1, LEFT_PAD, '─' * min(len(self.value) + 1, max_input_w), curses.color_pair(4) | curses.A_DIM)
            
            # Footer
            TUI.safe_addstr(self.scr, TOP_PAD + 5, LEFT_PAD, 'Enter Confirm  Esc Cancel', curses.color_pair(4) | curses.A_DIM)
            
            # Position cursor
            cur_x = LEFT_PAD + (self.cursor_pos - scroll_off)
            try:
                self.scr.move(input_y, cur_x)
            except:
                pass
            
            self.scr.refresh()
            k = self.scr.getch()
            handled, res = handle_key_event(k, self.keymap, self)
            if handled:
                if res == 'EXIT_CANCEL':
                    curses.curs_set(0)
                    return None
                elif res == 'EXIT_CONFIRM':
                    curses.curs_set(0)
                    return self.value
            elif 32 <= k <= 126:
                self.handle_char(chr(k))


def copy_to_clipboard(text):
    """Copy text to system clipboard."""
    for cmd in [
        ['pbcopy'],
        ['clip'],
        ['wl-copy'],
        ['xclip', '-selection', 'clipboard'],
        ['xsel', '-b', '-i'],
    ]:
        try:
            encoding = 'utf-16le' if 'clip' in cmd else 'utf-8'
            subprocess.run(cmd, input=text.encode(encoding), check=True, stderr=subprocess.DEVNULL)
            return True
        except:
            pass
    return False


class LogScreen:
    """Log viewer with left-aligned design."""
    
    def __init__(self, scr, log, title_func, draw_func):
        self.scr = scr
        self.log = log
        self.title_func = title_func
        self.draw_func = draw_func
        self.view_log = False
        self.copied = False
        self.scroll = 0
        
        self.keymap = {}
        register_key(self.keymap, KeyBind(ord('v'), self.action_toggle_log, "View Log"))
        register_key(self.keymap, KeyBind(ord('c'), self.action_copy, "Copy Log"))
        register_key(self.keymap, KeyBind(27, self.action_esc, "Back/Exit"))

    def handle_key(self, k):
        if k == ord('v') or k == ord('c'):
            return handle_key_event(k, self.keymap, self)
        
        if not self.view_log:
            return True, 'EXIT'
        
        # Log view navigation
        if k in (curses.KEY_UP, ord('k')):
            self.scroll = max(0, self.scroll - 1)
            return True, None
        if k in (curses.KEY_DOWN, ord('j')):
            self.scroll += 1
            return True, None
            
        return handle_key_event(k, self.keymap, self)

    def action_toggle_log(self, ctx):
        self.view_log = not self.view_log
        self.copied = False
        self.scroll = 0
        
    def action_copy(self, ctx):
        if self.view_log:
            self.copied = copy_to_clipboard(self.log)
            
    def action_esc(self, ctx):
        if self.view_log:
            self.action_toggle_log(ctx)
        else:
            return 'EXIT'
        
    def run(self):
        self.scr.nodelay(False)
        self.scr.timeout(-1)
        curses.flushinp()
        
        while True:
            if not TUI.check_terminal_size(self.scr):
                return
                
            self.scr.clear()
            h, w = self.scr.getmaxyx()
            
            if self.view_log:
                header = "LOG" if not self.copied else "LOG (copied!)"
                TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, header, curses.color_pair(6) | curses.A_BOLD)
                
                lines = self.log.split('\n')
                visible = h - TOP_PAD - 4
                for i, line in enumerate(lines[self.scroll:self.scroll + visible]):
                    TUI.safe_addstr(self.scr, TOP_PAD + 2 + i, LEFT_PAD, line[:w - LEFT_PAD - 2], curses.color_pair(4))
                
                TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, 'v Back  c Copy  ↑↓ Scroll', curses.color_pair(4) | curses.A_DIM)
            else:
                self.draw_func(self.scr, h, w)
            
            self.scr.refresh()
            k = self.scr.getch()
            if k == -1:
                continue
            handled, res = self.handle_key(k)
            if handled and res == 'EXIT':
                break


def show_error_screen(scr, error):
    """Display error with left-aligned design."""
    import traceback
    log = traceback.format_exc()
    if log.strip() == 'NoneType: None':
        log = str(error)
    
    def draw(s, h, w):
        y = TOP_PAD
        
        # Face
        for i, line in enumerate(SAD_FACE):
            TUI.safe_addstr(s, y + i, LEFT_PAD, line, curses.color_pair(6) | curses.A_BOLD)
        
        y += len(SAD_FACE) + 1
        
        # Title
        is_build_error = "Build failed" in str(error)
        title = 'BUILD ERROR' if is_build_error else 'ERROR'
        TUI.safe_addstr(s, y, LEFT_PAD, title, curses.color_pair(6) | curses.A_BOLD)
        
        # Message
        TUI.safe_addstr(s, y + 2, LEFT_PAD, str(error)[:w - LEFT_PAD - 4], curses.color_pair(4))
        
        # Footer
        TUI.safe_addstr(s, h - 2, LEFT_PAD, "v View log  Esc Exit", curses.color_pair(4) | curses.A_DIM)

    LogScreen(scr, log, None, draw).run()


def show_success_screen(scr, page_count, has_warnings=False, typst_logs=None):
    """Display success with left-aligned design."""
    log = '\n'.join(typst_logs) if typst_logs else ""
    
    def draw(s, h, w):
        y = TOP_PAD
        face = HMM_FACE if has_warnings else HAPPY_FACE
        color = curses.color_pair(3) if has_warnings else curses.color_pair(2)
        
        # Face
        for i, line in enumerate(face):
            TUI.safe_addstr(s, y + i, LEFT_PAD, line, color | curses.A_BOLD)
        
        y += len(face) + 1
        
        # Title
        title = 'BUILD SUCCEEDED' + (' (with warnings)' if has_warnings else '')
        TUI.safe_addstr(s, y, LEFT_PAD, title, color | curses.A_BOLD)
        
        # Details
        TUI.safe_addstr(s, y + 2, LEFT_PAD, f'{OUTPUT_FILE.name}', curses.color_pair(4))
        TUI.safe_addstr(s, y + 3, LEFT_PAD, f'{page_count} pages', curses.color_pair(4) | curses.A_DIM)
        
        # Footer
        hint = "v View log  Esc Exit" if has_warnings else "Press any key"
        TUI.safe_addstr(s, h - 2, LEFT_PAD, hint, curses.color_pair(4) | curses.A_DIM)

    LogScreen(scr, log, None, draw).run()
