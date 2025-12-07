import curses
from ..base import TUI
from .config import ConfigEditor
from .hierarchy import HierarchyEditor
from .schemes import SchemeEditor
from .snippets import SnippetsEditor
from .indexignore import IndexignoreEditor

def show_editor_menu(scr):
    options = [
        ("c", "General Settings", "Edit configuration"),
        ("h", "Chapter Structure", "Edit document structure"),
        ("s", "Color Themes", "Edit color themes"),
        ("p", "Code Snippets", "Edit custom snippets"),
        ("i", "Ignored Files", "Manage ignored files"),
    ]
    cur = 0
    while True:
        h_raw, w_raw = scr.getmaxyx()
        h, w = (h_raw - 2, w_raw - 2)
        scr.clear()
        bw = 50
        bh = len(options) * 3 + 2
        bx = (w - bw) // 2
        by = (h - bh) // 2
        TUI.draw_box(scr, by, bx, bh + 2, bw, 'Select Editor')
        for i, (key, label, desc) in enumerate(options):
            y = by + 2 + i * 3
            selected = i == cur
            style = curses.color_pair(2) | curses.A_BOLD if selected else curses.color_pair(4)
            if selected:
                TUI.safe_addstr(scr, y, bx + 2, '▶', curses.color_pair(3) | curses.A_BOLD)
            TUI.safe_addstr(scr, y, bx + 4, f'{label}', style)
            TUI.safe_addstr(scr, y, bx + bw - 5, f'({key.upper()})', curses.color_pair(4) | curses.A_DIM)
            TUI.safe_addstr(scr, y + 1, bx + 6, desc, curses.color_pair(4) | curses.A_DIM)
        footer = 'Enter: Select  Esc: Back'
        TUI.safe_addstr(scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        scr.refresh()
        k = scr.getch()
        if k == 27:
            return
        elif k in (curses.KEY_UP, ord('k')):
            cur = max(0, cur - 1)
        elif k in (curses.KEY_DOWN, ord('j')):
            cur = min(len(options) - 1, cur + 1)
        elif k in (ord('\n'), 10):
            sel = options[cur][0]
            if sel == 'c':
                ConfigEditor(scr).run()
            elif sel == 'h':
                HierarchyEditor(scr).run()
            elif sel == 's':
                SchemeEditor(scr).run()
            elif sel == 'p':
                SnippetsEditor(scr).run()
            elif sel == 'i':
                IndexignoreEditor(scr).run()
        elif k == ord('c'):
            ConfigEditor(scr).run()
        elif k == ord('h'):
            HierarchyEditor(scr).run()
        elif k == ord('s'):
            SchemeEditor(scr).run()
        elif k == ord('p'):
            SnippetsEditor(scr).run()
        elif k == ord('i'):
            IndexignoreEditor(scr).run()