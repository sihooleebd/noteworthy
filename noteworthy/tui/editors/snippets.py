import curses
from ..base import ListEditor, TUI, LEFT_PAD, TOP_PAD
from ..components.common import LineEditor
from ...config import SNIPPETS_FILE
from ..keybinds import ConfirmBind, KeyBind
from ...utils import register_key


class SnippetsEditor(ListEditor):
    """Code snippets editor with left-aligned design."""
    
    def __init__(self, scr):
        super().__init__(scr, "Code Snippets")
        self.filepath = SNIPPETS_FILE
        self._load_snippets()
        self.section_title = "Snippets"
        
        register_key(self.keymap, ConfirmBind(self.action_select))
        register_key(self.keymap, KeyBind(ord('n'), self.action_new, "New Snippet"))
        register_key(self.keymap, KeyBind(ord('d'), self.action_delete, "Delete Snippet"))
    
    def action_select(self, ctx):
        if self.cursor >= len(self.snippets):
            self.action_new(ctx)
        else:
            name, definition = self.snippets[self.cursor]
            new_name = LineEditor(self.scr, initial_value=name, title="Snippet Name").run()
            if new_name is not None:
                self.snippets[self.cursor][0] = new_name
                self.modified = True
            new_def = LineEditor(self.scr, initial_value=definition, title="Definition").run()
            if new_def is not None:
                self.snippets[self.cursor][1] = new_def
                self.modified = True
                
    def action_new(self, ctx):
        self.snippets.append(["new_snippet", "[definition]"])
        self.cursor = len(self.snippets) - 1
        self.modified = True
        self._update_items()
        
        name, definition = self.snippets[self.cursor]
        new_name = LineEditor(self.scr, initial_value=name, title="New Snippet Name").run()
        if new_name is not None:
            self.snippets[self.cursor][0] = new_name
        new_def = LineEditor(self.scr, initial_value=definition, title="Definition").run()
        if new_def is not None:
            self.snippets[self.cursor][1] = new_def
        
    def action_delete(self, ctx):
        if self.cursor < len(self.snippets) and self.snippets:
            if TUI.prompt_confirm(self.scr, "Delete snippet?"):
                del self.snippets[self.cursor]
                self.cursor = min(self.cursor, max(0, len(self.snippets) - 1))
                self.modified = True
                self._update_items()
    
    def _load_snippets(self):
        self.snippets = []
        try:
            content = SNIPPETS_FILE.read_text()
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('#let ') and '=' in line:
                    rest = line[5:]
                    eq_pos = rest.find('=')
                    if eq_pos != -1:
                        name = rest[:eq_pos].strip()
                        if '(' in name:
                            name = name[:name.find('(') + 1] + name[name.find('(') + 1:name.find(')') + 1]
                        definition = rest[eq_pos + 1:].strip()
                        self.snippets.append([name, definition])
        except:
            pass
        if not self.snippets:
            self.snippets = [["example", "[example text]"]]
        self._update_items()

    def _update_items(self):
        self.items = self.snippets + [["+ Add snippet...", ""]]

    def _load(self):
        self._load_snippets()

    def _save_snippets(self):
        lines = [f"#let {name} = {definition}" for name, definition in self.snippets]
        SNIPPETS_FILE.write_text('\n'.join(lines) + '\n')
        self.modified = False
    
    def save(self):
        try:
            self._save_snippets()
            return True
        except:
            return False

    def _draw_item(self, y, x, item, width, selected):
        name, definition = item
        
        if selected:
            TUI.safe_addstr(self.scr, y, x, "▶", curses.color_pair(3) | curses.A_BOLD)
        
        if name == "+ Add snippet...":
            style = curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else curses.A_DIM)
            TUI.safe_addstr(self.scr, y, x + 2, name, style)
        else:
            name_style = curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0)
            def_style = curses.color_pair(4) | (curses.A_BOLD if selected else 0)
            TUI.safe_addstr(self.scr, y, x + 2, name[:20], name_style)
            TUI.safe_addstr(self.scr, y, x + 24, definition[:width - 26], def_style)

    def _draw_footer(self, h, w):
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, "n New  d Delete  Enter Edit  Esc Save", 
                       curses.color_pair(4) | curses.A_DIM)
