import curses
from ..base import TUI, LEFT_PAD, TOP_PAD
from ...assets import LOGO
from .config import ConfigEditor
from .hierarchy import HierarchyEditor
from .schemes import SchemeEditor
from .snippets import SnippetsEditor
from .indexignore import IndexignoreEditor
from .module_config import ModuleConfigEditor


def show_editor_menu(scr):
    """Editor selection menu with left-aligned design."""
    options = [
        ("c", "General Settings", "Edit configuration"),
        ("m", "Module Config", "Manage packages"),
        ("h", "Chapter Structure", "Edit document structure"),
        ("s", "Color Themes", "Edit color themes"),
        ("p", "Code Snippets", "Edit custom snippets"),
        ("i", "Ignored Files", "Manage ignored files"),
    ]
    cur = 0
    
    while True:
        h, w = scr.getmaxyx()
        scr.clear()
        
        y = TOP_PAD
        
        # Logo
        for i, line in enumerate(LOGO):
            if y + i >= h - 20:
                break
            TUI.safe_addstr(scr, y + i, LEFT_PAD, line, curses.color_pair(1) | curses.A_BOLD)
        y += len(LOGO) + 1
        
        # Title
        TUI.safe_addstr(scr, y, LEFT_PAD, 'Select Editor', curses.color_pair(1) | curses.A_BOLD)
        y += 2
        
        # Options list
        for i, (key, label, desc) in enumerate(options):
            opt_y = y + i * 2
            
            if i == cur:
                TUI.safe_addstr(scr, opt_y, LEFT_PAD, '▶', curses.color_pair(3) | curses.A_BOLD)
                TUI.safe_addstr(scr, opt_y, LEFT_PAD + 2, label, curses.color_pair(2) | curses.A_BOLD)
            else:
                TUI.safe_addstr(scr, opt_y, LEFT_PAD + 2, label, curses.color_pair(4))
            
            TUI.safe_addstr(scr, opt_y, LEFT_PAD + 22, f'({key})', curses.color_pair(4) | curses.A_DIM)
            TUI.safe_addstr(scr, opt_y + 1, LEFT_PAD + 4, desc, curses.color_pair(4) | curses.A_DIM)
        
        # Footer
        TUI.safe_addstr(scr, h - 2, LEFT_PAD, 'Enter Select  Esc Back', curses.color_pair(4) | curses.A_DIM)
        
        scr.refresh()
        k = scr.getch()
        
        if k == 27:
            return
        elif k in (curses.KEY_UP, ord('k')):
            cur = max(0, cur - 1)
        elif k in (curses.KEY_DOWN, ord('j')):
            cur = min(len(options) - 1, cur + 1)
        elif k in (ord('\n'), 10):
            _run_editor(scr, options[cur][0])
        elif k == ord('c'):
            _run_editor(scr, 'c')
        elif k == ord('m'):
            _run_editor(scr, 'm')
        elif k == ord('h'):
            _run_editor(scr, 'h')
        elif k == ord('s'):
            _run_editor(scr, 's')
        elif k == ord('p'):
            _run_editor(scr, 'p')
        elif k == ord('i'):
            _run_editor(scr, 'i')


def _run_editor(scr, key):
    """Launch the appropriate editor by key."""
    editors = {
        'c': ConfigEditor,
        'm': ModuleConfigEditor,
        'h': HierarchyEditor,
        's': SchemeEditor,
        'p': SnippetsEditor,
        'i': IndexignoreEditor,
    }
    if key in editors:
        editors[key](scr).run()