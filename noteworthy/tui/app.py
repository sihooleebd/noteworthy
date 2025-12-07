import curses
import json
from ..config import CONFIG_FILE, HIERARCHY_FILE, SCHEMES_FILE
from ..core.templates import restore_templates
from ..core.sync import sync_hierarchy_with_content
from .base import TUI
from .wizards.init import InitWizard
from .wizards.hierarchy import HierarchyWizard
from .wizards.schemes import SchemesWizard
from .wizards.sync import SyncWizard
from .menus import MainMenu
from .editors import show_editor_menu
from .editors.hierarchy import HierarchyEditor
from .components.build import BuildMenu, run_build_process
from .components.common import show_error_screen

def needs_init():
    return not (CONFIG_FILE.exists() and HIERARCHY_FILE.exists() and SCHEMES_FILE.exists())

def run_app(scr, args):
    TUI.init_colors()
    if not TUI.check_terminal_size(scr):
        return
    restore_templates(scr)
    if needs_init():
        if not CONFIG_FILE.exists():
            if InitWizard(scr).run() is None:
                return
        if not HIERARCHY_FILE.exists():
            res = HierarchyWizard(scr).run()
            if res is None:
                return
            elif res == 'edit':
                HierarchyEditor(scr).run()
        if not SCHEMES_FILE.exists():
            if SchemesWizard(scr).run() is None:
                return
    if HIERARCHY_FILE.exists():
        missing, new = sync_hierarchy_with_content()
        if missing or new:
            if SyncWizard(scr, missing, new).run() is False:
                return
    while True:
        menu = MainMenu(scr)
        action = menu.run()
        if action is None:
            break
        elif action == 'editor':
            show_editor_menu(scr)
        elif action == 'builder':
            try:
                hierarchy = json.loads(HIERARCHY_FILE.read_text())
                menu = BuildMenu(scr, hierarchy)
                res = menu.run()
                if res:
                    run_build_process(scr, hierarchy, res)
            except Exception as e:
                show_error_screen(scr, e)