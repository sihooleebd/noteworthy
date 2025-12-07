import curses
import json
import copy
from ..base import ListEditor, TUI
from ..components.common import LineEditor
from ...config import SCHEMES_FILE
from ...utils import load_config_safe, save_config
from .text import TextEditor

def extract_themes():
    try:
        schemes = json.loads(SCHEMES_FILE.read_text())
        return list(schemes.keys())
    except:
        return ['noteworthy-dark', 'noteworthy-light', 'rose-pine', 'nord', 'dracula', 'gruvbox']

def hex_to_curses_color(hex_color):
    if not hex_color or not hex_color.startswith('#'):
        return 4
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        if curses.COLORS < 256:
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if lum > 180:
                return 4
            if r > g and r > b:
                return 6
            if g > r and g > b:
                return 2
            if b > r and b > g:
                return 1
            if r > 150 and g > 100:
                return 3
            return 5
        best_idx = 16
        best_dist = 1000000
        levels = [0, 95, 135, 175, 215, 255]
        for ri, rv in enumerate(levels):
            for gi, gv in enumerate(levels):
                for bi, bv in enumerate(levels):
                    idx = 16 + 36 * ri + 6 * gi + bi
                    dist = (r - rv) ** 2 + (g - gv) ** 2 + (b - bv) ** 2
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = idx
        for i in range(24):
            val = 8 + 10 * i
            dist = (r - val) ** 2 + (g - val) ** 2 + (b - val) ** 2
            if dist < best_dist:
                best_dist = dist
                best_idx = 232 + i
        return best_idx
    except:
        return 4

class ThemeDetailEditor(ListEditor):

    def __init__(self, scr, schemes, theme_name):
        super().__init__(scr, f'THEME: {theme_name}')
        self.schemes = schemes
        self.theme_name = theme_name
        self.theme = self.schemes[self.theme_name]
        self._build_items()
        self.box_title = 'Properties'
        self.box_width = 70

    def _build_items(self):
        self.items = []
        for key in ['page-fill', 'text-main', 'text-heading', 'text-muted', 'text-accent']:
            self.items.append((key, self.theme.get(key, '')))
        for block, data in self.theme.get('blocks', {}).items():
            self.items.append((f'block.{block}.fill', data.get('fill', '')))
            self.items.append((f'block.{block}.stroke', data.get('stroke', '')))
        plot = self.theme.get('plot', {})
        for key in ['stroke', 'highlight', 'grid-opacity']:
            self.items.append((f'plot.{key}', str(plot.get(key, ''))))

    def _get_value(self, key):
        if key.startswith('block.'):
            parts = key.split('.')
            return self.theme.get('blocks', {}).get(parts[1], {}).get(parts[2], '')
        elif key.startswith('plot.'):
            parts = key.split('.')
            return str(self.theme.get('plot', {}).get(parts[1], ''))
        return self.theme.get(key, '')

    def _set_value(self, key, val):
        if key.startswith('block.'):
            parts = key.split('.')
            if 'blocks' not in self.theme:
                self.theme['blocks'] = {}
            if parts[1] not in self.theme['blocks']:
                self.theme['blocks'][parts[1]] = {}
            self.theme['blocks'][parts[1]][parts[2]] = val
        elif key.startswith('plot.'):
            parts = key.split('.')
            if 'plot' not in self.theme:
                self.theme['plot'] = {}
            if parts[1] == 'grid-opacity':
                try:
                    self.theme['plot'][parts[1]] = float(val)
                except:
                    self.theme['plot'][parts[1]] = val
            else:
                self.theme['plot'][parts[1]] = val
        else:
            self.theme[key] = val
        self.modified = True

    def _get_label(self, key):
        if key.startswith('block.'):
            parts = key.split('.')
            return f'{parts[1]}.{parts[2]}'
        elif key.startswith('plot.'):
            parts = key.split('.')
            return f'plot.{parts[1]}'
        return key

    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        list_h = min(len(self.items) + 3, h - 8)
        total_h = 3 + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        title_str = f"{self.title}{(' *' if self.modified else '')}"
        TUI.safe_addstr(self.scr, start_y, (w - len(title_str)) // 2, title_str, curses.color_pair(1) | curses.A_BOLD)
        bw = min(self.box_width, w - 4)
        bx = (w - bw) // 2
        left_w = 22
        TUI.draw_box(self.scr, start_y + 2, bx, list_h, bw, self.box_title)
        TUI.safe_addstr(self.scr, start_y + 3, bx + 4, 'Property', curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, start_y + 3, bx + left_w + 2, 'Color', curses.color_pair(1) | curses.A_BOLD)
        for i in range(1, list_h - 1):
            TUI.safe_addstr(self.scr, start_y + 2 + i, bx + left_w, '│', curses.color_pair(4) | curses.A_DIM)
        vis = list_h - 3
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis:
            self.scroll = self.cursor - vis + 1
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.items):
                break
            y = start_y + 4 + i
            self._draw_item(y, bx, self.items[idx], bw, idx == self.cursor)
        self._draw_footer(h, w)
        self.scr.refresh()

    def _draw_item(self, y, x, item, width, selected):
        key, _ = item
        left_w = 22
        if selected:
            TUI.safe_addstr(self.scr, y, x + 2, '>', curses.color_pair(3) | curses.A_BOLD)
        label = self._get_label(key)
        TUI.safe_addstr(self.scr, y, x + 4, label[:left_w - 6], curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0))
        hex_val = self._get_value(key)
        color = hex_to_curses_color(hex_val)
        TUI.safe_addstr(self.scr, y, x + left_w + 2, '██', curses.color_pair(color))
        TUI.safe_addstr(self.scr, y, x + left_w + 5, hex_val[:width - left_w - 8], curses.color_pair(4) | (curses.A_BOLD if selected else 0))

    def _draw_footer(self, h, w):
        footer = 'Enter: Edit  Esc: Back (Auto-saves)'
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    def _handle_input(self, k):
        if super()._handle_input(k):
            return True
        if k in (ord('\n'), 10):
            key, _ = self.items[self.cursor]
            curr_val = self._get_value(key)
            new_val = LineEditor(self.scr, initial_value=curr_val, title='Edit Color').run()
            if new_val is not None:
                self._set_value(key, new_val)
                self._build_items()
            return True
        return False

class SchemeEditor(ListEditor):

    def __init__(self, scr):
        super().__init__(scr, 'SCHEME MANAGER')
        self.filepath = SCHEMES_FILE
        self.schemes = self._load_schemes()
        self.config = load_config_safe()
        self._build_items()
        self.box_title = 'Available Schemes'
        self.box_width = 70

    def _load_schemes(self):
        return json.loads(SCHEMES_FILE.read_text())

    def _build_items(self):
        self.items = sorted(list(self.schemes.keys())) + ['+ Add new scheme...']

    def save(self):
        try:
            SCHEMES_FILE.write_text(json.dumps(self.schemes, indent=4))
            self.modified = False
            return True
        except:
            return False

    def _create_new(self):
        name = LineEditor(self.scr, title='New Scheme Name', initial_value='new-scheme').run()
        if name and name not in self.schemes:
            blank_scheme = {
                "page-fill": "#ffffff",
                "text-main": "#000000",
                "text-heading": "#000000",
                "text-muted": "#000000",
                "text-accent": "#000000",
                "blocks": {},
                "plot": {
                    "stroke": "#000000",
                    "highlight": "#000000",
                    "grid-opacity": 0.15
                }
            }
            for b in ['definition', 'equation', 'example', 'solution', 'proof', 'note', 'notation', 'analysis', 'theorem']:
                blank_scheme['blocks'][b] = {
                    "fill": "#ffffff",
                    "stroke": "#000000",
                    "title": b.title()
                }
            self.schemes[name] = blank_scheme
            self._build_items()
            self.modified = True
            try:
                self.cursor = self.items.index(name)
            except:
                pass

    def _delete_current(self):
        if not self.items:
            return
        name = self.items[self.cursor]
        if name == '+ Add new scheme...':
            return
        if len(self.items) > 2:
            del self.schemes[name]
            self._build_items()
            self.modified = True
            self.cursor = min(self.cursor, len(self.items) - 1)

    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        list_h = min(len(self.items) + 2, h - 8)
        total_h = 2 + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        title_str = f"{self.title}{(' *' if self.modified else '')}"
        TUI.safe_addstr(self.scr, start_y, (w - len(title_str)) // 2, title_str, curses.color_pair(1) | curses.A_BOLD)
        bw = min(self.box_width, w - 4)
        bx = (w - bw) // 2
        TUI.draw_box(self.scr, start_y + 2, bx, list_h, bw, self.box_title)
        vis = list_h - 2
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis:
            self.scroll = self.cursor - vis + 1
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.items):
                break
            y = start_y + 3 + i
            self._draw_item(y, bx, self.items[idx], bw, idx == self.cursor)
        self._draw_footer(h, w)
        self.scr.refresh()

    def _draw_item(self, y, x, item, width, selected):
        name = item
        if name == '+ Add new scheme...':
            TUI.safe_addstr(self.scr, y, x + 4, name, curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else curses.A_DIM))
            if selected:
                TUI.safe_addstr(self.scr, y, x + 2, '>', curses.color_pair(3) | curses.A_BOLD)
            return
        is_active = self.config.get('display-mode') == name
        if selected:
            TUI.safe_addstr(self.scr, y, x + 2, '>', curses.color_pair(3) | curses.A_BOLD)
        attr = curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0)
        TUI.safe_addstr(self.scr, y, x + 4, name[:width - 25], attr)
        if is_active:
            TUI.safe_addstr(self.scr, y, x + width - 12, '(ACTIVE)', curses.color_pair(2) | curses.A_BOLD)

    def _draw_footer(self, h, w):
        footer = 'Enter:Edit Space:Select n:New d:Del Esc:Save x:Export l:Import'
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    def _handle_input(self, k):
        if super()._handle_input(k):
            return True
        if k in (ord('\n'), 10):
            if self.items:
                name = self.items[self.cursor]
                if name == '+ Add new scheme...':
                    self._create_new()
                else:
                    editor = ThemeDetailEditor(self.scr, self.schemes, name)
                    editor.run()
                    if editor.modified:
                        self.modified = True
            return True
        elif k == ord(' '):
            if self.items:
                name = self.items[self.cursor]
                if name != '+ Add new scheme...':
                    self.config['display-mode'] = name
                    save_config(self.config)
            return True
        elif k == ord('n'):
            self._create_new()
            return True
        elif k == ord('d'):
            if TUI.prompt_confirm(self.scr, 'Delete scheme? (y/n): '):
                self._delete_current()
            return True
        return False