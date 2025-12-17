import curses
from ..base import ListEditor, TUI
from ..components.common import LineEditor
from ...config import SNIPPETS_FILE
from ..keybinds import ConfirmBind, KeyBind
from ...utils import register_key

class SnippetsEditor(ListEditor):
    def __init__(self, scr):
        super().__init__(scr, "Code Snippets")
        self.filepath = SNIPPETS_FILE
        self._load_snippets()
        self.box_title = "Snippets"
        self.box_width = 80
        
        register_key(self.keymap, ConfirmBind(self.action_select))
        register_key(self.keymap, KeyBind(ord('n'), self.action_new, "New Snippet"))
        register_key(self.keymap, KeyBind(ord('d'), self.action_delete, "Delete Snippet"))
    
    def action_select(self, ctx):
        if self.cursor >= len(self.snippets):
            self.action_new(ctx)
        else:
            name, definition = self.snippets[self.cursor]
            new_name = LineEditor(self.scr, initial_value=name, title="Edit Snippet Name").run()
            if new_name is not None:
                self.snippets[self.cursor][0] = new_name
                self.modified = True
            new_def = LineEditor(self.scr, initial_value=definition, title="Edit Definition").run()
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
        if new_name is not None: self.snippets[self.cursor][0] = new_name
        new_def = LineEditor(self.scr, initial_value=definition, title="New Definition").run()
        if new_def is not None: self.snippets[self.cursor][1] = new_def
        
    def action_delete(self, ctx):
         if self.cursor < len(self.snippets) and self.snippets:
            if TUI.prompt_confirm(self.scr, "Delete snippet? (y/n): "):
                del self.snippets[self.cursor]
            if self.cursor >= len(self.snippets): self.cursor = max(0, len(self.snippets) - 1)
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
        except: pass
        if not self.snippets: self.snippets = [["example", "[example text]"]]
        self._update_items()

    def _update_items(self):
        self.items = self.snippets + [["+ Add new snippet...", ""]]

    def _load(self):
        self._load_snippets()

    def _save_snippets(self):
        lines = []
        for name, definition in self.snippets:
            lines.append(f"#let {name} = {definition}")
        SNIPPETS_FILE.write_text('\n'.join(lines) + '\n')
        self.modified = False
    
    def save(self):
        try: self._save_snippets(); return True
        except: return False

    def _draw_item(self, y, x, item, width, selected):
        name, definition = item
        left_w = 22
        
        if selected: TUI.safe_addstr(self.scr, y, x + 2, ">", curses.color_pair(3) | curses.A_BOLD)
        
        if name == "+ Add new snippet...":
            TUI.safe_addstr(self.scr, y, x + 4, name, curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else curses.A_DIM))
        else:
            TUI.safe_addstr(self.scr, y, x + 4, name[:left_w - 6], curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0))
            TUI.safe_addstr(self.scr, y, x + left_w + 2, definition[:width - left_w - 6], curses.color_pair(4) | (curses.A_BOLD if selected else 0))

    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        list_h = min(len(self.items) + 2, h - 8)
        total_h = 2 + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        
        title_str = f"{self.title}{' *' if self.modified else ''}"
        TUI.safe_addstr(self.scr, start_y, (w - len(title_str)) // 2, title_str, curses.color_pair(1) | curses.A_BOLD)
        
        bw = min(self.box_width, w - 4)
        bx = (w - bw) // 2
        left_w = 22
        
        TUI.draw_box(self.scr, start_y + 2, bx, list_h, bw, self.box_title)
        
        TUI.safe_addstr(self.scr, start_y + 3, bx + 4, "Name", curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, start_y + 3, bx + left_w + 2, "Definition", curses.color_pair(1) | curses.A_BOLD)
        
        for i in range(1, list_h - 1):
            TUI.safe_addstr(self.scr, start_y + 2 + i, bx + left_w, "│", curses.color_pair(4) | curses.A_DIM)
        
        vis = list_h - 3
        if self.cursor < self.scroll: self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis: self.scroll = self.cursor - vis + 1
        
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.items): break
            y = start_y + 4 + i
            self._draw_item(y, bx, self.items[idx], bw, idx == self.cursor)
            
        self._draw_footer(h, w)
        self.scr.refresh()

    def _draw_footer(self, h, w):
        footer = "n: New  d: Delete  Enter: Edit  Esc: Save & Exit  x: Export  l: Import"
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
