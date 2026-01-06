
import curses
from ..base import BaseEditor, TUI, LEFT_PAD, TOP_PAD
from ...utils import register_key
from ..keybinds import NavigationBind, KeyBind
from .config import ConfigEditor
from .module_config import ModuleConfigEditor
from .blueprint import BlueprintEditor
from .hierarchy import HierarchyEditor
from .schemes import SchemeEditor
from .snippets import SnippetsEditor
from .indexignore import IndexignoreEditor
from pathlib import Path
from ...config import BASE_DIR

class SettingsEditor(BaseEditor):
    """
    Mac System Preferences style editor.
    Sidebar on the left, active editor on the right.
    """
    def __init__(self, scr):
        super().__init__(scr, "Settings")
        self.sidebar_width = 25
        self.active_pane = 'sidebar'  # or 'content'
        self.sidebar_idx = 0
        
        # Initialize sub-editors
        # We will create subwindows for them when we draw
        self.general_editor = ConfigEditor(scr) # Placeholder scr
        self.module_editor = ModuleConfigEditor(scr) # Placeholder scr
        
        self.sections = [
            ("General", self.general_editor),
            ("Structure", HierarchyEditor(scr)),
            ("Themes", SchemeEditor(scr)),
            ("Snippets", SnippetsEditor(scr)),
            ("Ignored", IndexignoreEditor(scr)),
            ("Modules", None),
            ("Module Settings", self.module_editor),
        ]
        
        self.discover_modules(scr)

        # Navigation keys
        register_key(self.keymap, NavigationBind('UP', self.nav_up))
        register_key(self.keymap, NavigationBind('DOWN', self.nav_down))
        register_key(self.keymap, NavigationBind('RIGHT', self.focus_content))
        register_key(self.keymap, KeyBind(ord('\n'), self.focus_content, "Edit"))
        register_key(self.keymap, KeyBind(curses.KEY_ENTER, self.focus_content, "Edit"))
        register_key(self.keymap, NavigationBind('LEFT', self.focus_sidebar))
        register_key(self.keymap, KeyBind(27, self.on_escape, "Back"))

    def nav_up(self, ctx):
        if self.active_pane == 'sidebar':
            new_idx = max(0, self.sidebar_idx - 1)
            # Skip subtitles (editor is None)
            while new_idx > 0 and self.sections[new_idx][1] is None:
                new_idx -= 1
            if self.sections[new_idx][1] is not None:
                self.sidebar_idx = new_idx
        else:
            # Delegate to active editor?
            # Actually, we should probably pass key events to the active editor
            # if we are in content mode.
            pass

    def nav_down(self, ctx):
        if self.active_pane == 'sidebar':
            new_idx = min(len(self.sections) - 1, self.sidebar_idx + 1)
            # Skip subtitles
            while new_idx < len(self.sections) - 1 and self.sections[new_idx][1] is None:
                new_idx += 1
            if self.sections[new_idx][1] is not None:
                self.sidebar_idx = new_idx
        else:
            pass

    def focus_content(self, ctx):
        self.active_pane = 'content'

    def focus_sidebar(self, ctx):
        self.active_pane = 'sidebar'

    def on_escape(self, ctx):
        if self.active_pane == 'content':
            self.active_pane = 'sidebar'
        else:
            return 'EXIT'

    def handle_input(self, k):
        if self.active_pane == 'content':
            # Pass input to the active editor
            editor = self.sections[self.sidebar_idx][1]
            # We need to map ESC to leave content mode
            if k == 27:
                self.active_pane = 'sidebar'
                return True, None
            
            # Special case: If key is LEFT, go back to sidebar
            if k == curses.KEY_LEFT:
                 self.active_pane = 'sidebar'
                 return True, None
            
            return editor.handle_input(k)
        else:
            if k in (27, curses.KEY_LEFT):
                return True, 'EXIT'
            return super().handle_input(k)

    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        # Draw Sidebar
        self._draw_sidebar(h, w)
        
        # Draw Separator
        for y in range(h):
            TUI.safe_addstr(self.scr, y, self.sidebar_width, "│", curses.color_pair(4)|curses.A_DIM)
            
        # Draw Content
        self._draw_content(h, w)
        
        self.scr.refresh()

    def _draw_sidebar(self, h, w):
        # Title
        TUI.safe_addstr(self.scr, TOP_PAD, LEFT_PAD, "Settings", curses.color_pair(1)|curses.A_BOLD)
        
        current_y = TOP_PAD + 3
        for i, (label, section_editor) in enumerate(self.sections):
            # Add spacing before subtitles (but not if it's the first item, though usually it won't be)
            if section_editor is None and i > 0:
                current_y += 1

            y = current_y
            current_y += 1
            
            style = curses.color_pair(4)
            prefix = "  "
            
            if section_editor is None:
                # Subtitle string - match Title impact
                TUI.safe_addstr(self.scr, y, LEFT_PAD, label, curses.color_pair(1)|curses.A_BOLD)
                continue

            if i == self.sidebar_idx:
                if self.active_pane == 'sidebar':
                    style = curses.color_pair(3)|curses.A_BOLD
                    prefix = "▶ "
                else:
                    style = curses.color_pair(4)|curses.A_REVERSE
            
            TUI.safe_addstr(self.scr, y, LEFT_PAD, prefix + label, style)
            
            # Update Indicator
            has_update = False
            outdated = getattr(self.module_editor, 'outdated_modules', set())
            
            if label == "Modules":
                 if outdated:
                     has_update = True
            elif hasattr(section_editor, 'module_name'):
                 if section_editor.module_name in outdated:
                     has_update = True
            
            if has_update:
                TUI.safe_addstr(self.scr, y, LEFT_PAD + len(prefix + label) + 1, "[U]", curses.color_pair(3)|curses.A_BOLD)

    def discover_modules(self, scr):
        # Scan user modules
        modules_dir = BASE_DIR / 'templates/module'
        if modules_dir.exists():
            for d in sorted(modules_dir.iterdir()):
                if d.is_dir() and d.name != 'core': # Skip core dir itself
                    bp = d / 'blueprint.json'
                    if bp.exists():
                        editor = BlueprintEditor(scr, d.name, bp)
                        self.sections.append((d.name.title(), editor))

        # Scan core modules
        core_dir = modules_dir / 'core'
        if core_dir.exists():
            for d in sorted(core_dir.iterdir()):
                if d.is_dir():
                    bp = d / 'blueprint.json'
                    if bp.exists():
                        editor = BlueprintEditor(scr, d.name, bp)
                        self.sections.append((d.name.title(), editor))

    def save(self):
        for _, editor in self.sections:
            if editor.modified:
                editor.save()
        return True

    def _draw_content(self, h, w):
        editor = self.sections[self.sidebar_idx][1]
        
        # Create a subwindow for the content
        # y, x, h, w
        # Content area starts at sidebar_width + 1
        content_x = self.sidebar_width + 1
        content_w = w - content_x
        
        # We need to hack the editor's scr to be our subwindow temporarily
        # OR we pass the offsets to the editor. 
        # Since we can't easily create a persistent subwindow that survives refresh easily without flickering,
        # let's try creating a derived window.
        
        try:
             # derwin(nlines, ncols, begin_y, begin_x)
            sub = self.scr.subwin(h, content_w, 0, content_x)
            sub.keypad(1)  # Enable keypad for arrow keys
            editor.scr = sub
            editor.refresh()
        except Exception:
            # Fallback if window creation fails
            pass
