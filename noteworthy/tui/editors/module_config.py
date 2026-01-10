import logging
import curses
import json
import shutil
from pathlib import Path
from ..base import ListEditor, TUI, LEFT_PAD, TOP_PAD
from ...core.pm import (
    sync_modules_config, load_full_config, save_full_config,
    check_dependencies, create_custom_module, install_modules,
    install_core_modules_with_sha, get_module_sha_from_cache,
    ensure_module_cache, check_module_updates
)
from ...core.modules import generate_imports_file, get_module_conflicts
from ..components.common import LineEditor
from ...utils import register_key
from ..keybinds import KeyBind

# Setup debug logging
logging.basicConfig(filename='module_debug.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

MODULES_DIR = Path.cwd() / "templates/module"


class ModuleConfigEditor(ListEditor):
    """Module configuration editor with dynamic module discovery."""
    
    def __init__(self, scr):
        super().__init__(scr, "Module Configuration")
        
        # Show loading message
        TUI.safe_addstr(scr, TOP_PAD, LEFT_PAD, "Syncing modules...", curses.color_pair(4))
        scr.refresh()
        
        # Sync config with remote and local (sanity check)
        def sync_callback(msg):
            scr.clear()
            TUI.safe_addstr(scr, TOP_PAD, LEFT_PAD, "Syncing modules...", curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(scr, TOP_PAD + 2, LEFT_PAD, msg[:60], curses.color_pair(4))
            scr.refresh()
        
        self.config = sync_modules_config(sync_callback)
        
        # Extract module sections
        self.core_modules = self.config.get("core_modules", {})
        self.modules = self.config.get("modules", {})
        self.local_modules = self.config.get("local_modules", {})

        # Check for updates and missing files
        self.outdated_modules = check_module_updates(self.config)
        self.missing_modules = self._check_missing_modules()
        self.has_updates = bool(self.outdated_modules)
        self.has_missing = bool(self.missing_modules)
        
        self.section_title = "Modules"
        self.modified = False
        
        # Build metadata index for dependency checking
        self._build_index()
        
        # Register keybinds
        register_key(self.keymap, KeyBind(ord(' '), self.action_space, "Toggle Status"))
        register_key(self.keymap, KeyBind(ord('\n'), self.action_enter, "Action"))
        register_key(self.keymap, KeyBind(curses.KEY_ENTER, self.action_enter, "Action"))
        register_key(self.keymap, KeyBind(ord('c'), self.action_show_conflicts, "Show Conflicts"))
        register_key(self.keymap, KeyBind(ord('r'), self.action_resync, "Resync"))
        register_key(self.keymap, KeyBind(ord('u'), self.action_update_all, "Update All"))
        
        self._build_items()
    
    def _check_missing_modules(self):
        """Identify enabled modules that are missing from disk."""
        missing = set()
        # Check core modules
        for name in self.core_modules:
            if not (MODULES_DIR / "core" / name).exists():
                missing.add(f"core/{name}")
        
        # Check defaults
        for name, state in self.modules.items():
            if state.get("status") != "disabled":
                if not (MODULES_DIR / name).exists():
                    missing.add(name)
        
        # Check locals
        for name, state in self.local_modules.items():
            if state.get("status") != "disabled":
                if not (MODULES_DIR / name).exists():
                    missing.add(name)
        return missing

    def _build_index(self):
        """Build metadata index for all modules."""
        self.index = {}
        
        # Core modules
        for name, meta in self.core_modules.items():
            self.index[name] = {
                "name": name,
                "dependencies": meta.get("dependencies", []),
                "exports": meta.get("exports", []),
                "source": "core"
            }
        
        # Default modules
        for name, state in self.modules.items():
            self.index[name] = {
                "name": name,
                "dependencies": state.get("dependencies", []),
                "exports": state.get("exports", []),
                "source": "remote"
            }
        
        # Local modules
        for name, state in self.local_modules.items():
            self.index[name] = {
                "name": name,
                "dependencies": [],
                "exports": [],
                "source": "local"
            }
    
    def _build_items(self):
        """Build the list items with three sections."""
        self.items = []
        
        # Section: Core Modules (non-toggleable, always global)
        if self.core_modules:
            self.items.append(("── Core (always enabled) ──", None, "header", False))
            for name in sorted(self.core_modules.keys()):
                state = {"status": "global", "source": "core"}
                self.items.append((name, state, "core", False))
        
        # Section: Default Modules (from remote repo)
        if self.modules:
            self.items.append(("── Modules ──", None, "header", False))
            for name in sorted(self.modules.keys()):
                state = self.modules[name]
                self.items.append((name, state, "default", False))
        
        # Section: Local Modules (user-created)
        if self.local_modules:
            self.items.append(("── Local ──", None, "header", False))
            for name in sorted(self.local_modules.keys()):
                state = self.local_modules[name]
                self.items.append((name, state, "local", False))
        
        # Create action
        self.items.append(("+ Create Custom Module...", None, "action", True))
    
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
        
        # Calculate visible area
        list_start_y = TOP_PAD + 2
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
            
            name, state, item_type, is_action = self.items[idx]
            is_selected = (idx == self.cursor)
            
            # Handle headers
            if item_type == "header":
                TUI.safe_addstr(self.scr, y, LEFT_PAD, name, curses.color_pair(4) | curses.A_DIM)
                continue
            
            # Draw cursor (skip for headers)
            if is_selected:
                TUI.safe_addstr(self.scr, y, LEFT_PAD, "▶", curses.color_pair(3) | curses.A_BOLD)
            
            # Draw Name
            name_attr = 0
            if is_selected:
                name_attr |= curses.A_REVERSE
            if is_action:
                name_attr |= curses.color_pair(3)
            elif item_type == "core":
                # Core modules are dimmed (non-toggleable)
                name_attr |= curses.A_DIM
            
            TUI.safe_addstr(self.scr, y, LEFT_PAD + 2, name, name_attr)
            
            # Draw Status
            if not is_action and state:
                status = state.get("status", "disabled")
                status_str = self._get_status_str(state)
                
                status_attr = 0
                if is_selected:
                    status_attr |= curses.A_REVERSE
                
                if item_type == "core":
                    # Core is always global, show in green but dimmed
                    status_attr |= curses.color_pair(2) | curses.A_DIM
                elif status == "disabled":
                    status_attr |= curses.color_pair(4) | curses.A_DIM
                elif status == "qualified":
                    status_attr |= curses.color_pair(2)
                elif status == "global":
                    status_attr |= curses.color_pair(3) | curses.A_BOLD

                TUI.safe_addstr(self.scr, y, LEFT_PAD + 35, status_str, status_attr)
                
                # Show update/missing indicator
                indicator = ""
                attr = curses.color_pair(3) | curses.A_BOLD
                
                if item_type == "core":
                     if f"core/{name}" in self.missing_modules:
                         indicator = "[Missing]"
                         attr = curses.color_pair(6) | curses.A_BOLD
                     elif f"core/{name}" in self.outdated_modules:
                         indicator = "[Update available]"
                elif item_type == "default":
                     if name in self.missing_modules:
                         indicator = "[Missing]"
                         attr = curses.color_pair(6) | curses.A_BOLD
                     elif name in self.outdated_modules:
                         indicator = "[Update available]"
                elif item_type == "local" and name in self.missing_modules:
                     indicator = "[Missing]"
                     attr = curses.color_pair(6) | curses.A_BOLD
                
                if indicator:
                    TUI.safe_addstr(self.scr, y, LEFT_PAD + 48, indicator, attr)

        # Conflicts warning
        conflicts = get_module_conflicts(self._get_enabled_modules())
        if conflicts:
            TUI.safe_addstr(self.scr, h - 3, LEFT_PAD, f"⚠ {len(conflicts)} symbol conflicts!", 
                           curses.color_pair(3) | curses.A_BOLD)
        
        # Footer
        footer = "Space Toggle  r Resync  u Update  c Conflicts  Esc Save"
        if self.has_missing:
            footer = "Esc Restore Missing  " + footer
        TUI.safe_addstr(self.scr, h - 2, LEFT_PAD, footer, 
                       curses.color_pair(4) | curses.A_DIM)
        
        self.scr.refresh()

    def action_space(self, ctx):
        """Toggle module status (only for default and local modules)."""
        name, state, item_type, is_action = self.items[self.cursor]
        
        # Can't toggle headers, actions, or core modules
        if is_action or not state or item_type in ("header", "core"):
            return
        
        curr = state.get("status", "disabled")
        nxt = "disabled"
        if curr == "disabled":
            nxt = "qualified"
        elif curr == "qualified":
            nxt = "global"
        elif curr == "global":
            nxt = "disabled"
        
        # Check dependencies when enabling
        if nxt != "disabled":
            missing = check_dependencies(name, self.index, self._get_enabled_modules())
            if missing:
                if TUI.prompt_confirm(self.scr, f"Enable dependencies: {', '.join(missing)}?"):
                    for m in missing:
                        if m in self.modules:
                            self.modules[m]["status"] = "qualified"
                        elif m in self.local_modules:
                            self.local_modules[m]["status"] = "qualified"
                else:
                    return
        
        # Update the correct section
        if item_type == "default":
            self.modules[name]["status"] = nxt
            # Check if newly enabled module is missing
            if nxt != "disabled" and not (MODULES_DIR / name).exists():
                 self.missing_modules.add(name)
                 self.has_missing = True
        elif item_type == "local":
            self.local_modules[name]["status"] = nxt
            if nxt != "disabled" and not (MODULES_DIR / name).exists():
                 self.missing_modules.add(name)
                 self.has_missing = True
        
        self.modified = True
        logging.debug(f"Action Space: modified=True, has_missing={self.has_missing}")
        self._build_items()

    def action_enter(self, ctx):
        name, state, item_type, is_action = self.items[self.cursor]
        if is_action:
            self._create_custom()
        elif item_type == "local":
            self._rename_custom(name)

    def action_resync(self, ctx):
        """Re-sync modules with remote repository."""
        def sync_callback(msg):
            self.scr.clear()
            TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, "Resyncing...", curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, TOP_PAD + 2, LEFT_PAD, msg[:60], curses.color_pair(4))
            self.scr.refresh()
        
        self.config = sync_modules_config(sync_callback)
        self.core_modules = self.config.get("core_modules", {})
        self.modules = self.config.get("modules", {})
        self.local_modules = self.config.get("local_modules", {})
        
        # Re-check updates after resync
        self.outdated_modules = check_module_updates(self.config)
        self.missing_modules = self._check_missing_modules()
        self.has_updates = bool(self.outdated_modules)
        self.has_missing = bool(self.missing_modules)
        
        self._build_index()
        self._build_items()
        
        TUI.show_message(self.scr, "Sync Complete", "Module list updated from remote repository.")
    
    def action_update_all(self, ctx):
        """Mark all outdated modules to be updated (by setting modified=True)"""
        if not self.has_updates:
            TUI.show_message(self.scr, "Info", "No updates available.")
            return

        cnt = 0
        for name in self.modules:
            if name in self.outdated_modules and self.modules[name]["status"] != "disabled":
                cnt += 1
        
        if cnt > 0:
             self.modified = True
             TUI.show_message(self.scr, "Update", f"Marked {cnt} modules for update on Save.")
        else:
             TUI.show_message(self.scr, "Info", "Enable modules to update them.")

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
        """Get list of all enabled module names."""
        enabled = list(self.core_modules.keys())  # Core always enabled
        enabled += [k for k, v in self.modules.items() if v.get("status") != "disabled"]
        enabled += [k for k, v in self.local_modules.items() if v.get("status") != "disabled"]
        return enabled

    def _create_custom(self):
        name = LineEditor(self.scr, title="New Module Name").run()
        if name:
            # Check for duplicates
            if name in self.modules or name in self.local_modules or name in self.core_modules:
                TUI.show_message(self.scr, "Error", "Module name already exists!")
                return
            
            self.local_modules[name] = {"source": "local", "status": "qualified"}
            self.index[name] = {"name": name, "dependencies": [], "exports": [], "source": "local"}
            self.modified = True
            self._build_items()
                
    def _rename_custom(self, old_name):
        new_name = LineEditor(self.scr, title=f"Rename '{old_name}'", initial_value=old_name).run()
        if new_name and new_name != old_name:
            if new_name in self.modules or new_name in self.local_modules or (MODULES_DIR / new_name).exists():
                TUI.show_message(self.scr, "Error", "Name already exists!")
                return
            
            if old_name in self.local_modules:
                self.local_modules[new_name] = self.local_modules.pop(old_name)
            if old_name in self.index:
                self.index[new_name] = self.index.pop(old_name)
            
            old_path = MODULES_DIR / old_name
            if old_path.exists():
                shutil.move(old_path, MODULES_DIR / new_name)
            
            self.modified = True
            self._build_items()

    def handle_input(self, k):
        if k == 27: # Esc
            logging.debug("ESC pressed (manual catch)")
            return True, self.do_exit()
        
        logging.debug(f"Key pressed: {k}")
        return super().handle_input(k)

    def do_exit(self, ctx=None):
        """Override exit to ensure updates are applied."""
        logging.debug(f"do_exit called. modified={self.modified}, has_updates={self.has_updates}, has_missing={self.has_missing}")
        if self.modified or self.has_updates or self.has_missing:
            self.save()
        return 'EXIT'

    def save(self):
        logging.debug(f"save called. modified={self.modified}, has_updates={self.has_updates}, has_missing={self.has_missing}")
        if self.modified or self.has_updates or self.has_missing:
            try:
                def progress_cb(msg):
                    h, w = self.scr.getmaxyx()
                    self.scr.clear()
                    TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, "Installing modules...", curses.color_pair(1) | curses.A_BOLD)
                    TUI.safe_addstr(self.scr, TOP_PAD + 2, LEFT_PAD, msg[:60], curses.color_pair(4))
                    self.scr.refresh()
                
                # Install core modules (and store SHAs)
                core_installed = install_core_modules_with_sha(progress_cb, self.config)
                for name, sha in core_installed.items():
                    if name in self.core_modules:
                        self.core_modules[name]["sha"] = sha
                
                # Create local modules
                for name, state in self.local_modules.items():
                    mod_path = MODULES_DIR / name
                    if not mod_path.exists():
                        create_custom_module(name)
                
                # Install enabled remote modules that aren't present locally OR have updates
                to_install = []
                for name, state in self.modules.items():
                    if state.get("status") == "disabled":
                        continue
                    
                    mod_path = MODULES_DIR / name
                    needs_install = False
                    
                    # Check if missing
                    if not mod_path.exists():
                        needs_install = True
                        logging.debug(f"Module {name} missing at {mod_path}")
                    # Check if update available (SHA mismatch or missing SHA)
                    elif name in self.outdated_modules:
                        needs_install = True
                        logging.debug(f"Module {name} outdated")
                    
                    if needs_install:
                        to_install.append(name)

                logging.debug(f"to_install list: {to_install}")

                if to_install:
                    # Install and update SHAs
                    installed = install_modules(to_install, progress_cb, self.config)
                    logging.debug(f"Install result: {installed}")
                    for name, sha in installed.items():
                        if name in self.modules:
                             self.modules[name]["sha"] = sha
                
                # Update config
                self.config["core_modules"] = self.core_modules
                self.config["modules"] = self.modules
                self.config["local_modules"] = self.local_modules
                save_full_config(self.config)
                
                generate_imports_file()
                
                # Refresh outdated/missing list
                self.outdated_modules = check_module_updates(self.config)
                self.missing_modules = self._check_missing_modules()
                self.has_updates = bool(self.outdated_modules)
                self.has_missing = bool(self.missing_modules)
                self.modified = False
            
            except Exception as e:
                TUI.show_message(self.scr, "Error Saving", f"Failed to save/install modules:\n{str(e)}")
                return False
            
        return True
