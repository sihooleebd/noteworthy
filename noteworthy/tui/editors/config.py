import curses
import json
from ..base import ListEditor, TUI, LEFT_PAD, TOP_PAD
from ..components.common import LineEditor
from ...config import METADATA_FILE, CONSTANTS_FILE, PREFACE_FILE
from ...utils import load_config_safe, save_config, register_key
from ..keybinds import ConfirmBind, ToggleBind, KeyBind, NavigationBind
from .schemes import extract_themes
from .text import TextEditor


class ConfigEditor(ListEditor):
    """Configuration editor with left-aligned design."""

    def __init__(self, scr):
        super().__init__(scr, 'General Settings')
        self.config = load_config_safe()
        self.themes = extract_themes()
        self._build_items()
        self.section_title = 'Configuration'
        self.content_width = 80
        
        
        # Explicit registration to fix navigation
        register_key(self.keymap, NavigationBind('UP', self.cursor_up))
        register_key(self.keymap, NavigationBind('DOWN', self.cursor_down))
        
        register_key(self.keymap, ConfirmBind(self.action_edit))
        register_key(self.keymap, ToggleBind(self.action_toggle))
        register_key(self.keymap, KeyBind(curses.KEY_RIGHT, self.action_next_value))
        register_key(self.keymap, KeyBind(curses.KEY_LEFT, self.action_prev_value))

    def _build_items(self):
        field_meta = {
            "title": ("Title", "str"),
            "subtitle": ("Subtitle", "str"),
            "authors": ("Authors", "list"),
            "affiliation": ("Affiliation", "str"),
            "font": ("Body Font", "str"),
            "title-font": ("Title Font", "str"),
            "show-solution": ("Show Solutions", "bool"),
            "display-cover": ("Display Cover", "bool"),
            "display-outline": ("Display Outline", "bool"),
            "display-chap-cover": ("Chapter Covers", "bool"),
            "chapter-name": ("Chapter Label", "str"),
            "subchap-name": ("Section Label", "str"),
            "subchap-name": ("Section Label", "str"),
            "render-sample-count": ("Render Samples", "int"),
            "render-implicit-count": ("Implicit Samples", "int"),
            "pad-chapter-id": ("Pad Chapter ID", "bool"),
            "pad-page-id": ("Pad Page ID", "bool"),
            "heading-numbering": ("Heading Numbering", "choice", ["1.1", "1.", "I.1", "A.1"])
        }

        self.fields = []
        processed_keys = set()
        
        for key, meta in field_meta.items():
            if key in self.config:
                if len(meta) == 3:
                    self.fields.append((key, meta[0], meta[1], meta[2]))
                else:
                    self.fields.append((key, meta[0], meta[1]))
                processed_keys.add(key)
        
        for key, val in self.config.items():
            if key not in processed_keys and key != 'display-mode':
                if isinstance(val, bool): ftype = "bool"
                elif isinstance(val, int): ftype = "int"
                elif isinstance(val, list): ftype = "list"
                else: ftype = "str"
                label = key.replace("-", " ").title()
                self.fields.append((key, label, ftype))
        
        self.items = self.fields
        self.items.insert(0, ('Preface', 'Edit Preface Content...', 'action'))

    def save(self):
        try:
            save_config(self.config)
            return True
        except:
            return False

    def _load(self):
        self.config = load_config_safe()
        self.themes = extract_themes()
        self._build_items()
        self.cursor = min(self.cursor, max(0, len(self.items) - 1))

    def _draw_item(self, y, x, item, width, selected):
        key = item[0]
        if len(item) == 4:
            _, label, ftype, opts = item
        else:
            _, label, ftype = item
            opts = None

        label_w = 24

        # Selection indicator
        if selected:
            TUI.safe_addstr(self.scr, y, x, '▶', curses.color_pair(3) | curses.A_BOLD)
        
        # Special case: Preface action
        if key == 'Preface':
            style = curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0)
            TUI.safe_addstr(self.scr, y, x + 2, key, style)
            TUI.safe_addstr(self.scr, y, x + label_w, label, curses.color_pair(4) | curses.A_DIM)
            return

        # Label
        style = curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0)
        TUI.safe_addstr(self.scr, y, x + 2, label[:label_w - 4], style)

        # Value
        val = self.config.get(key)
        val_str = str(val) if val is not None else "(none)"
        
        color = curses.color_pair(4)
        if selected:
            color |= curses.A_BOLD

        if ftype == 'bool':
            val_str = 'Yes' if val else 'No'
            color = curses.color_pair(2 if val else 6)
            if selected:
                color |= curses.A_BOLD
        elif ftype == 'list':
            val_str = ', '.join(val) if isinstance(val, list) else str(val)
        elif ftype == 'choice':
            if selected:
                color = curses.color_pair(5) | curses.A_BOLD
        
        TUI.safe_addstr(self.scr, y, x + label_w, val_str[:width - label_w - 2], color)

    def _draw_footer(self, h, w):
        footer = 'Enter Edit  Space Toggle  Esc Save'
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, footer, curses.color_pair(4) | curses.A_DIM)

    def action_edit(self, ctx):
        item = self.items[self.cursor]
        key = item[0]
        if len(item) == 4:
            _, label, ftype, opts = item
        else:
            _, label, ftype = item
            opts = None

        if key == 'Preface':
            editor = TextEditor(self.scr, filepath=PREFACE_FILE, title='Preface Editor')
            editor.run()
        elif ftype == 'choice' and opts:
            val = self.config.get(key, opts[0])
            try:
                idx = opts.index(val)
            except:
                idx = 0
            idx = (idx + 1) % len(opts)
            self.config[key] = opts[idx]
            self.modified = True
        elif ftype == 'bool':
            self.config[key] = not self.config.get(key, False)
            self.modified = True
        elif ftype == 'list':
            val = self.config.get(key, [])
            curr = ', '.join(val)
            new_val = LineEditor(self.scr, initial_value=curr, title=f'Edit {label}').run()
            if new_val is not None:
                self.config[key] = [s.strip() for s in new_val.split(',') if s.strip()]
                self.modified = True
        else:
            val = self.config.get(key)
            init_val = str(val) if val is not None else ""
            new_val = LineEditor(self.scr, initial_value=init_val, title=f'Edit {label}').run()
            
            if new_val is not None:
                if ftype == 'int':
                    try:
                        self.config[key] = int(new_val) if new_val else None
                    except ValueError:
                        pass
                else:
                    self.config[key] = new_val if new_val else None
                self.modified = True
    
    def action_toggle(self, ctx):
        item = self.items[self.cursor]
        key = item[0]
        if len(item) == 4:
            _, label, ftype, opts = item
        else:
            _, label, ftype = item
            opts = None
        
        if ftype == 'bool':
            self.config[key] = not self.config.get(key, False)
            self.modified = True
        elif ftype == 'choice' and opts:
            val = self.config.get(key, opts[0])
            try:
                idx = opts.index(val)
            except:
                idx = 0
            idx = (idx + 1) % len(opts)
            self.config[key] = opts[idx]
            self.modified = True

    def action_next_value(self, ctx):
        item = self.items[self.cursor]
        if len(item) == 4:
            key, _, ftype, opts = item
            if ftype == 'choice':
                val = self.config.get(key, opts[0])
                try:
                    idx = opts.index(val)
                except:
                    idx = 0
                self.config[key] = opts[(idx + 1) % len(opts)]
                self.modified = True
    
    def action_prev_value(self, ctx):
        item = self.items[self.cursor]
        if len(item) == 4:
            key, _, ftype, opts = item
            if ftype == 'choice':
                val = self.config.get(key, opts[0])
                try:
                    idx = opts.index(val)
                except:
                    idx = 0
                self.config[key] = opts[(idx - 1 + len(opts)) % len(opts)]
                self.modified = True