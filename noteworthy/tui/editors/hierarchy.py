import curses
import json
from ..base import ListEditor, TUI, LEFT_PAD, TOP_PAD
from ..components.common import LineEditor
from ..keybinds import ConfirmBind, KeyBind
from ...config import HIERARCHY_FILE
from ...utils import load_config_safe, register_key


class HierarchyEditor(ListEditor):
    """Chapter structure editor with left-aligned design."""
    
    def __init__(self, scr):
        super().__init__(scr, "Chapter Structure")
        self.hierarchy = json.loads(HIERARCHY_FILE.read_text())
        self.config = load_config_safe()
        self.filepath = HIERARCHY_FILE
        self._build_items()
        self.section_title = "Hierarchy"
        
        register_key(self.keymap, ConfirmBind(self.action_edit))
        register_key(self.keymap, KeyBind(ord('d'), self.action_delete, "Delete Item"))
    
    def _build_items(self):
        self.items = []
        for ci, ch in enumerate(self.hierarchy):
            self.items.append(("ch_title", ci, None, ch))
            self.items.append(("ch_summary", ci, None, ch))
            for pi, p in enumerate(ch.get("pages", [])):
                self.items.append(("pg_title", ci, pi, p))
            self.items.append(("add_page", ci, None, None))
        self.items.append(("add_chapter", None, None, None))
    
    def _get_value(self, item):
        t, ci, pi, _ = item
        if t == "ch_title":
            return self.hierarchy[ci]["title"]
        elif t == "ch_summary":
            return self.hierarchy[ci]["summary"]
        elif t == "pg_title":
            return self.hierarchy[ci]["pages"][pi]["title"]
        return ""
    
    def _set_value(self, val):
        t, ci, pi, _ = self.items[self.cursor]
        val = val.strip()
        
        if t == "ch_title":
            self.hierarchy[ci]["title"] = val
        elif t == "ch_summary":
            self.hierarchy[ci]["summary"] = val
        elif t == "pg_title":
            self.hierarchy[ci]["pages"][pi]["title"] = val
        
        self.modified = True
        self._build_items()
    
    def _add_chapter(self):
        next_id = str(len(self.hierarchy))
        new_ch = {"id": next_id, "title": "New Chapter", "summary": "", "pages": []}
        self.hierarchy.append(new_ch)
        self.modified = True
        self._build_items()
        for i, item in enumerate(self.items):
            if item[0] == "ch_title" and item[1] == len(self.hierarchy) - 1:
                self.cursor = i
                break
    
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
        elif t == "pg_title":
            del self.hierarchy[ci]["pages"][pi]
            self.modified = True
            self._build_items()
            self.cursor = min(self.cursor, len(self.items) - 1)
    
    def _load(self):
        self.hierarchy = json.loads(HIERARCHY_FILE.read_text())
        self._build_items()
        from ..wizards.sync import SyncWizard
        if SyncWizard(self.scr).run():
            self._load()

    def save(self):
        try:
            HIERARCHY_FILE.write_text(json.dumps(self.hierarchy, indent=4))
            self.modified = False
            from ..wizards.sync import SyncWizard
            SyncWizard(self.scr).run()
            return True
        except:
            return False

    def _draw_item(self, y, x, item, width, selected):
        t, ci, pi, _ = item
        
        if selected:
            TUI.safe_addstr(self.scr, y, x, "▶", curses.color_pair(3) | curses.A_BOLD)
        
        style = curses.color_pair(4) | (curses.A_BOLD if selected else 0)
        
        if t == "ch_title":
            label = self.config.get("chapter-name", "Chapter")
            TUI.safe_addstr(self.scr, y, x + 2, label, curses.color_pair(5) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, y, x + 14, str(self._get_value(item))[:width - 16], style)
            
        elif t == "ch_summary":
            TUI.safe_addstr(self.scr, y, x + 4, "Summary:", curses.color_pair(4) | curses.A_DIM)
            TUI.safe_addstr(self.scr, y, x + 14, str(self._get_value(item))[:width - 16], style)
            
        elif t == "pg_title":
            TUI.safe_addstr(self.scr, y, x + 4, "Page:", curses.color_pair(4))
            TUI.safe_addstr(self.scr, y, x + 14, str(self._get_value(item))[:width - 16], style)
            
        elif t == "add_page":
            TUI.safe_addstr(self.scr, y, x + 4, "+ Add page", 
                           curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else curses.A_DIM))
            
        elif t == "add_chapter":
            TUI.safe_addstr(self.scr, y, x + 2, "+ Add chapter", 
                           curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else curses.A_DIM))

    def _draw_footer(self, h, w):
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, "Enter Edit  d Delete  Esc Save", 
                       curses.color_pair(4) | curses.A_DIM)

    def action_edit(self, ctx):
        item = self.items[self.cursor]
        t, ci, pi, _ = item
        if t == "add_chapter":
            self._add_chapter()
        elif t == "add_page":
            self._add_page(ci)
        else:
            curr_val = str(self._get_value(item))
            if t == "ch_summary":
                from .text import TextEditor
                new_val = TextEditor(self.scr, initial_text=curr_val, title="Edit Summary").run()
                if new_val is not None:
                    self._set_value(new_val)
            else:
                title = "Edit Value"
                new_val = LineEditor(self.scr, initial_value=curr_val, title=title).run()
                if new_val is not None:
                    self._set_value(new_val)
    
    def action_delete(self, ctx):
        item = self.items[self.cursor]
        t = item[0]
        if t not in ("add_chapter", "add_page"):
            msg = "Delete chapter?" if t.startswith("ch_") else "Delete page?"
            if TUI.prompt_confirm(self.scr, msg):
                self._delete_current()