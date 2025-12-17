import curses
from .base import TUI
from ..config import LOGO
from ..utils import register_key, handle_key_event
from .keybinds import KeyBind, NavigationBind, ConfirmBind

def show_keybindings_menu(scr):
    h_raw, w_raw = scr.getmaxyx()
    h, w = (h_raw - 2, w_raw - 2)
    bw, bh = (60, 20)
    bx, by = ((w - bw) // 2, (h - bh) // 2)
    win = curses.newwin(bh, bw, by, bx)
    win.box()
    start_y = 2
    win.addstr(0, 2, ' KEYBINDINGS ', curses.color_pair(1) | curses.A_BOLD)
    keys = [('General', ''), ('Arrows/hjkl', 'Navigation'), ('Enter', 'Select / Confirm'), ('Esc', 'Back / Cancel'), ('?', 'Show this help'), ('', ''), ('Editors', ''), ('Space', 'Toggle Checkbox / Bool'), ('i', 'Insert (Text)'), ('d', 'Delete (Item/Line)'), ('n', 'New Item'), ('s', 'Save (explicit)'), ('', ''), ('Builder', ''), ('Space', 'Toggle Chapter/Page'), ('a / n', 'Select All / None'), ('d / f / l', 'Toggle Options'), ('c', 'Configure Flags')]
    for k, v in keys:
        if not v:
            win.addstr(start_y, 2, k, curses.color_pair(5) | curses.A_BOLD)
        else:
            win.addstr(start_y, 4, k, curses.color_pair(4) | curses.A_BOLD)
            win.addstr(start_y, 24, v, curses.color_pair(4))
        start_y += 1
        if start_y >= bh - 2:
            break
    win.addstr(bh - 2, 2, 'Press any key to close...', curses.color_pair(4) | curses.A_DIM)
    win.refresh()
    win.getch()

class MainMenu:

    def __init__(self, scr):
        self.scr = scr
        self.options = [('e', 'Editor', 'Edit configuration and content'), ('b', 'Builder', 'Build PDF document')]
        self.selected = 1
        
        self.keymap = {}
        register_key(self.keymap, NavigationBind('LEFT', self.move_prev))
        register_key(self.keymap, NavigationBind('UP', self.move_prev))
        register_key(self.keymap, NavigationBind('RIGHT', self.move_next))
        register_key(self.keymap, NavigationBind('DOWN', self.move_next))
        register_key(self.keymap, ConfirmBind(self.action_confirm))
        register_key(self.keymap, KeyBind(27, self.action_exit, "Exit"))
        register_key(self.keymap, KeyBind(ord('?'), self.action_help, "Help"))
        register_key(self.keymap, KeyBind(ord('e'), self.action_editor, "Editor"))
        register_key(self.keymap, KeyBind(ord('b'), self.action_builder, "Builder"))

    def move_prev(self, ctx):
        self.selected = max(0, self.selected - 1)
        
    def move_next(self, ctx):
        self.selected = min(len(self.options) - 1, self.selected + 1)
        
    def action_confirm(self, ctx):
        return self.options[self.selected][1].lower()
        
    def action_editor(self, ctx):
        return 'editor'
        
    def action_builder(self, ctx):
        return 'builder'
        
    def action_exit(self, ctx):
        return 'EXIT'
        
    def action_help(self, ctx):
        show_keybindings_menu(self.scr)

    def draw(self):
        h_raw, w_raw = self.scr.getmaxyx()
        h, w = (h_raw - 2, w_raw - 2)
        self.scr.clear()
        lh = len(LOGO)
        layout = 'vert'
        if h < lh + 18 and w > 80:
            layout = 'horz'
        if layout == 'vert':
            start_y = max(1, (h - lh - 10) // 2)
            lgx = (w - 14) // 2
            for i, line in enumerate(LOGO):
                TUI.safe_addstr(self.scr, start_y + i, lgx, line, curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, start_y + lh + 1, (w - 10) // 2, 'NOTEWORTHY', curses.color_pair(1) | curses.A_BOLD)
            btn_y = start_y + lh + 4
            btn_w = 20
            start_x = (w - (btn_w * 2 + 4)) // 2
            for i, (key, label, desc) in enumerate(self.options):
                bx = start_x + i * (btn_w + 4)
                style = curses.color_pair(2) | curses.A_BOLD if i == self.selected else curses.color_pair(4)
                TUI.draw_box(self.scr, btn_y, bx, 5, btn_w, '')
                TUI.safe_addstr(self.scr, btn_y + 2, bx + (btn_w - len(label)) // 2, label, style)
                TUI.safe_addstr(self.scr, btn_y + 5, bx + (btn_w - 3) // 2, f'({key.upper()})', curses.color_pair(4) | curses.A_DIM)
        else:
            total_w = 16 + 8 + 30
            start_x = (w - total_w) // 2
            start_y = (h - lh) // 2
            for i, line in enumerate(LOGO):
                TUI.safe_addstr(self.scr, start_y + i, start_x, line, curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, start_y + lh + 1, start_x + 2, 'NOTEWORTHY', curses.color_pair(1) | curses.A_BOLD)
            btn_x = start_x + 24
            btn_start_y = start_y + (lh - 10) // 2
            btn_w = 20
            for i, (key, label, desc) in enumerate(self.options):
                by = btn_start_y + i * 6
                style = curses.color_pair(2) | curses.A_BOLD if i == self.selected else curses.color_pair(4)
                TUI.draw_box(self.scr, by, btn_x, 5, btn_w, '')
                TUI.safe_addstr(self.scr, by + 2, btn_x + (btn_w - len(label)) // 2, label, style)
                TUI.safe_addstr(self.scr, by + 2, btn_x + btn_w + 2, f'({key.upper()})', curses.color_pair(4) | curses.A_DIM)
        footer = 'Arrows: Select  Enter: Confirm  Esc: Quit'
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()

    def run(self):
        self.scr.timeout(-1)
        while True:
            if not TUI.check_terminal_size(self.scr):
                return None
            self.draw()
            k = self.scr.getch()
            handled, res = handle_key_event(k, self.keymap, self)
            if handled:
                if res == 'EXIT':
                    return 'EXIT'
                elif res:
                    return res