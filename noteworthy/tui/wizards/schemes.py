import curses
import json
import shutil
from pathlib import Path
from ..base import TUI
from ...config import SCHEMES_FILE, BASE_DIR

class SchemesWizard:

    def __init__(self, scr):
        self.scr = scr

    def run(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        bw, bh = (min(60, w - 4), 8)
        bx, by = ((w - bw) // 2, (h - bh) // 2)
        TUI.draw_box(self.scr, by, bx, bh, bw, 'SCHEMES SETUP')
        TUI.safe_addstr(self.scr, by + 2, bx + 2, 'Schemes configuration is missing.', curses.color_pair(4))
        TUI.safe_addstr(self.scr, by + 3, bx + 2, 'Restore default color themes?', curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, by + 5, bx + 2, 'Press Enter to Restore  |  Esc to Cancel', curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
        while True:
            if not TUI.check_terminal_size(self.scr):
                return None
            k = self.scr.getch()
            if k == 27:
                return None
            elif k in (ord('\n'), 10, curses.KEY_ENTER):
                break
        try:
            minimal_schemes = {'noteworthy-dark': {'page-fill': '#262323', 'text-main': '#d8d0cc', 'text-heading': '#ddbfa1', 'text-muted': '#8f8582', 'text-accent': '#d49c93', 'blocks': {}, 'plot': {'stroke': '#ddbfa1', 'highlight': '#d4aa8e', 'grid-opacity': 0.15}}}
            default_src = BASE_DIR / 'templates/config/schemes.json'
            if default_src.exists() and default_src != SCHEMES_FILE:
                shutil.copy(default_src, SCHEMES_FILE)
            else:
                SCHEMES_FILE.parent.mkdir(parents=True, exist_ok=True)
                SCHEMES_FILE.write_text(json.dumps(minimal_schemes, indent=4))
            return True
        except:
            return None