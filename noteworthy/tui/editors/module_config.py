import curses
import json
import shutil
from pathlib import Path
from ..base import ListEditor, TUI, LEFT_PAD, TOP_PAD
from ...core.pm import get_installed_modules, save_modules_config, create_custom_module, check_dependencies, get_latest_commit_sha, get_commit_log, get_modules_meta, save_modules_meta, download_modules
from ...core.modules import generate_imports_file, get_module_conflicts
from ..components.common import LineEditor
from ...utils import register_key
from ..keybinds import KeyBind

STANDARD_MODULES = {
    'layout', 'trees', 'shape', 'data', 'graph', 'block', 
    'canvas', 'dsa', 'cover', 'combi'
}


class ModuleConfigEditor(ListEditor):
    """Module configuration editor with left-aligned design."""
    
    def __init__(self, scr):
        super().__init__(scr, "Module Configuration")
        self.modules = get_installed_modules()
        self.meta = get_modules_meta()
        self.remote_index = {}
        self._build_local_index()
        self.section_title = "Modules"
        self._build_items()
        self.modified = False
        
        register_key(self.keymap, KeyBind(ord(' '), self.action_space, "Toggle Status"))
        register_key(self.keymap, KeyBind(ord('\n'), self.action_enter, "Action"))
        register_key(self.keymap, KeyBind(curses.KEY_ENTER, self.action_enter, "Action"))
        
        self._check_for_updates()
        
    def _check_for_updates(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, "Checking for updates...", curses.color_pair(4))
        self.scr.refresh()
        
        latest_sha = get_latest_commit_sha()
        current_sha = self.meta.get("commit")
        
        if latest_sha and latest_sha != current_sha:
            if TUI.prompt_confirm(self.scr, "Updates available. Update now?"):
                self.meta["commit"] = latest_sha
                save_modules_meta(self.meta)
                
                to_update = [name for name, state in self.modules.items() 
                            if state.get("status") != "disabled" and state.get("source") == "remote"]
                
                if to_update:
                    def progress_cb(m):
                        self.scr.clear()
                        TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, "Updating Modules", curses.color_pair(1) | curses.A_BOLD)
                        TUI.safe_addstr(self.scr, TOP_PAD + 2, LEFT_PAD, m[:60], curses.color_pair(4))
                        self.scr.refresh()
                    download_modules(to_update, progress_cb)
                    TUI.show_message(self.scr, "Success", "Modules updated!")

    def _build_local_index(self):
        self.index = {}
        root = Path("templates/module")
        if root.exists():
            for d in root.iterdir():
                if d.is_dir():
                    meta_path = d / "metadata.json"
                    if meta_path.exists():
                        try:
                            self.index[d.name] = json.loads(meta_path.read_text())
                        except:
                            pass
                    else:
                        self.index[d.name] = {"name": d.name, "dependencies": []}

    def _build_items(self):
        self.items = []
        all_keys = set(self.modules.keys()) | set(self.index.keys())
        standard = sorted([k for k in all_keys if k in STANDARD_MODULES])
        custom = sorted([k for k in all_keys if k not in STANDARD_MODULES])
        
        for name in standard:
            state = self.modules.get(name, {"status": "disabled", "source": "local"})
            self.items.append((name, state, False, False))
            
        if custom:
            self.items.append(("", None, False, False))
            for name in custom:
                state = self.modules.get(name, {"status": "disabled", "source": "local"})
                self.items.append((name, state, True, False))
                
        self.items.append(("+ Create Custom Module...", None, False, True))
            
    def _get_status_str(self, state):
        if not state:
            return ""
        s = state.get("status", "disabled")
        if s == "global":
            return "Global"
        if s == "qualified":
            return "Qualified"
        return "Disabled"

    def refresh(self):
        conflicts = get_module_conflicts()
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        # Title
        title = f"{self.title}{' *' if self.modified else ''}"
        TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, title, curses.color_pair(1) | curses.A_BOLD)
        
        # Section header
        TUI.safe_addstr(self.scr, TOP_PAD + 2, LEFT_PAD, self.section_title, curses.color_pair(4) | curses.A_DIM)
        
        # Items
        list_y = TOP_PAD + 3
        visible = h - list_y - 4
        
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + visible:
            self.scroll = self.cursor - visible + 1
        
        for i in range(visible):
            idx = self.scroll + i
            if idx >= len(self.items):
                break
            
            name, state, is_custom, is_action = self.items[idx]
            y = list_y + i
            
            if name == "" and state is None:
                TUI.safe_addstr(self.scr, y, LEFT_PAD, "─" * 50, curses.color_pair(4) | curses.A_DIM)
                continue
            
            selected = idx == self.cursor
            
            if selected:
                TUI.safe_addstr(self.scr, y, LEFT_PAD, "▶", curses.color_pair(3) | curses.A_BOLD)
            
            if is_action:
                style = curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else 0)
                TUI.safe_addstr(self.scr, y, LEFT_PAD + 2, name, style)
            else:
                style = curses.color_pair(4) | (curses.A_BOLD if selected else 0)
                TUI.safe_addstr(self.scr, y, LEFT_PAD + 2, name[:30], style)
                
                status_str = self._get_status_str(state)
                if state.get("status") == "global":
                    status_style = curses.color_pair(2) | curses.A_BOLD
                elif state.get("status") == "qualified":
                    status_style = curses.color_pair(5)
                else:
                    status_style = curses.color_pair(4) | curses.A_DIM
                
                TUI.safe_addstr(self.scr, y, LEFT_PAD + 35, status_str, status_style)
        
        # Conflicts warning
        if conflicts:
            TUI.safe_addstr(self.scr, h - 3, LEFT_PAD, f"⚠ {len(conflicts)} symbol conflicts!", 
                           curses.color_pair(3) | curses.A_BOLD)
        
        # Footer
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, "Space Toggle  Enter Action  Esc Save", 
                       curses.color_pair(4) | curses.A_DIM)
        
        self.scr.refresh()

    def action_space(self, ctx):
        name, state, is_custom, is_action = self.items[self.cursor]
        if is_action or not state:
            return
        
        curr = state.get("status", "disabled")
        nxt = "disabled"
        if curr == "disabled":
            nxt = "qualified"
        elif curr == "qualified":
            nxt = "global"
        elif curr == "global":
            nxt = "disabled"
        
        if nxt != "disabled":
            missing = check_dependencies(name, self.index, self._get_enabled_modules())
            if missing:
                if TUI.prompt_confirm(self.scr, f"Enable dependencies: {', '.join(missing)}?"):
                    for m in missing:
                        if m not in self.modules:
                            self.modules[m] = {"source": "remote", "status": "qualified"}
                        else:
                            self.modules[m]["status"] = "qualified"
                else:
                    return
        
        if name not in self.modules:
            self.modules[name] = state
            
        self.modules[name]["status"] = nxt
        self.modified = True
        self._build_items()

    def action_enter(self, ctx):
        name, state, is_custom, is_action = self.items[self.cursor]
        if is_action:
            self._create_custom()
        elif is_custom:
            self._rename_custom(name)

    def _get_enabled_modules(self):
        return [k for k, v in self.modules.items() if v.get("status") != "disabled"]

    def _create_custom(self):
        name = LineEditor(self.scr, title="New Module Name").run()
        if name:
            self.modules[name] = {"source": "local", "status": "qualified"}
            self.index[name] = {"name": name, "dependencies": [], "exports": []}
            self.modified = True
            self._build_items()
                
    def _rename_custom(self, old_name):
        new_name = LineEditor(self.scr, title=f"Rename '{old_name}'", initial_value=old_name).run()
        if new_name and new_name != old_name:
            if new_name in self.modules or (Path("templates/module") / new_name).exists():
                TUI.show_message(self.scr, "Error", "Name already exists!")
                return
            
            if old_name in self.modules:
                self.modules[new_name] = self.modules.pop(old_name)
            if old_name in self.index:
                self.index[new_name] = self.index.pop(old_name)
                
            old_path = Path("templates/module") / old_name
            if old_path.exists():
                shutil.move(old_path, Path("templates/module") / new_name)
                
            self.modified = True
            self._build_items()

    def save(self):
        if self.modified:
            for name, state in self.modules.items():
                if state.get("source") == "local":
                    mod_path = Path("templates/module") / name
                    if not mod_path.exists():
                        create_custom_module(name)
            
            to_download = []
            for name, state in self.modules.items():
                if state.get("status") == "disabled":
                    continue
                mod_path = Path("templates/module") / name
                if not mod_path.exists():
                    if state.get("source") == "local":
                        create_custom_module(name)
                    else:
                        to_download.append(name)
                        state["source"] = "remote"

            if to_download:
                def progress_cb(msg):
                    h, w = self.scr.getmaxyx()
                    self.scr.clear()
                    TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, "Downloading...", curses.color_pair(1) | curses.A_BOLD)
                    TUI.safe_addstr(self.scr, TOP_PAD + 2, LEFT_PAD, msg[:60], curses.color_pair(4))
                    self.scr.refresh()
                download_modules(to_download, progress_cb)
            
            generate_imports_file()
        return True
