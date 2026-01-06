import curses
from ..base import TUI, LEFT_PAD, TOP_PAD
from ...assets import LOGO
from .settings import SettingsEditor

def show_editor_menu(scr):
    """Launch the unified Settings Editor directly."""
    SettingsEditor(scr).run()

# Legacy map kept for reference or direct launching if needed
def _run_editor(scr, key):
    pass