
import curses
import json
from pathlib import Path
from ..base import ListEditor, TUI, LEFT_PAD
from ..components.common import LineEditor
from ...config import BASE_DIR
from ...utils import register_key
from ..keybinds import KeyBind, NavigationBind

MODULES_CONFIG_DIR = BASE_DIR / 'config/modules'

class BlueprintEditor(ListEditor):
    """
    Editor for module configuration based on a blueprint.json schema.
    Reads schema from: templates/module/<name>/blueprint.json (or passed path)
    Reads/Writes values to: config/modules/<name>.json
    """
    def __init__(self, scr, module_name, blueprint_path):
        super().__init__(scr, f"{module_name.title()} Settings")
        self.module_name = module_name
        self.blueprint_path = Path(blueprint_path)
        self.config_path = MODULES_CONFIG_DIR / f"{module_name}.json"
        
        self.blueprint = {}
        self.config = {}
        
        self._load()
        
        
        # Explicit registration to fix navigation
        register_key(self.keymap, NavigationBind('UP', self.cursor_up))
        register_key(self.keymap, NavigationBind('DOWN', self.cursor_down))
        
        register_key(self.keymap, KeyBind(ord(' '), self.action_toggle, "Toggle"))
        register_key(self.keymap, KeyBind(ord('\n'), self.action_edit, "Edit"))
        register_key(self.keymap, KeyBind(curses.KEY_ENTER, self.action_edit, "Edit"))
        register_key(self.keymap, KeyBind(curses.KEY_RIGHT, self.action_next_value))
        register_key(self.keymap, KeyBind(curses.KEY_LEFT, self.action_prev_value))

    def _load(self):
        # Load Blueprint
        if self.blueprint_path.exists():
            try:
                self.blueprint = json.loads(self.blueprint_path.read_text())
            except:
                self.blueprint = {"settings": []}
        
        # Load User Config
        if self.config_path.exists():
            try:
                self.config = json.loads(self.config_path.read_text())
            except:
                self.config = {}
        
        self._build_items()

    def _build_items(self):
        self.items = []
        settings = self.blueprint.get("settings", [])
        
        for setting in settings:
            key = setting.get("key")
            if not key: continue
            
            label = setting.get("label", key.replace("_", " ").title())
            stype = setting.get("type", "string") # string, int, bool, choice
            default = setting.get("default")
            options = setting.get("options", [])
            
            self.items.append({
                "key": key,
                "label": label,
                "type": stype,
                "default": default,
                "options": options
            })

    def get_value(self, item):
        return self.config.get(item["key"], item["default"])

    def set_value(self, item, value):
        self.config[item["key"]] = value
        self.modified = True

    def _draw_item(self, y, x, item, width, selected):
        label = item["label"]
        stype = item["type"]
        val = self.get_value(item)
        
        label_w = 24
        
        # Selection indicator
        if selected:
            TUI.safe_addstr(self.scr, y, x, '▶', curses.color_pair(3) | curses.A_BOLD)
        
        # Label
        style = curses.color_pair(5 if selected else 4) | (curses.A_BOLD if selected else 0)
        TUI.safe_addstr(self.scr, y, x + 2, label[:label_w - 4], style)
        
        # Value
        val_str = str(val) if val is not None else "(none)"
        color = curses.color_pair(4)
        if selected:
            color |= curses.A_BOLD

        if stype == 'bool':
            val_str = 'Yes' if val else 'No'
            color = curses.color_pair(2 if val else 6)
            if selected:
                color |= curses.A_BOLD
        elif stype == 'list':
            val_str = ', '.join(val) if isinstance(val, list) else str(val)
        elif stype == 'choice':
            if selected:
                color = curses.color_pair(5) | curses.A_BOLD
        
        TUI.safe_addstr(self.scr, y, x + label_w, val_str[:width - label_w - 2], color)

    def action_edit(self, ctx):
        item = self.items[self.cursor]
        stype = item["type"]
        key = item["key"]
        val = self.get_value(item)
        
        if stype == 'bool':
            self.set_value(item, not val)
        elif stype == 'choice':
            opts = item["options"]
            if opts:
                try:
                    idx = opts.index(val)
                except:
                    idx = 0
                idx = (idx + 1) % len(opts)
                self.set_value(item, opts[idx])
        elif stype == 'int':
            init_val = str(val if val is not None else "")
            new_val = LineEditor(self.scr, initial_value=init_val, title=f'Edit {item["label"]}').run()
            if new_val is not None:
                try:
                    self.set_value(item, int(new_val))
                except:
                    pass
        else:
            init_val = str(val if val is not None else "")
            new_val = LineEditor(self.scr, initial_value=init_val, title=f'Edit {item["label"]}').run()
            if new_val is not None:
                self.set_value(item, new_val)

    def action_toggle(self, ctx):
        item = self.items[self.cursor]
        if item["type"] == 'bool':
            self.set_value(item, not self.get_value(item))
        elif item["type"] == 'choice':
             self.action_next_value(ctx)

    def action_next_value(self, ctx):
        item = self.items[self.cursor]
        if item["type"] == 'choice':
            opts = item["options"]
            if opts:
                val = self.get_value(item)
                try:
                    idx = opts.index(val)
                except:
                    idx = 0
                idx = (idx + 1) % len(opts)
                self.set_value(item, opts[idx])

    def action_prev_value(self, ctx):
        item = self.items[self.cursor]
        if item["type"] == 'choice':
            opts = item["options"]
            if opts:
                val = self.get_value(item)
                try:
                    idx = opts.index(val)
                except:
                    idx = 0
                idx = (idx - 1 + len(opts)) % len(opts)
                self.set_value(item, opts[idx])

    def save(self):
        if self.modified:
            MODULES_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(json.dumps(self.config, indent=4))
        return True
