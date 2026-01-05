import curses
import json
from pathlib import Path
from ..base import TUI, LEFT_PAD, TOP_PAD
from ...config import METADATA_FILE, CONSTANTS_FILE, MODULES_CONFIG_FILE
from ...assets import LOGO
from ...utils import load_config_safe, save_config, register_key, handle_key_event
from ..editors.schemes import extract_themes
from ..keybinds import KeyBind, NavigationBind, ConfirmBind


# Core modules that are always enabled - don't show in selection
CORE_MODULES = {'block', 'cover'}


def get_available_modules():
    """Scan local modules and fetch remote modules from GitHub."""
    from ...core.pm import fetch_index
    
    modules = {}
    module_dir = Path("templates/module")
    
    # First, scan local modules
    if module_dir.exists():
        for d in sorted(module_dir.iterdir()):
            if d.is_dir() and not d.name.startswith('.') and d.name != 'core':
                meta_path = d / "metadata.json"
                if meta_path.exists():
                    try:
                        meta = json.loads(meta_path.read_text())
                        modules[d.name] = {
                            "name": d.name,
                            "description": meta.get("description", ""),
                            "dependencies": meta.get("dependencies", []),
                            "source": "local"
                        }
                    except:
                        modules[d.name] = {
                            "name": d.name,
                            "description": "",
                            "dependencies": [],
                            "source": "local"
                        }
                else:
                    modules[d.name] = {
                        "name": d.name,
                        "description": "",
                        "dependencies": [],
                        "source": "local"
                    }
    
    # Then fetch remote modules and merge (remote fills in missing)
    try:
        remote = fetch_index()
        for name, data in remote.items():
            # Skip core modules - they're always enabled
            if name in CORE_MODULES:
                continue
            if name not in modules:
                modules[name] = {
                    "name": name,
                    "description": data.get("description", ""),
                    "dependencies": data.get("dependencies", []),
                    "source": "remote"
                }
    except:
        pass  # Offline
    
    return sorted(modules.values(), key=lambda m: m['name'])


class InitWizard:
    """Setup wizard with left-aligned design."""

    def __init__(self, scr):
        self.scr = scr
        themes = extract_themes()
        self.config = {
            'title': '', 'subtitle': '', 'authors': [], 'affiliation': '',
            'show-solution': True, 'chapter-name': 'Chapter', 'subchap-name': 'Section',
            'font': 'IBM Plex Serif', 'title-font': 'Noto Sans Adlam',
            'display-cover': True, 'display-outline': True, 'display-chap-cover': True,
            'display-mode': 'rose-pine'
        }
        
        self.steps = [
            ('title', 'Document Title', 'Enter the main title:', 'str'),
            ('subtitle', 'Subtitle', 'Enter a subtitle (optional):', 'str'),
            ('authors', 'Authors', 'Enter author names (comma-separated):', 'list'),
            ('affiliation', 'Affiliation', 'Enter your organization:', 'str'),
            ('display-mode', 'Color Theme', 'Select theme:', 'choice', themes),
            ('font', 'Body Font', 'Enter body font name:', 'str'),
            ('chapter-name', 'Chapter Label', "What to call chapters:", 'str'),
        ]
        
        self.current_step = 0
        self.choice_index = 0
        self.input_value = ""
        
        # Module selection
        self.available_modules = get_available_modules()
        self.selected_modules = {m['name']: False for m in self.available_modules}  # All unchecked by default
        self.module_cursor = 0
        self.module_scroll = 0
        self.in_module_step = False
        
        TUI.init_colors()
        
        # Load existing config
        try:
            current = load_config_safe()
            if current:
                self.config.update(current)
        except:
            pass
        
        self.keymap = {}
        register_key(self.keymap, KeyBind(27, self.action_cancel, "Cancel"))
        register_key(self.keymap, ConfirmBind(self.action_next))
        register_key(self.keymap, NavigationBind('LEFT', self.action_choice_left))
        register_key(self.keymap, NavigationBind('RIGHT', self.action_choice_right))
        register_key(self.keymap, NavigationBind('UP', self.action_up))
        register_key(self.keymap, NavigationBind('DOWN', self.action_down))

    def action_cancel(self, ctx):
        return 'EXIT'

    def action_up(self, ctx):
        if self.in_module_step:
            self.module_cursor = max(0, self.module_cursor - 1)

    def action_down(self, ctx):
        if self.in_module_step:
            self.module_cursor = min(len(self.available_modules) - 1, self.module_cursor + 1)

    def action_choice_left(self, ctx):
        step = self.steps[self.current_step]
        if step[3] == 'choice':
            choices = step[4]
            self.choice_index = (self.choice_index - 1) % len(choices)

    def action_choice_right(self, ctx):
        step = self.steps[self.current_step]
        if step[3] == 'choice':
            choices = step[4]
            self.choice_index = (self.choice_index + 1) % len(choices)

    def action_next(self, ctx):
        if self.in_module_step:
            return 'FINISH_MODULES'
        
        step = self.steps[self.current_step]
        key, stype = step[0], step[3]
        
        if stype == 'choice':
            choices = step[4]
            self.config[key] = choices[self.choice_index]
            self.current_step += 1
            self.choice_index = 0
        else:
            value = self.get_input()
            if value or key != 'title':
                if stype == 'list':
                    self.config[key] = [s.strip() for s in value.split(',') if s.strip()] if value else []
                else:
                    self.config[key] = value if value else self.config.get(key, '')
                self.current_step += 1
            elif not value and key == 'title':
                h, w = self.scr.getmaxyx()
                TUI.safe_addstr(self.scr, h - 3, LEFT_PAD, 'Title is required!', curses.color_pair(6) | curses.A_BOLD)
                self.scr.refresh()
                curses.napms(1000)

    def refresh_config_step(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        y = TOP_PAD
        
        # Logo
        for i, line in enumerate(LOGO[:min(len(LOGO), 8)]):
            TUI.safe_addstr(self.scr, y + i, LEFT_PAD, line, curses.color_pair(1) | curses.A_BOLD)
        
        y += len(LOGO[:8]) + 1
        TUI.safe_addstr(self.scr, y, LEFT_PAD, 'Setup Wizard', curses.color_pair(1) | curses.A_BOLD)
        y += 2
        
        step = self.steps[self.current_step]
        key, label, prompt, stype = step[0], step[1], step[2], step[3]
        
        TUI.safe_addstr(self.scr, y, LEFT_PAD, f'Step {self.current_step + 1}/{len(self.steps)}: {label}', 
                       curses.color_pair(5) | curses.A_BOLD)
        y += 1
        TUI.safe_addstr(self.scr, y, LEFT_PAD, prompt, curses.color_pair(4))
        y += 2
        
        if stype == 'choice':
            choices = step[4]
            choice_text = f'◀  {choices[self.choice_index]}  ▶'
            TUI.safe_addstr(self.scr, y, LEFT_PAD, choice_text, curses.color_pair(5) | curses.A_BOLD)
            y += 1
            TUI.safe_addstr(self.scr, y + 1, LEFT_PAD, '←→ Select  Enter Confirm', curses.color_pair(4) | curses.A_DIM)
        else:
            curr_val = self.config.get(key, '')
            if isinstance(curr_val, list):
                curr_val = ', '.join(curr_val)
            if curr_val:
                TUI.safe_addstr(self.scr, y, LEFT_PAD, f'Current: {str(curr_val)[:50]}', curses.color_pair(4) | curses.A_DIM)
            self.input_y = y + 2
        
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, 'Enter Continue  Esc Cancel', curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()

    def refresh_module_step(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        y = TOP_PAD
        TUI.safe_addstr(self.scr, y, LEFT_PAD, 'Select Modules', curses.color_pair(1) | curses.A_BOLD)
        y += 1
        TUI.safe_addstr(self.scr, y, LEFT_PAD, 'Space to toggle, Enter to finish (☁ = remote)', curses.color_pair(4) | curses.A_DIM)
        y += 2
        
        TUI.safe_addstr(self.scr, y, LEFT_PAD, 'Core modules (always enabled):', curses.color_pair(4) | curses.A_DIM)
        y += 1
        TUI.safe_addstr(self.scr, y, LEFT_PAD + 2, '• block - Semantic content blocks', curses.color_pair(4))
        y += 1
        TUI.safe_addstr(self.scr, y, LEFT_PAD + 2, '• cover - Document covers', curses.color_pair(4))
        y += 2
        
        TUI.safe_addstr(self.scr, y, LEFT_PAD, 'Optional modules:', curses.color_pair(4) | curses.A_DIM)
        y += 1
        
        visible = h - y - 4
        if self.module_cursor < self.module_scroll:
            self.module_scroll = self.module_cursor
        elif self.module_cursor >= self.module_scroll + visible:
            self.module_scroll = self.module_cursor - visible + 1
        
        for i in range(visible):
            idx = self.module_scroll + i
            if idx >= len(self.available_modules):
                break
            
            mod = self.available_modules[idx]
            is_selected = self.selected_modules.get(mod['name'], False)
            is_cursor = idx == self.module_cursor
            is_remote = mod.get('source') == 'remote'
            
            if is_cursor:
                TUI.safe_addstr(self.scr, y + i, LEFT_PAD, '▶', curses.color_pair(3) | curses.A_BOLD)
            
            cb = '[✓]' if is_selected else '[ ]'
            cb_color = curses.color_pair(2 if is_selected else 4)
            TUI.safe_addstr(self.scr, y + i, LEFT_PAD + 2, cb, cb_color)
            
            # Show LC/RM tag with highlighting
            tag = 'RM' if is_remote else 'LC'
            tag_color = curses.color_pair(5) if is_remote else curses.color_pair(2)
            TUI.safe_addstr(self.scr, y + i, LEFT_PAD + 6, tag, tag_color | curses.A_BOLD)
            
            name_style = curses.color_pair(4) | (curses.A_BOLD if is_cursor else 0)
            TUI.safe_addstr(self.scr, y + i, LEFT_PAD + 9, mod['name'][:15], name_style)
            
            if mod['description']:
                TUI.safe_addstr(self.scr, y + i, LEFT_PAD + 25, mod['description'][:w - LEFT_PAD - 28], 
                               curses.color_pair(4) | curses.A_DIM)
        
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, 'Space Toggle  Enter Finish  Esc Cancel', curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()

    def get_input(self):
        curses.echo()
        curses.curs_set(1)
        h, w = self.scr.getmaxyx()
        y = self.input_y if hasattr(self, 'input_y') else TOP_PAD + 12
        
        TUI.safe_addstr(self.scr, y, LEFT_PAD, '> ', curses.color_pair(3) | curses.A_BOLD)
        self.scr.refresh()
        
        try:
            value = self.scr.getstr(y, LEFT_PAD + 2, 50).decode('utf-8').strip()
        except:
            value = ''
        
        curses.noecho()
        curses.curs_set(0)
        return value

    def _enable_dependencies(self, mod_name):
        """Enable all dependencies for a module."""
        for mod in self.available_modules:
            if mod['name'] == mod_name:
                for dep in mod.get('dependencies', []):
                    self.selected_modules[dep] = True
                    self._enable_dependencies(dep)  # Recursive
                break

    def _save_module_config(self):
        """Save selected modules to config."""
        modules = {}
        for mod in self.available_modules:
            name = mod['name']
            source = mod.get('source', 'local')
            if self.selected_modules.get(name, False):
                modules[name] = {"status": "global", "source": source}
            else:
                modules[name] = {"status": "disabled", "source": source}
        
        MODULES_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        config = {"modules": modules, "meta": {}}
        MODULES_CONFIG_FILE.write_text(json.dumps(config, indent=4))

    def run(self):
        # Welcome screen
        while True:
            if not TUI.check_terminal_size(self.scr):
                return None
            h, w = self.scr.getmaxyx()
            self.scr.clear()
            
            y = TOP_PAD
            for i, line in enumerate(LOGO):
                TUI.safe_addstr(self.scr, y + i, LEFT_PAD, line, curses.color_pair(1) | curses.A_BOLD)
            
            y += len(LOGO) + 2
            TUI.safe_addstr(self.scr, y, LEFT_PAD, 'Welcome to Noteworthy!', curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, y + 2, LEFT_PAD, 'Press Enter to begin setup...', curses.color_pair(4) | curses.A_DIM)
            
            self.scr.refresh()
            k = self.scr.getch()
            if k == 27:
                return None
            if k in (ord('\n'), 10, curses.KEY_ENTER):
                break
        
        # Config steps
        while self.current_step < len(self.steps):
            if not TUI.check_terminal_size(self.scr):
                return None
            
            self.refresh_config_step()
            k = self.scr.getch()
            
            handled, res = handle_key_event(k, self.keymap, self)
            if handled and res == 'EXIT':
                return None
        
        # Module selection step
        self.in_module_step = True
        while True:
            if not TUI.check_terminal_size(self.scr):
                return None
            
            self.refresh_module_step()
            k = self.scr.getch()
            
            if k == 27:
                return None
            elif k == ord(' '):
                mod = self.available_modules[self.module_cursor]
                name = mod['name']
                new_state = not self.selected_modules.get(name, False)
                self.selected_modules[name] = new_state
                if new_state:
                    self._enable_dependencies(name)
            elif k in (curses.KEY_UP, ord('k')):
                self.module_cursor = max(0, self.module_cursor - 1)
            elif k in (curses.KEY_DOWN, ord('j')):
                self.module_cursor = min(len(self.available_modules) - 1, self.module_cursor + 1)
            elif k in (ord('\n'), 10, curses.KEY_ENTER):
                break
        
        # Save everything
        try:
            METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            save_config(self.config)
            self._save_module_config()
            return True
        except:
            return None