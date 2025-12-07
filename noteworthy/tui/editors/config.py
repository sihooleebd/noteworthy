import curses
import json
from ..base import ListEditor, TUI
from ..components.common import LineEditor
from ...config import CONFIG_FILE, PREFACE_FILE
from ...utils import load_config_safe, save_config
from .schemes import extract_themes
from .text import TextEditor

class ConfigEditor(ListEditor):

    def __init__(self, scr):
        super().__init__(scr, 'CONFIGURATION')
        self.config = load_config_safe()
        self.filepath = CONFIG_FILE
        self.themes = extract_themes()
        self._build_items()
        self.box_title = 'Settings'
        self.box_width = 80 # Increased width for better margin

    def _build_items(self):
        # Metadata for known fields to ensure nice display and ordering
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
            "box-margin": ("Box Margin", "str"),
            "box-inset": ("Box Inset", "str"),
            "render-sample-count": ("Render Samples", "int"),
            "render-implicit-count": ("Implicit Samples", "int"),
            "pad-chapter-id": ("Pad Chapter ID", "bool"),
            "pad-page-id": ("Pad Page ID", "bool")
        }

        self.fields = []
        processed_keys = set()
        
        # 1. Add known fields
        # 1. Add known fields
        for key, meta in field_meta.items():
            if key in self.config:
                 if len(meta) == 3: self.fields.append((key, meta[0], meta[1], meta[2]))
                 else: self.fields.append((key, meta[0], meta[1]))
                 processed_keys.add(key)
        
        # 2. Add remaining
        for key, val in self.config.items():
            if key not in processed_keys and key != 'display-mode':
                if isinstance(val, bool): ftype = "bool"
                elif isinstance(val, int): ftype = "int"
                elif isinstance(val, list): ftype = "list"
                else: ftype = "str"
                label = key.replace("-", " ").title()
                self.fields.append((key, label, ftype))
        
        self.items = self.fields
        # Sort not needed as we manual ordered known fields
        self.items = self.fields
        # Sort not needed as we manual ordered known fields
        self.items.insert(0, ('Preface', 'Edit Preface Content...', 'action'))

    def save(self):
        return save_config(self.config)

    def _draw_item(self, y, x, item, width, selected):
        key = item[0]
        # Check type
        if len(item) == 4: _, label, ftype, opts = item
        else: _, label, ftype = item

        left_w = 26 # Increased margin

        if selected:
            TUI.safe_addstr(self.scr, y, x + 2, '>', curses.color_pair(3) | curses.A_BOLD)
        
        if key == 'Preface':
            TUI.safe_addstr(self.scr, y, x + 4, key, curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0))
            TUI.safe_addstr(self.scr, y, x + left_w, "│", curses.color_pair(4) | curses.A_DIM)
            TUI.safe_addstr(self.scr, y, x + left_w + 2, label, curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else 0))
            return

        TUI.safe_addstr(self.scr, y, x + 4, label[:left_w - 6], curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0))
        
        # Draw separator
        TUI.safe_addstr(self.scr, y, x + left_w, "│", curses.color_pair(4) | curses.A_DIM)

        val = self.config.get(key)
        val_str = str(val) if val is not None else "(none)"
        
        color = curses.color_pair(4)
        if selected: color = color | curses.A_BOLD

        if ftype == 'bool':
            val_str = 'Yes' if val else 'No'
            color = curses.color_pair(2 if val else 6) | curses.A_BOLD
        elif ftype == 'list':
            val_str = ', '.join(val) if isinstance(val, list) else str(val)
        elif ftype == 'choice':
             color = curses.color_pair(5) | curses.A_BOLD
        
        TUI.safe_addstr(self.scr, y, x + left_w + 2, val_str[:width - left_w - 4], color)

    def refresh(self):
         # Override refresh to add header
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        list_h = min(len(self.items) + 2, h - 8)
        total_h = 2 + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        
        title_str = f"{self.title}{' *' if self.modified else ''}"
        TUI.safe_addstr(self.scr, start_y, (w - len(title_str)) // 2, title_str, curses.color_pair(1) | curses.A_BOLD)
        
        bw = min(self.box_width, w - 4)
        bx = (w - bw) // 2
        left_w = 26
        
        TUI.draw_box(self.scr, start_y + 2, bx, list_h, bw, self.box_title)
        
        # Header
        TUI.safe_addstr(self.scr, start_y + 3, bx + 4, "Setting", curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, start_y + 3, bx + left_w + 2, "Value", curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, start_y + 3, bx + left_w, "│", curses.color_pair(4) | curses.A_DIM)

        # Draw separator line below header?
        # Standard draw_box handles outline. list_h includes title row inside box?
        # Creating a fake separator line (horizontal)
        # for x_off in range(1, bw-1): 
        #      if x_off == left_w - 2: TUI.safe_addstr(self.scr, start_y + 4, bx + x_off, "┼", curses.color_pair(4) | curses.A_DIM)
        #      else: TUI.safe_addstr(self.scr, start_y + 4, bx + x_off, "─", curses.color_pair(4) | curses.A_DIM)

        vis = list_h - 3 # -1 for top border, -1 for bottom, -1 for header row?
        # Actually draw_box draws border. Inside is list_h-2 lines.
        # We used first line for Header. So start loop at 1.
        
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
        footer = 'Enter:Edit Space:Toggle Esc:Save x:Export l:Import'
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    def _handle_input(self, k):
        if super()._handle_input(k):
            return True
        
        item = self.items[self.cursor]
        key = item[0]
        if len(item) == 4: _, label, ftype, opts = item
        else: _, label, ftype = item

        if k in (ord('\n'), 10):
            if key == 'Preface':
                editor = TextEditor(self.scr, filepath=PREFACE_FILE, title='Preface Editor')
                editor.run()
            elif ftype == 'choice':
                val = self.config.get(key, opts[0])
                try: idx = opts.index(val)
                except: idx = 0
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
                val = self.config.get(key, "")
                new_val = LineEditor(self.scr, initial_value=str(val), title=f'Edit {label}').run()
                if new_val is not None:
                    if ftype == 'int':
                        try: self.config[key] = int(new_val)
                        except: pass
                    else:
                        self.config[key] = new_val
                    self.modified = True
            return True
        elif k == ord(' '):
            if ftype == 'bool':
                self.config[key] = not self.config.get(key, False)
                self.modified = True
            elif ftype == 'choice':
                val = self.config.get(key, opts[0])
                try: idx = opts.index(val)
                except: idx = 0
                idx = (idx + 1) % len(opts)
                self.config[key] = opts[idx]
                self.modified = True
            return True
        return False