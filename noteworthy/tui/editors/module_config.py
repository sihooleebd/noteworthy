import curses
import json
import shutil
from pathlib import Path
from ..base import ListEditor, TUI
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
    def __init__(self, scr):
        super().__init__(scr, "Module Configuration")
        self.modules = get_installed_modules()
        self.meta = get_modules_meta()
        self.remote_index = {}
        self._build_local_index()
        self.box_title = "Modules"
        self._build_items()
        self.modified = False
        
        # Register Keybinds
        register_key(self.keymap, KeyBind(ord(' '), self.action_space, "Toggle Status"))
        register_key(self.keymap, KeyBind(ord('\n'), self.action_enter, "Action"))
        register_key(self.keymap, KeyBind(curses.KEY_ENTER, self.action_enter, "Action"))
        
        # Check updates immediately
        self._check_for_updates()
        
    def _check_for_updates(self):
        # UI: "Checking for updates..."
        h, w = TUI.get_dims(self.scr)
        # Clear screen and show loading
        self.scr.clear()
        TUI.safe_addstr(self.scr, h//2, (w-20)//2, "Checking for updates...", curses.color_pair(4))
        self.scr.refresh()
        
        latest_sha = get_latest_commit_sha()
        current_sha = self.meta.get("commit")
        
        if latest_sha and latest_sha != current_sha:
            logs = list(get_commit_log(current_sha, latest_sha))
            msg = "New updates available!\n\nChanges:\n" + "\n".join(logs[:10])
            if len(logs) > 10: msg += "\n...and more"
            msg += "\n\nUpdate modules now?"
            
            if TUI.prompt_confirm(self.scr, "Update Available"):
                # Mark to update
                self.meta["commit"] = latest_sha
                save_modules_meta(self.meta)
                
                # Re-download all enabled remote modules
                to_update = []
                for name, state in self.modules.items():
                    if state.get("status") != "disabled" and state.get("source") == "remote":
                         to_update.append(name)
                
                if to_update:
                    def progress_cb(m):
                        TUI.draw_box(self.scr, h//2 - 2, w//2 - 20, 5, 40, "Updating Modules")
                        TUI.safe_addstr(self.scr, h//2, w//2 - 18, m[:36].ljust(36), curses.color_pair(4))
                        self.scr.refresh()
                    download_modules(to_update, progress_cb)
                    
                    TUI.show_message(self.scr, "Success", "Modules updated successfully!")

        
    def _build_local_index(self):
        self.index = {}
        root = Path("templates/module")
        if root.exists():
            for d in root.iterdir():
                if d.is_dir():
                    meta_path = d / "metadata.json"
                    if meta_path.exists():
                        try:
                            meta = json.loads(meta_path.read_text())
                            self.index[d.name] = meta
                        except: pass
                    else:
                        self.index[d.name] = {"name": d.name, "dependencies": []}

    def _build_items(self):
        self.items = [] # List of tuples (name, state, is_custom, is_action)
        
        all_keys = set(self.modules.keys()) | set(self.index.keys())
        standard = sorted([k for k in all_keys if k in STANDARD_MODULES])
        custom = sorted([k for k in all_keys if k not in STANDARD_MODULES])
        
        for name in standard:
            state = self.modules.get(name, {"status": "disabled", "source": "local"})
            self.items.append((name, state, False, False))
            
        if custom:
            self.items.append(("", None, False, False)) # Separator
            for name in custom:
                state = self.modules.get(name, {"status": "disabled", "source": "local"})
                self.items.append((name, state, True, False))
                
        self.items.append(("+ Create Custom Module...", None, False, True))
            
    def _get_status_str(self, state):
        if not state: return ""
        s = state.get("status", "disabled")
        if s == "global": return "Imported (Global)"
        if s == "qualified": return "Enabled (Qualified)"
        return "Disabled"
        
    def refresh(self):
        conflicts = get_module_conflicts()
        h, w = TUI.get_dims(self.scr)
        self.scr.clear()
        
        title = "Module Configuration"
        TUI.safe_addstr(self.scr, 1, (w-len(title))//2, title, curses.color_pair(1)|curses.A_BOLD)

        list_h = min(len(self.items) + 3, h - 8) 
        start_y = 3
        bx = (w - 70) // 2
        bw = 70
        
        TUI.draw_box(self.scr, start_y, bx, list_h, bw, "Modules")
        
        TUI.safe_addstr(self.scr, start_y + 1, bx + 2, "Module Name", curses.color_pair(1)|curses.A_BOLD)
        TUI.safe_addstr(self.scr, start_y + 1, bx + 40, "Status", curses.color_pair(1)|curses.A_BOLD)
        
        vis_count = list_h - 3
        
        if self.cursor < self.scroll: self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis_count: self.scroll = self.cursor - vis_count + 1
        
        for i in range(vis_count):
            idx = self.scroll + i
            if idx >= len(self.items): break
            
            name, state, is_custom, is_action = self.items[idx]
            y = start_y + 2 + i
            
            if name == "" and state is None: 
                TUI.safe_addstr(self.scr, y, bx + 1, "─" * (bw - 2), curses.color_pair(4)|curses.A_DIM)
                continue
                
            selected = (idx == self.cursor)
            style = curses.color_pair(4)
            if selected: style = curses.color_pair(3) | curses.A_BOLD
            
            if is_action:
                TUI.safe_addstr(self.scr, y, bx + 2, name, style)
            else:
                TUI.safe_addstr(self.scr, y, bx + 2, name[:35].ljust(35), style)
                
                status_str = self._get_status_str(state)
                status_style = style
                if state.get("status") == "global": status_style = style | curses.A_BOLD
                elif state.get("status") == "disabled": status_style = style | curses.A_DIM
                
                # Highlight new/unsaved custom modules
                mod_path = Path("templates/module") / name
                if is_custom and not mod_path.exists():
                     status_str += " *"
                
                TUI.safe_addstr(self.scr, y, bx + 40, status_str, status_style)
                 
        help_msg = "Space: Toggle Status   Enter: Rename (Custom) / Create   Esc: Save & Exit"
        TUI.safe_addstr(self.scr, h-2, (w-len(help_msg))//2, help_msg, curses.color_pair(4))
        
        if conflicts:
            warn = f"WARNING: {len(conflicts)} symbol conflicts detected in Global modules!"
            TUI.safe_addstr(self.scr, h-3, (w-len(warn))//2, warn, curses.color_pair(2)|curses.A_BOLD)

        self.scr.refresh()

    def action_space(self, ctx):
        name, state, is_custom, is_action = self.items[self.cursor]
        if is_action or not state: return
        
        curr = state.get("status", "disabled")
        nxt = "disabled"
        if curr == "disabled": nxt = "qualified"
        elif curr == "qualified": nxt = "global"
        elif curr == "global": nxt = "disabled"
        
        if nxt != "disabled":
            missing = check_dependencies(name, self.index, self._get_enabled_modules())
            if missing:
                msg = f"Module '{name}' requires: {', '.join(missing)}.\nEnable them?"
                if TUI.prompt_confirm(self.scr, msg):
                    for m in missing:
                        if m not in self.modules: self.modules[m] = {"source": "remote", "status": "qualified"}
                        else: self.modules[m]["status"] = "qualified"
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
            # Just add to config/state, do NOT create files yet
            self.modules[name] = {"source": "local", "status": "qualified"}
            # Mock index entry
            self.index[name] = {"name": name, "dependencies": [], "exports": []}
            self.modified = True
            self._build_items()
                
    def _rename_custom(self, old_name):
        new_name = LineEditor(self.scr, title=f"Rename '{old_name}'", initial_value=old_name).run()
        if new_name and new_name != old_name:
            if new_name in self.modules or (Path("templates/module") / new_name).exists():
                TUI.show_message(self.scr, "Error", "Module name already exists!")
                return
            
            # Update modules config key
            if old_name in self.modules:
                self.modules[new_name] = self.modules.pop(old_name)
                
            # Update index
            if old_name in self.index:
                self.index[new_name] = self.index.pop(old_name)
                
            # Determine if we need to rename on disk NOW or LATER
            # If it exists on disk, rename it now to keep sync? 
            # User expectation: rename happens immediately if it exists, or just updates pending if not.
            old_path = Path("templates/module") / old_name
            if old_path.exists():
                shutil.move(old_path, Path("templates/module") / new_name)
                
            self.modified = True
            self._build_items()

    def save(self):
        if self.modified:
            # 1. Create local modules if missing
            for name, state in self.modules.items():
                if state.get("source") == "local":
                    mod_path = Path("templates/module") / name
                    if not mod_path.exists():
                        create_custom_module(name)
                        
            # 2. Identify Remote Modules to Download
            # For now, we download if it's marked 'remote' and missing on disk.
            # In future, could check versions.
            to_download = []
            for name, state in self.modules.items():
                # We assume if it's in the list and not 'local', it's 'remote' (or we default it)
                # But wait, we default everything to 'local' in _build_items if missing. 
                # We need to respect the 'source' from config or index. 
                # Actually, standard modules are usually 'remote' candidate if we change the source in config.
                # However, currently modules.json defaults to local.
                # Let's check against list of what's missing on disk.
                mod_path = Path("templates/module") / name
                if not mod_path.exists() and state.get("source") == "remote":
                    to_download.append(name)
            
            # Also check if we just enabled a standard module that was missing? 
            # If user enables 'graph', and 'graph' folder is missing, we should download it.
            # So checking existence is good. 'source' might be wrong in config if we didn't set it.
            # Let's force check against index for source?
            
            # Refined Logic:
            # If enabled/global/qualified AND missing on disk:
            #   If in local storage -> create (handled above)
            #   If in remote index -> add to download list
            
            for name, state in self.modules.items():
                if state.get("status") == "disabled": continue
                
                mod_path = Path("templates/module") / name
                if not mod_path.exists():
                    if state.get("source") == "local":
                        create_custom_module(name)
                    else:
                        to_download.append(name)
                        # Ensure config says remote
                        state["source"] = "remote"

            if to_download:
                from ...core.pm import download_modules
                
                def progress_cb(msg):
                    h, w = TUI.get_dims(self.scr)
                    TUI.draw_box(self.scr, h//2 - 2, w//2 - 20, 5, 40, "Downloading Modules")
                    TUI.safe_addstr(self.scr, h//2, w//2 - 18, msg[:36].ljust(36), curses.color_pair(4))
                    self.scr.refresh()
                    
                download_modules(to_download, progress_cb)
            
            # 3. Generate Imports
            generate_imports_file()
        return True
