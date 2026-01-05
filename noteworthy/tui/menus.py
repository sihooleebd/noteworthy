import curses
from .base import TUI, LEFT_PAD, TOP_PAD
from ..assets import LOGO
from ..utils import register_key, handle_key_event
from .keybinds import KeyBind, NavigationBind, ConfirmBind


def show_keybindings_menu(scr):
    """Display keybindings help screen."""
    h, w = scr.getmaxyx()
    scr.clear()
    
    TUI.safe_addstr(scr, TOP_PAD, LEFT_PAD, 'KEYBINDINGS', curses.color_pair(1) | curses.A_BOLD)
    
    keys = [
        ('', 'General'),
        ('↑↓/jk', 'Navigate'),
        ('Enter', 'Select / Confirm'),
        ('Esc', 'Back / Cancel'),
        ('?', 'Show this help'),
        ('', ''),
        ('', 'Editors'),
        ('Space', 'Toggle'),
        ('Enter', 'Edit value'),
        ('d', 'Delete'),
        ('n', 'New item'),
        ('', ''),
        ('', 'Builder'),
        ('Space', 'Toggle chapter/page'),
        ('a/n', 'Select all / none'),
    ]
    
    y = TOP_PAD + 2
    for key, desc in keys:
        if not key:
            TUI.safe_addstr(scr, y, LEFT_PAD, desc, curses.color_pair(5) | curses.A_BOLD)
        else:
            TUI.safe_addstr(scr, y, LEFT_PAD, key, curses.color_pair(4) | curses.A_BOLD)
            TUI.safe_addstr(scr, y, LEFT_PAD + 12, desc, curses.color_pair(4))
        y += 1
        if y >= h - 3:
            break
    
    TUI.safe_addstr(scr, h - 2, LEFT_PAD, 'Press any key to close', curses.color_pair(4) | curses.A_DIM)
    scr.refresh()
    scr.getch()


class MainMenu:
    """Main menu with left-aligned design."""

    def __init__(self, scr):
        self.scr = scr
        self.options = [
            ('e', 'Editor', 'Edit configuration and content'),
            ('b', 'Builder', 'Build PDF document')
        ]
        self.selected = 0
        
        self.keymap = {}
        register_key(self.keymap, NavigationBind('UP', self.move_prev))
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
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        # Draw logo (left-aligned)
        logo_y = TOP_PAD
        for i, line in enumerate(LOGO):
            TUI.safe_addstr(self.scr, logo_y + i, LEFT_PAD, line, curses.color_pair(1) | curses.A_BOLD)
        
        # Title below logo
        title_y = logo_y + len(LOGO) + 1
        TUI.safe_addstr(self.scr, title_y, LEFT_PAD, 'NOTEWORTHY', curses.color_pair(1) | curses.A_BOLD)
        
        # Menu options
        menu_y = title_y + 3
        for i, (key, label, desc) in enumerate(self.options):
            y = menu_y + i * 2
            
            if i == self.selected:
                TUI.safe_addstr(self.scr, y, LEFT_PAD, '▶', curses.color_pair(3) | curses.A_BOLD)
                TUI.safe_addstr(self.scr, y, LEFT_PAD + 2, label, curses.color_pair(2) | curses.A_BOLD)
            else:
                TUI.safe_addstr(self.scr, y, LEFT_PAD + 2, label, curses.color_pair(4))
            
            TUI.safe_addstr(self.scr, y, LEFT_PAD + 14, f'({key})', curses.color_pair(4) | curses.A_DIM)
        
        # Footer
        footer = '↑↓ Navigate  Enter Confirm  Esc Quit  ? Help'
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, footer, curses.color_pair(4) | curses.A_DIM)
        
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