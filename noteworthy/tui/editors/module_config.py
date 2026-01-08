import curses
import json
import shutil
from pathlib import Path
from ..base import ListEditor, TUI, LEFT_PAD, TOP_PAD
from ...core.pm import (
    get_installed_modules, save_modules_config, create_custom_module, check_dependencies,
    get_latest_commit_sha, get_commit_log, get_modules_meta, save_modules_meta,
    download_modules, fetch_remote_modules, fetch_core_submodules, get_changed_files
)
from ...core.modules import generate_imports_file, get_module_conflicts
from ..components.common import LineEditor
from ...utils import register_key
from ..keybinds import KeyBind

MODULES_DIR = Path("templates/module")


class ModuleConfigEditor(ListEditor):
    """Module configuration editor with dynamic module discovery."""
    
    def __init__(self, scr):
        super().__init__(scr, "Module Configuration")
        self.modules = get_installed_modules()
        self.meta = get_modules_meta()
        self.remote_modules = []
        self.core_submodules = []
        self.section_title = "Modules"
        self.modified = False
        
        register_key(self.keymap, KeyBind(ord(' '), self.action_space, "Toggle Status"))
        register_key(self.keymap, KeyBind(ord('\n'), self.action_enter, "Action"))
        register_key(self.keymap, KeyBind(curses.KEY_ENTER, self.action_enter, "Action"))
        register_key(self.keymap, KeyBind(ord('c'), self.action_show_conflicts, "Show Conflicts"))
        
        self.has_updates = False
        self.new_commit_sha = None
        self.outdated_modules = set()
        self._check_updates_silent()
        
        register_key(self.keymap, KeyBind(ord('u'), self.action_update, "Update All"))
        
        self._build_local_index()
        self._build_items()

    def _build_local_index(self):
        self.index = {}
        if MODULES_DIR.exists():
            for item in MODULES_DIR.iterdir():
                if item.is_dir() and not item.name.startswith('.') and item.name != 'core':
                    meta_file = item / "metadata.json"
                    entry = {
                        "name": item.name,
                        "dependencies": [],
                        "exports": [],
                        "source": "local"
                    }
                    if meta_file.exists():
                        try:
                            with open(meta_file, 'r') as f:
                                meta = json.load(f)
                            entry.update(meta)
                        except:
                            pass
                    self.index[item.name] = entry
        
        # Ensure installed modules are in index
        for name, state in self.modules.items():
            if name not in self.index:
                self.index[name] = {
                    "name": name,
                    "dependencies": [],
                    "exports": [],
                    "source": state.get("source", "local")
                }

    def _check_updates_silent(self):
        # Silent check for updates
        try:
             # Check for granular updates
            from ...core.pm import check_module_updates
            self.outdated_modules = check_module_updates(self.modules)
            if self.outdated_modules:
                self.has_updates = True
        except:
            self.outdated_modules = set()
            pass
            
    def action_update(self, ctx):
        if not self.has_updates:
            return
            
        if TUI.prompt_confirm(self.scr, "Update available modules?"):
             # self.meta["commit"] = ... # No longer using global commit for all
             
             to_update = list(self.outdated_modules)
             
             if to_update:
                 def progress_cb(m):
                     self.scr.clear()
                     TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, "Updating Modules", curses.color_pair(1) | curses.A_BOLD)
                     TUI.safe_addstr(self.scr, TOP_PAD + 2, LEFT_PAD, m[:60], curses.color_pair(4))
                     self.scr.refresh()
                 download_modules(to_update, progress_cb)
                 self.has_updates = False
                 self.outdated_modules = set()
                 self.modified = True
                 TUI.show_message(self.scr, "Success", "Modules updated!")
                 self._build_items()

    def _build_items(self):
        self.items = []
        
        # Get all module names
        all_names = set(self.modules.keys()) | set(self.index.keys())
        standard = sorted([n for n in all_names if self.modules.get(n, {}).get("source") != "local" 
                          and self.index.get(n, {}).get("source") != "local"])
        custom = sorted([n for n in all_names if self.modules.get(n, {}).get("source") == "local" 
                        or self.index.get(n, {}).get("source") == "local"])
        
        for name in standard:
            state = self.modules.get(name, {"status": "disabled", "source": "remote"})
            self.items.append((name, state, False, False))
        
        # Custom/local modules
        if custom:
            self.items.append(("", None, False, False))  # Separator
            for name in custom:
                state = self.modules.get(name, {"status": "disabled", "source": "local"})
                self.items.append((name, state, True, False))
        
        # Create action
        self.items.append(("+ Create Custom Module...", None, False, True))
    
    def _get_status_str(self, state):
        if not state:
            return ""
        s = state.get("status", "disabled")
        if s == "global":
            return "GLOBAL"
        if s == "qualified":
            return "QUALIFIED"
        return "DISABLED"

    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        # Title
        title_str = f"{self.title}{' *' if self.modified else ''}"
        TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, title_str, curses.color_pair(1) | curses.A_BOLD)
        
        # Section header
        TUI.safe_addstr(self.scr, TOP_PAD + 2, LEFT_PAD, self.section_title, curses.color_pair(4) | curses.A_DIM)
        
        # Calculate visible area
        list_start_y = TOP_PAD + 3
        visible_rows = h - list_start_y - 3
        
        # Scroll adjustment
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + visible_rows:
            self.scroll = self.cursor - visible_rows + 1
            
        # Draw items
        for i in range(visible_rows):
            idx = self.scroll + i
            if idx >= len(self.items):
                break
            y = list_start_y + i
            
            name, state, is_custom, is_action = self.items[idx]
            is_selected = (idx == self.cursor)
            
            # Draw cursor
            if is_selected:
                TUI.safe_addstr(self.scr, y, LEFT_PAD, "▶", curses.color_pair(3) | curses.A_BOLD)
            
            # Draw Name
            name_attr = 0
            if is_selected:
                name_attr |= curses.A_REVERSE
            if is_action:
                 name_attr |= curses.color_pair(3)
            
            TUI.safe_addstr(self.scr, y, LEFT_PAD + 2, name, name_attr)
            
            # Draw Status
            if not is_action and state:
                status = state.get("status", "disabled")
                status_str = self._get_status_str(state)
                
                status_attr = 0
                if is_selected:
                    status_attr |= curses.A_REVERSE
                
                if status == "disabled":
                     status_attr |= curses.color_pair(4) | curses.A_DIM
                elif status == "qualified":
                     status_attr |= curses.color_pair(2)
                elif status == "global":
                     status_attr |= curses.color_pair(3) | curses.A_BOLD

                TUI.safe_addstr(self.scr, y, LEFT_PAD + 35, status_str, status_attr)

                if self.has_updates and name in self.outdated_modules:
                    TUI.safe_addstr(self.scr, y, LEFT_PAD + 45, "[U]", curses.color_pair(3)|curses.A_BOLD)

        # Conflicts warning
        conflicts = get_module_conflicts(self._get_enabled_modules())
        if conflicts:
            TUI.safe_addstr(self.scr, h - 3, LEFT_PAD, f"⚠ {len(conflicts)} symbol conflicts!", 
                           curses.color_pair(3) | curses.A_BOLD)
        
        # Footer
        footer = "Space Toggle  Enter Details  c Conflicts  Esc Back"
        if self.has_updates:
            footer = "u Update  " + footer
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, footer, 
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
            self.modules[name] = state.copy()
        
        self.modules[name]["status"] = nxt
        self.modified = True
        self._build_items()

    def action_enter(self, ctx):
        name, state, is_custom, is_action = self.items[self.cursor]
        if is_action:
            self._create_custom()
        elif is_custom:
            self._rename_custom(name)

    def action_show_conflicts(self, ctx):
        """Show symbol conflicts in a dialog."""
        conflicts = get_module_conflicts()
        if not conflicts:
            TUI.show_message(self.scr, "No Conflicts", "No symbol conflicts detected!")
            return
        
        # Build conflict message
        lines = []
        for sym, modules in sorted(conflicts.items()):
            lines.append(f"  {sym}: {', '.join(modules)}")
        
        msg = f"{len(conflicts)} symbol conflicts:\n" + "\n".join(lines[:15])
        if len(lines) > 15:
            msg += f"\n...and {len(lines) - 15} more"
        
        TUI.show_message(self.scr, "Symbol Conflicts", msg)

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
            if new_name in self.modules or (MODULES_DIR / new_name).exists():
                TUI.show_message(self.scr, "Error", "Name already exists!")
                return
            
            if old_name in self.modules:
                self.modules[new_name] = self.modules.pop(old_name)
            if old_name in self.index:
                self.index[new_name] = self.index.pop(old_name)
            
            old_path = MODULES_DIR / old_name
            if old_path.exists():
                shutil.move(old_path, MODULES_DIR / new_name)
            
            self.modified = True
            self._build_items()

    def save(self):
        if self.modified:
            # Create local modules
            for name, state in self.modules.items():
                if state.get("source") == "local":
                    mod_path = MODULES_DIR / name
                    if not mod_path.exists():
                        create_custom_module(name)
            
            # Download missing remote modules
            to_download = []
            for name, state in self.modules.items():
                if state.get("status") == "disabled":
                    continue
                mod_path = MODULES_DIR / name
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
            
            save_modules_config(self.modules)
            generate_imports_file()
        return True
