import curses
import subprocess
from ...config import SAD_FACE, HAPPY_FACE, HMM_FACE, OUTPUT_FILE
from ...utils import register_key, handle_key_event
from ..base import TUI
from ..keybinds import KeyBind, ConfirmBind, NavigationBind

class LineEditor:

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
        h_raw, w_raw = self.scr.getmaxyx()
        box_h = 7
        box_w = max(50, len(self.title) + 10, len(self.value) + 10)
        box_w = min(box_w, w_raw - 2)
        
        bh, bw = (14, min(40, w_raw - 4))
        by, bx = TUI.center(self.scr, bh, bw)
        
        box_y = by
        box_x = bx
        
        curses.curs_set(1)
        
        scroll_off = 0
        
        while True:
            if not TUI.check_terminal_size(self.scr):
                return None
                
            TUI.draw_box(self.scr, box_y, box_x, box_h, box_w, self.title)
            TUI.safe_addstr(self.scr, box_y + 4, box_x + 2, 'Enter: Confirm  Esc: Cancel', curses.color_pair(4) | curses.A_DIM)
            input_y = box_y + 2
            input_x = box_x + 2
            max_len = box_w - 4
            
            if self.cursor_pos < scroll_off:
                scroll_off = self.cursor_pos
            if self.cursor_pos >= scroll_off + max_len:
                scroll_off = self.cursor_pos - max_len + 1
            
            disp_val = self.value[scroll_off:scroll_off + max_len]
            
            TUI.safe_addstr(self.scr, input_y, input_x, ' ' * max_len, curses.color_pair(4))
            TUI.safe_addstr(self.scr, input_y, input_x, disp_val, curses.color_pair(1) | curses.A_BOLD)
            
            real_cur_x = input_x + 1 + (self.cursor_pos - scroll_off)
            
            real_cur_x = min(real_cur_x, input_x + 1 + max_len) 
            
            real_y = input_y + 1
            try:
                self.scr.move(real_y, real_cur_x)
            except:
                pass
            
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
    try:
        subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
    try:
        subprocess.run(['clip'], input=text.encode('utf-16le'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
    try:
        subprocess.run(['wl-copy'], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
    try:
        subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
    try:
        subprocess.run(['xsel', '-b', '-i'], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
    return False

class LogScreen:
    def __init__(self, scr, log, title_func, draw_func):
        self.scr = scr
        self.log = log
        self.title_func = title_func
        self.draw_func = draw_func
        self.view_log = False
        self.copied = False
        
        self.keymap = {}
        register_key(self.keymap, KeyBind(ord('v'), self.action_toggle_log, "View Log"))
        register_key(self.keymap, KeyBind(ord('c'), self.action_copy, "Copy Log"))
        register_key(self.keymap, KeyBind(27, self.action_esc, "Back/Exit"))
        register_key(self.keymap, KeyBind(None, self.action_any, "Exit"))

    def handle_key(self, k):
        if k == ord('v') or k == ord('c'):
             return handle_key_event(k, self.keymap, self)
        
        if not self.view_log:
             return True, 'EXIT'
             
        return handle_key_event(k, self.keymap, self)

    def action_toggle_log(self, ctx):
        self.view_log = not self.view_log
        self.copied = False
        
    def action_copy(self, ctx):
        if self.view_log:
            self.copied = copy_to_clipboard(self.log)
            
    def action_esc(self, ctx):
        if self.view_log:
            self.action_toggle_log(ctx)
        else:
            return 'EXIT'
            
    def action_any(self, ctx):
        if not self.view_log: return 'EXIT'
        
    def run(self):
        self.scr.nodelay(False)
        self.scr.timeout(-1)
        curses.flushinp()
        
        while True:
            if not TUI.check_terminal_size(self.scr):
                return
                
            self.scr.clear()
            h, w = TUI.get_dims(self.scr)
            
            if self.view_log:
                 header = "LOG (press 'v' or 'Esc' to go back, 'c' to copy)"
                 if self.copied: header = 'LOG (copied to clipboard!)'
                 TUI.safe_addstr(self.scr, 0, 2, header, curses.color_pair(6) | curses.A_BOLD)
                 for i, line in enumerate(self.log.split('\n')[:h-3]):
                     TUI.safe_addstr(self.scr, i + 2, 2, line, curses.color_pair(4))
            else:
                 self.draw_func(self.scr, h, w)
            
            self.scr.refresh()
            k = self.scr.getch()
            if k == -1: continue
            handled, res = self.handle_key(k)
            if handled and res == 'EXIT': break

def show_error_screen(scr, error):
    import traceback
    log = traceback.format_exc()
    if log.strip() == 'NoneType: None': log = str(error)
    
    def draw(s, h, w):
        face = SAD_FACE
        total_h = len(face) + 2 + 1 + 2 + 1
        
        cy, cx = TUI.center(s, content_h=total_h if total_h < h else h)
        y = cy + 1
        
        for i, line in enumerate(face):
             _, lx = TUI.center(s, content_w=len(line))
             TUI.safe_addstr(s, y + i, lx, line, curses.color_pair(6) | curses.A_BOLD)
             
        my = y + len(face) + 2
        
        is_build_error = "Build failed" in str(error) or (isinstance(error, Exception) and getattr(error, 'is_build_error', False))
        title = 'BUILD ERROR' if is_build_error else 'FATAL ERROR'
        _, tx = TUI.center(s, content_w=len(title))
        TUI.safe_addstr(s, my, tx, title, curses.color_pair(6) | curses.A_BOLD)
        
        err = str(error)[:max(10, w - 10)]
        _, ex = TUI.center(s, content_w=len(err))
        TUI.safe_addstr(s, my + 2, ex, err, curses.color_pair(4))
        
        hint = "Press 'v' to view log  |  Esc: Exit"
        _, hx = TUI.center(s, content_w=len(hint))
        TUI.safe_addstr(s, my + 4, hx, hint, curses.color_pair(4) | curses.A_DIM)

    LogScreen(scr, log, None, draw).run()

def show_success_screen(scr, page_count, has_warnings=False, typst_logs=None):
    log = '\n'.join(typst_logs) if typst_logs else ""
    
    def draw(s, h, w):
        face = HMM_FACE if has_warnings else HAPPY_FACE
        color = curses.color_pair(3) if has_warnings else curses.color_pair(2)
        
        total_h = len(face) + 2 + 1 + 2 + 1
        cy, cx = TUI.center(s, content_h=total_h)
        y = cy + 1
        
        for i, line in enumerate(face):
            _, lx = TUI.center(s, content_w=len(line))
            TUI.safe_addstr(s, y + i, lx, line, color | curses.A_BOLD)
            
        my = y + len(face) + 2
        title = 'BUILD SUCCEEDED (with warnings)' if has_warnings else 'BUILD SUCCEEDED!'
        _, tx = TUI.center(s, content_w=len(title))
        TUI.safe_addstr(s, my, tx, title, color | curses.A_BOLD)
        
        msg = f'Created: {OUTPUT_FILE} ({page_count} pages)'
        _, mx = TUI.center(s, content_w=len(msg))
        TUI.safe_addstr(s, my + 2, mx, msg, curses.color_pair(4))
        
        hint = "Press 'v' to view log  |  Esc: Exit" if has_warnings else 'Press any key to exit...'
        _, hx = TUI.center(s, content_w=len(hint))
        TUI.safe_addstr(s, my + 4, hx, hint, curses.color_pair(4) | curses.A_DIM)

    LogScreen(scr, log, None, draw).run()
