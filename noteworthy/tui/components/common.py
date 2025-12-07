import curses
import subprocess
from ...config import SAD_FACE, HAPPY_FACE, HMM_FACE, OUTPUT_FILE
from ..base import TUI

class LineEditor:

    def __init__(self, scr, title='Edit', initial_value=''):
        self.scr = scr
        self.title = title
        self.value = initial_value

    def run(self):
        h_raw, w_raw = self.scr.getmaxyx()
        box_h = 7
        box_w = max(50, len(self.title) + 10, len(self.value) + 10)
        box_y = (h_raw - box_h) // 2
        box_x = (w_raw - box_w) // 2
        curses.curs_set(1)
        while True:
            TUI.draw_box(self.scr, box_y, box_x, box_h, box_w, self.title)
            TUI.safe_addstr(self.scr, box_y + 4, box_x + 2, 'Enter: Confirm  Esc: Cancel', curses.color_pair(4) | curses.A_DIM)
            input_y = box_y + 2
            input_x = box_x + 2
            max_len = box_w - 4
            disp_val = self.value
            if len(disp_val) >= max_len:
                disp_val = disp_val[-(max_len - 1):]
            TUI.safe_addstr(self.scr, input_y, input_x, ' ' * max_len, curses.color_pair(4))
            TUI.safe_addstr(self.scr, input_y, input_x, disp_val, curses.color_pair(1) | curses.A_BOLD)
            real_y = input_y + 1
            real_x = input_x + 1 + len(disp_val)
            self.scr.move(real_y, real_x)
            k = self.scr.getch()
            if k == 27:
                curses.curs_set(0)
                return None
            elif k in (ord('\n'), 10, curses.KEY_ENTER):
                curses.curs_set(0)
                return self.value
            elif k in (curses.KEY_BACKSPACE, 127, 8):
                self.value = self.value[:-1]
            elif 32 <= k <= 126:
                self.value += chr(k)

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

def show_error_screen(scr, error):
    import traceback
    log = traceback.format_exc()
    if log.strip() == 'NoneType: None':
        log = str(error)
    view_log = False
    copied = False
    while True:
        scr.clear()
        h_raw, w_raw = scr.getmaxyx()
        h, w = (h_raw - 2, w_raw - 2)
        if view_log:
            header = "ERROR LOG (press 'v' to go back, 'c' to copy)"
            if copied:
                header = 'ERROR LOG (copied to clipboard!)'
            TUI.safe_addstr(scr, 0, 2, header, curses.color_pair(6) | curses.A_BOLD)
            for i, line in enumerate(log.split('\n')[:h - 3]):
                TUI.safe_addstr(scr, i + 2, 2, line, curses.color_pair(4))
        else:
            y = max(0, (h - len(SAD_FACE) - 8) // 2)
            for i, line in enumerate(SAD_FACE):
                TUI.safe_addstr(scr, y + i, (w - 9) // 2, line, curses.color_pair(6) | curses.A_BOLD)
            my = y + len(SAD_FACE) + 2
            my = y + len(SAD_FACE) + 2
            
            is_build_error = "Build failed" in str(error) or isinstance(error, Exception) and getattr(error, 'is_build_error', False)
            title = 'BUILD FAILED' if is_build_error else 'FATAL ERROR'
            
            TUI.safe_addstr(scr, my, (w - len(title)) // 2, title, curses.color_pair(6) | curses.A_BOLD)
            err = str(error)[:w - 10]
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
    with open('debug_trace.log', 'a') as f:
        f.write('Entered show_success_screen\n')
    view_log = False
    copied = False
    while True:
        scr.clear()
        h_raw, w_raw = scr.getmaxyx()
        h, w = (h_raw - 2, w_raw - 2)
        if view_log and typst_logs:
            header = "TYPST LOG (press 'v' to go back, 'c' to copy)"
            if copied:
                header = 'TYPST LOG (copied to clipboard!)'
            TUI.safe_addstr(scr, 0, 2, header, curses.color_pair(3) | curses.A_BOLD)
            for i, line in enumerate(typst_logs[:h - 3]):
                c = 6 if 'error:' in line.lower() else 3 if 'warning:' in line.lower() else 4
                TUI.safe_addstr(scr, i + 2, 2, line[:w - 4], curses.color_pair(c))
        else:
            face = HMM_FACE if has_warnings else HAPPY_FACE
            color = curses.color_pair(3) if has_warnings else curses.color_pair(2)
            y = max(0, (h - len(face) - 8) // 2)
            for i, line in enumerate(face):
                TUI.safe_addstr(scr, y + i, (w - len(face[0])) // 2, line, color | curses.A_BOLD)
            my = y + len(face) + 2
            title = 'BUILD SUCCEEDED (with warnings)' if has_warnings else 'BUILD SUCCEEDED!'
            TUI.safe_addstr(scr, my, (w - len(title)) // 2, title, color | curses.A_BOLD)
            msg = f'Created: {OUTPUT_FILE} ({page_count} pages)'
            TUI.safe_addstr(scr, my + 2, (w - len(msg)) // 2, msg, curses.color_pair(4))
            if has_warnings:
                hint = "Press 'v' to view log  |  Press any other key to exit"
            else:
                hint = 'Press any key to exit...'
            TUI.safe_addstr(scr, my + 4, (w - len(hint)) // 2, hint, curses.color_pair(4) | curses.A_DIM)
        scr.refresh()
        key = scr.getch()
        if key == -1:
            continue
        if key == ord('v') and has_warnings:
            view_log = not view_log
            copied = False
        elif key == ord('c') and view_log and typst_logs:
            copied = copy_to_clipboard('\n'.join(typst_logs))
        elif not view_log:
            break