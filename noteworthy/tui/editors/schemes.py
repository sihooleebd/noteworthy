import curses
import json
from ..base import ListEditor, TUI, LEFT_PAD, TOP_PAD
from ..components.common import LineEditor
from ...config import SCHEMES_DIR
from ...utils import load_config_safe, save_config, register_key
from ..keybinds import ConfirmBind, KeyBind, NavigationBind


def extract_themes():
    """Extract theme names from the schemes folder."""
    try:
        data_dir = SCHEMES_DIR / 'data'
        if not data_dir.exists():
            return []
        return [f.stem for f in sorted(data_dir.glob('*.json'))]
    except:
        return []


def load_all_schemes():
    """Load all schemes from individual files."""
    schemes = {}
    data_dir = SCHEMES_DIR / 'data'
    if data_dir.exists():
        for f in sorted(data_dir.glob('*.json')):
            try:
                schemes[f.stem] = json.loads(f.read_text())
            except:
                pass
    return schemes


def save_scheme(name, scheme_data):
    """Save a single scheme to its individual file."""
    data_dir = SCHEMES_DIR / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / f'{name}.json'
    target.write_text(json.dumps(scheme_data, indent=4))


def delete_scheme_file(name):
    """Delete a scheme file."""
    target = SCHEMES_DIR / 'data' / f'{name}.json'
    if target.exists():
        target.unlink()


def hex_to_curses_color(hex_color):
    """Convert hex color to curses color pair index."""
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
    """Theme detail editor with left-aligned design."""

    def __init__(self, scr, schemes, theme_name):
        super().__init__(scr, f'Theme: {theme_name}')
        self.schemes = schemes
        self.theme_name = theme_name
        self.theme = self.schemes[self.theme_name]
        self._build_items()
        self.section_title = 'Colors'
        
        # Explicitly register navigation keys to resolve issue
        register_key(self.keymap, KeyBind(curses.KEY_LEFT, self.do_exit, "Back"))
        self.section_title = 'Colors'

    def save(self):
        save_scheme(self.theme_name, self.theme)
        return True

    def action_select(self, ctx):
        key, _ = self.items[self.cursor]
        curr_val = self._get_value(key)
        new_val = LineEditor(self.scr, initial_value=curr_val, title='Edit Color').run()
        if new_val is not None:
            self._set_value(key, new_val)
            self._build_items()

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
            return key
        return key

    def _draw_item(self, y, x, item, width, selected):
        key, _ = item
        
        if selected:
            TUI.safe_addstr(self.scr, y, x, '▶', curses.color_pair(3) | curses.A_BOLD)
        
        label = self._get_label(key)
        hex_val = self._get_value(key)
        color = hex_to_curses_color(hex_val)
        
        style = curses.color_pair(4) | (curses.A_BOLD if selected else 0)
        TUI.safe_addstr(self.scr, y, x + 2, label[:20], style)
        TUI.safe_addstr(self.scr, y, x + 24, '██', curses.color_pair(color))
        TUI.safe_addstr(self.scr, y, x + 27, hex_val[:width - 30], curses.color_pair(4) | curses.A_DIM)

    def _draw_footer(self, h, w):
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, 'Enter Edit  Esc Save', curses.color_pair(4) | curses.A_DIM)


class SchemeEditor(ListEditor):
    """Scheme editor with left-aligned design."""

    def __init__(self, scr):
        super().__init__(scr, 'Color Themes')
        self.schemes = load_all_schemes()
        self.config = load_config_safe()
        self._build_items()
        self.section_title = 'Available Themes'
        
        register_key(self.keymap, ConfirmBind(self.action_select))
        register_key(self.keymap, KeyBind(ord('n'), self._create_new))
        register_key(self.keymap, KeyBind(ord('d'), self._delete_current_prompt))
        register_key(self.keymap, KeyBind(ord(' '), self.action_set_active))
        
    def action_select(self, ctx):
        if self.items:
            name = self.items[self.cursor]
            if name == '+ Add theme...':
                self._create_new()
            else:
                editor = ThemeDetailEditor(self.scr, self.schemes, name)
                editor.run()
                if editor.modified:
                    self.modified = True

    def action_set_active(self, ctx):
        if self.items:
            name = self.items[self.cursor]
            if name != '+ Add theme...':
                self.config['display-mode'] = name
                save_config(self.config)

    def _load(self):
        self.schemes = load_all_schemes()
        self._build_items()
        self.cursor = min(self.cursor, max(0, len(self.items) - 1))

    def _build_items(self):
        self.items = sorted(list(self.schemes.keys())) + ['+ Add theme...']

    def save(self):
        for name, scheme_data in self.schemes.items():
            save_scheme(name, scheme_data)
        self.modified = False
        return True

    def _create_new(self):
        name = LineEditor(self.scr, title='New Theme Name', initial_value='new-theme').run()
        if name and name not in self.schemes:
            blank_scheme = {
                "page-fill": "#ffffff",
                "text-main": "#000000",
                "text-heading": "#000000",
                "text-muted": "#666666",
                "text-accent": "#0066cc",
                "blocks": {},
                "plot": {"stroke": "#000000", "highlight": "#0066cc", "grid-opacity": 0.15}
            }
            for b in ['definition', 'theorem', 'example', 'proof', 'note']:
                blank_scheme['blocks'][b] = {"fill": "#f5f5f5", "stroke": "#cccccc", "title": b.title()}
            self.schemes[name] = blank_scheme
            save_scheme(name, blank_scheme)
            self._build_items()
            self.modified = True
            try:
                self.cursor = self.items.index(name)
            except:
                pass

    def _delete_current(self):
        if not self.items or len(self.items) <= 2:
            return
        name = self.items[self.cursor]
        if name == '+ Add theme...':
            return
        
        if self.config.get('display-mode') == name:
            real_themes = [t for t in self.items if t not in ('+ Add theme...', name)]
            if real_themes:
                self.config['display-mode'] = real_themes[0]
                save_config(self.config)
        
        del self.schemes[name]
        delete_scheme_file(name)
        self._build_items()
        self.modified = True
        self.cursor = min(self.cursor, len(self.items) - 1)

    def _delete_current_prompt(self, ctx):
        if TUI.prompt_confirm(self.scr, 'Delete theme?'):
            self._delete_current()

    def _draw_item(self, y, x, item, width, selected):
        name = item
        
        if selected:
            TUI.safe_addstr(self.scr, y, x, '▶', curses.color_pair(3) | curses.A_BOLD)
        
        if name == '+ Add theme...':
            style = curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else curses.A_DIM)
            TUI.safe_addstr(self.scr, y, x + 2, name, style)
            return
        
        is_active = self.config.get('display-mode') == name
        style = curses.color_pair(4) | (curses.A_BOLD if selected else 0)
        TUI.safe_addstr(self.scr, y, x + 2, name[:width - 15], style)
        
        if is_active:
            TUI.safe_addstr(self.scr, y, x + width - 10, '(active)', curses.color_pair(2) | curses.A_BOLD)

    def _draw_footer(self, h, w):
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, 'Enter Edit  Space Active  n New  d Delete  Esc Save', 
                       curses.color_pair(4) | curses.A_DIM)