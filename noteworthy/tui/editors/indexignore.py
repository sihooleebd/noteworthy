import curses
from ..base import ListEditor, TUI, LEFT_PAD, TOP_PAD
from ...config import INDEXIGNORE_FILE
from ..components.common import LineEditor
from ...utils import load_indexignore, save_indexignore, register_key
from ..keybinds import ConfirmBind, KeyBind


class IndexignoreEditor(ListEditor):
    """Ignored files editor with left-aligned design."""

    def __init__(self, scr):
        super().__init__(scr, 'Ignored Files')
        self.filepath = INDEXIGNORE_FILE
        self.ignored = sorted(list(load_indexignore()))
        self._update_items()
        self.section_title = 'Ignored Patterns'
        
        register_key(self.keymap, ConfirmBind(self.action_enter))
        register_key(self.keymap, KeyBind(ord('n'), self.action_add, "Add Pattern"))
        register_key(self.keymap, KeyBind(ord('d'), self.action_delete, "Delete Pattern"))
        
    def action_enter(self, ctx):
        if self.items[self.cursor] == "+ Add pattern...":
            self.action_add(ctx)
        else:
            curr = self.ignored[self.cursor]
            new_val = LineEditor(self.scr, initial_value=curr, title="Edit Pattern").run()
            if new_val is not None:
                self.ignored[self.cursor] = new_val
                self.ignored.sort()
                self._update_items()
                self.modified = True

    def action_add(self, ctx):
        val = LineEditor(self.scr, title='Add Ignore Pattern').run()
        if val and val not in self.ignored:
            self.ignored.append(val)
            self.ignored.sort()
            self._update_items()
            self.modified = True
            
    def action_delete(self, ctx):
        if self.items and self.items[self.cursor] != "+ Add pattern...":
            if TUI.prompt_confirm(self.scr, "Delete pattern?"):
                del self.ignored[self.cursor]
                self._update_items()
                self.modified = True
                self.cursor = min(self.cursor, len(self.items) - 1)

    def _update_items(self):
        self.items = self.ignored + ["+ Add pattern..."]

    def save(self):
        save_indexignore(set(self.ignored))
        self.modified = False
        return True

    def _load(self):
        self.ignored = sorted(list(load_indexignore()))
        self._update_items()

    def _draw_item(self, y, x, item, width, selected):
        if selected:
            TUI.safe_addstr(self.scr, y, x, '▶', curses.color_pair(3) | curses.A_BOLD)
        
        if item == "+ Add pattern...":
            style = curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else curses.A_DIM)
            TUI.safe_addstr(self.scr, y, x + 2, item, style)
        else:
            style = curses.color_pair(4) | (curses.A_BOLD if selected else 0)
            TUI.safe_addstr(self.scr, y, x + 2, item[:width - 4], style)

    def _draw_footer(self, h, w):
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, 'Enter Edit  n Add  d Delete  Esc Save', 
                       curses.color_pair(4) | curses.A_DIM)
