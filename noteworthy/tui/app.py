import curses
import json
from ..config import METADATA_FILE, CONSTANTS_FILE, HIERARCHY_FILE, SCHEMES_DIR, BASE_DIR
from ..core.templates import restore_templates
from .base import TUI
from .wizards.init import InitWizard
from .wizards.hierarchy import HierarchyWizard
from .wizards.schemes import SchemesWizard
from .menus import MainMenu
from .editors import show_editor_menu
from .editors.hierarchy import HierarchyEditor
from .components.build import BuildMenu, run_build_process
from .components.common import show_error_screen

def combine_schemes():
    """Generate names.json manifest from config/schemes/data/ folder"""
    schemes_dir = SCHEMES_DIR
    themes_dir = schemes_dir / 'data'
    if not themes_dir.exists():
        return
    
    names = []
    for scheme_file in sorted(themes_dir.glob('*.json')):
        if scheme_file.name != 'names.json':  # Skip the manifest itself
            names.append(scheme_file.stem)  # filename without .json
    
    if names:
        names_file = schemes_dir / 'names.json'
        names_file.write_text(json.dumps(names, indent=4))

def needs_init():
    return not (METADATA_FILE.exists() and HIERARCHY_FILE.exists() and (SCHEMES_DIR / 'names.json').exists())

def run_build(scr):
    try:
        hierarchy = json.loads(HIERARCHY_FILE.read_text())
        menu = BuildMenu(scr, hierarchy)
        res = menu.run()
        if res:
            run_build_process(scr, hierarchy, res)
    except Exception as e:
        show_error_screen(scr, e)

def run_app(scr, args):
    TUI.init_colors()
    if not TUI.check_terminal_size(scr):
        return
    combine_schemes()  # Combine schemes folder into names.json
    restore_templates(scr)
    if needs_init():
        if not METADATA_FILE.exists():
            if InitWizard(scr).run() is None:
                return
        if not HIERARCHY_FILE.exists():
            res = HierarchyWizard(scr).run()
            if res is None:
                return
            elif res == 'edit':
                HierarchyEditor(scr).run()
        if not (SCHEMES_DIR / 'names.json').exists():
            if SchemesWizard(scr).run() is None:
                return
    
    # No sync wizard - just run the main menu
    while True:
        menu = MainMenu(scr)
        action = menu.run()
        if action is None or action == 'EXIT':
            break
        elif action == 'editor':
            show_editor_menu(scr)
        elif action == 'builder':
            run_build(scr)