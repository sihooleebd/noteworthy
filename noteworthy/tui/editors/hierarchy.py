import curses
import json
from ..base import ListEditor, TUI
from ..components.common import LineEditor
from ..keybinds import ConfirmBind, KeyBind
from ...config import HIERARCHY_FILE
from ...utils import load_config_safe, register_key

class HierarchyEditor(ListEditor):
    def __init__(self, scr):
        super().__init__(scr, "Chapter Structure")
        self.hierarchy = json.loads(HIERARCHY_FILE.read_text())
        self.config = load_config_safe()
        self.filepath = HIERARCHY_FILE
        self._build_items()
        self.box_title = "Hierarchy"
        self.box_width = 75
        
        register_key(self.keymap, ConfirmBind(self.action_edit))
        register_key(self.keymap, KeyBind(ord('d'), self.action_delete, "Delete Item"))
    
    def _build_items(self):
        self.items = []
        for ci, ch in enumerate(self.hierarchy):
            self.items.append(("ch_title", ci, None, ch))
            self.items.append(("ch_summary", ci, None, ch))
            for pi, p in enumerate(ch.get("pages", [])):
                self.items.append(("pg_title", ci, pi, p))
                self.items.append(("pg_id", ci, pi, p)) # NEW: Editable ID
            self.items.append(("add_page", ci, None, None))
        self.items.append(("add_chapter", None, None, None))
    
    def _get_value(self, item):
        t, ci, pi, _ = item
        if t == "ch_title": return self.hierarchy[ci]["title"]
        elif t == "ch_summary": return self.hierarchy[ci]["summary"]
        elif t == "pg_title": return self.hierarchy[ci]["pages"][pi]["title"]
        elif t == "pg_id": return self.hierarchy[ci]["pages"][pi].get("id", str(pi)) # Show ID
        return ""
    
    def _set_value(self, val):
        t, ci, pi, _ = self.items[self.cursor]
        val = val.strip()
        
        if t == "ch_title": self.hierarchy[ci]["title"] = val
        elif t == "ch_summary": self.hierarchy[ci]["summary"] = val
        elif t == "pg_title": self.hierarchy[ci]["pages"][pi]["title"] = val
        elif t == "pg_id": self.hierarchy[ci]["pages"][pi]["id"] = val # Edit ID
        
        self.modified = True; self._build_items()
    
    def _add_chapter(self):
        # Default ID needed for new chapters if we use IDs
        next_id = str(len(self.hierarchy))
        new_ch = {"id": next_id, "title": "New Chapter", "summary": "", "pages": []}
        self.hierarchy.append(new_ch)
        self.modified = True
        self._build_items()
        for i, item in enumerate(self.items):
            if item[0] == "ch_title" and item[1] == len(self.hierarchy) - 1:
                self.cursor = i; break
    
    def _add_page(self, ci):
        pages = self.hierarchy[ci]["pages"]
        next_id = str(len(pages))
        new_page = {"id": next_id, "title": "New Page"}
        pages.append(new_page)
        self.modified = True
        self._build_items()
    
    def _delete_current(self):
        t, ci, pi, _ = self.items[self.cursor]
        if t in ("ch_title", "ch_summary"):
            if len(self.hierarchy) > 1:
                del self.hierarchy[ci]
                self.modified = True
                self._build_items()
                self.cursor = min(self.cursor, len(self.items) - 1)
        elif t in ("pg_title", "pg_id"):
            del self.hierarchy[ci]["pages"][pi]
            self.modified = True
            self._build_items()
            self.cursor = min(self.cursor, len(self.items) - 1)
    
    def _load(self):
        self.hierarchy = json.loads(HIERARCHY_FILE.read_text())
        self._build_items()
        # Trigger Sync Wizard on load
        from ..wizards.sync import SyncWizard
        if SyncWizard(self.scr).run():
            self._load() # Reload if changed by wizard

    def save(self):
        try:
            HIERARCHY_FILE.write_text(json.dumps(self.hierarchy, indent=4))
            self.modified = False
            
            # Post-save sync check
            from ..wizards.sync import SyncWizard
            SyncWizard(self.scr).run()
            
            return True
        except Exception:
            return False

    def refresh(self):
        h, w = TUI.get_dims(self.scr)
        self.scr.clear()
        
        list_h = min(len(self.items) + 2, h - 8)
        total_h = 2 + list_h + 2
        
        cy, cx = TUI.center(self.scr, total_h, self.box_width)
        start_y = cy + 1 
        
        title_str = f"{self.title}{' *' if self.modified else ''}"
        ty, tx = TUI.center(self.scr, content_w=len(title_str))
        TUI.safe_addstr(self.scr, start_y, tx, title_str, curses.color_pair(1) | curses.A_BOLD)
        
        bw = min(self.box_width, w - 4)
        _, bx = TUI.center(self.scr, content_w=bw)
        left_w = 30 
        
        TUI.draw_box(self.scr, start_y + 2, bx, list_h, bw, self.box_title)
        
        TUI.safe_addstr(self.scr, start_y + 3, bx + 4, "Item", curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, start_y + 3, bx + left_w + 2, "Value", curses.color_pair(1) | curses.A_BOLD)
        
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

    def _draw_item(self, y, x, item, width, selected):
        t, ci, pi, _ = item
        left_w = 30
        
        if selected: TUI.safe_addstr(self.scr, y, x + 2, ">", curses.color_pair(3) | curses.A_BOLD)
        
        val_x = x + left_w + 2
        
        if t == "ch_title":
            label = self.config.get("chapter-name", "Chapter")
            TUI.safe_addstr(self.scr, y, x + 4, label[:left_w-6], curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0))
            val = str(self._get_value(item))
            TUI.safe_addstr(self.scr, y, val_x, val[:width-left_w-6], curses.color_pair(4) | (curses.A_BOLD if selected else 0))
            
        elif t == "ch_summary":
            TUI.safe_addstr(self.scr, y, x + 6, "Summary", curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0))
            val = str(self._get_value(item))
            TUI.safe_addstr(self.scr, y, val_x, val[:width-left_w-6], curses.color_pair(4) | (curses.A_BOLD if selected else 0))
            
        elif t == "pg_title":
            # Page Title
            TUI.safe_addstr(self.scr, y, x + 6, "Page Title", curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0))
            val = str(self._get_value(item))
            TUI.safe_addstr(self.scr, y, val_x, val[:width-left_w-6], curses.color_pair(4) | (curses.A_BOLD if selected else 0))
            
        elif t == "pg_id":
            # Page ID (Filename) - Indented slightly more or distinguished?
            TUI.safe_addstr(self.scr, y, x + 8, "File ID", curses.color_pair(5 if selected else 4) | curses.A_DIM)
            val = str(self._get_value(item)) + ".typ" # Show extension for clarity
            TUI.safe_addstr(self.scr, y, val_x, val[:width-left_w-6], curses.color_pair(4) | (curses.A_BOLD if selected else curses.A_DIM))
            
        elif t == "add_page":
            TUI.safe_addstr(self.scr, y, x + 6, "+ Add page...", curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else curses.A_DIM))
            
        elif t == "add_chapter":
            TUI.safe_addstr(self.scr, y, x + 4, "+ Add chapter...", curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else curses.A_DIM))

    def _draw_footer(self, h, w):
        footer = "Enter: Edit  d: Delete  Esc: Save & Exit  x: Export  l: Import"
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    def action_edit(self, ctx):
        item = self.items[self.cursor]; t, ci, pi, _ = item
        if t == "add_chapter": self._add_chapter()
        elif t == "add_page": self._add_page(ci)
        else:
            curr_val = str(self._get_value(item))
            if t == "ch_summary":
                from .text import TextEditor
                new_val = TextEditor(self.scr, initial_text=curr_val, title="Edit Summary").run()
                if new_val is not None: self._set_value(new_val)
            else:
                title = "Edit Value"
                if t == "pg_id": title = "Edit File ID (without .typ)"
                new_val = LineEditor(self.scr, initial_value=curr_val, title=title).run()
                if new_val is not None: self._set_value(new_val)

    def action_delete(self, ctx):
        item = self.items[self.cursor]; t = item[0]
        if t not in ("add_chapter", "add_page"):
            msg = "Delete item?"
            if t.startswith("ch_"): msg = "Delete ENTIRE Chapter? (y/n): "
            elif t.startswith("pg_"): msg = "Delete Page? (y/n): "
            
            if TUI.prompt_confirm(self.scr, msg):
                self._delete_current()