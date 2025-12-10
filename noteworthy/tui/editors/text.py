import curses
from pathlib import Path
from ..base import BaseEditor, TUI
from ..keybinds import KeyBind, NavigationBind, ConfirmBind
from ...utils import register_key, handle_key_event

class TextEditor(BaseEditor):

    def __init__(self, scr, filepath=None, initial_text=None, title='Text Editor'):
        super().__init__(scr, title)
        self.filepath = Path(filepath) if filepath else None
        if initial_text is not None:
            self.lines = initial_text.split('\n')
        elif self.filepath and self.filepath.exists():
            self.lines = self.filepath.read_text().split('\n')
        else:
            self.lines = ['']
        self.cy, self.cx = (0, 0)
        self.scroll_y = 0
        self.preferred_x = 0
        
        # Register Bindings
        register_key(self.keymap, NavigationBind('UP', self.move_up))
        register_key(self.keymap, NavigationBind('DOWN', self.move_down))
        register_key(self.keymap, NavigationBind('LEFT', self.move_left))
        register_key(self.keymap, NavigationBind('RIGHT', self.move_right))
        register_key(self.keymap, NavigationBind('HOME', self.move_home))
        register_key(self.keymap, NavigationBind('END', self.move_end))
        register_key(self.keymap, NavigationBind('PGUP', self.move_pgup))
        register_key(self.keymap, NavigationBind('PGDN', self.move_pgdn))
        
        register_key(self.keymap, KeyBind([curses.KEY_BACKSPACE, 127, 8], self.handle_backspace, "Backspace"))
        register_key(self.keymap, KeyBind([curses.KEY_DC], self.handle_delete, "Delete"))
        register_key(self.keymap, ConfirmBind(self.handle_enter))
        register_key(self.keymap, KeyBind(9, self.handle_tab, "Tab"))
        register_key(self.keymap, KeyBind(24, self.do_export, "Export")) # Ctrl+X
        register_key(self.keymap, KeyBind(12, self.do_import, "Import")) # Ctrl+L
        
        # Override Exit to handle return value behavior
        # We replace the default ExitBind from BaseEditor
        register_key(self.keymap, KeyBind(27, self.do_exit_text, "Save & Exit"))

    def do_exit_text(self, ctx=None):
        curses.curs_set(0)
        if self.modified:
             self.save()
        return 'EXIT_WITH_CONTENT'

    def save(self):
        if self.filepath:
            try:
                self.filepath.write_text('\n'.join(self.lines))
                self.modified = False
                return True
            except:
                return False
        return True

    def _load(self):
        if self.filepath and self.filepath.exists():
            self.lines = self.filepath.read_text().split('\n')
        self.refresh()

    def refresh(self):
        h, w = TUI.get_dims(self.scr)
        self.scr.clear()
        
        title_str = f"{self.title}{(' *' if self.modified else '')}"
        _, tx = TUI.center(self.scr, content_w=len(title_str))
        TUI.safe_addstr(self.scr, 0, tx, title_str, curses.color_pair(1) | curses.A_BOLD)
        
        visual_lines = self._get_visual_lines(w - 5)
        vcy = 0
        for i, (text, l_idx, start_idx) in enumerate(visual_lines):
            if l_idx == self.cy:
                is_last_chunk = True
                if i + 1 < len(visual_lines) and visual_lines[i + 1][1] == l_idx:
                    is_last_chunk = False
                if self.cx >= start_idx and (self.cx < start_idx + len(text) or (self.cx == start_idx + len(text) and is_last_chunk)):
                    vcy = i
                    break
        if vcy < self.scroll_y:
            self.scroll_y = vcy
        elif vcy >= self.scroll_y + (h - 5):
            self.scroll_y = vcy - (h - 6)
        for i in range(h - 5):
            idx = self.scroll_y + i
            if idx >= len(visual_lines):
                break
            text, l_idx, start_idx = visual_lines[idx]
            y = i + 2
            if start_idx == 0:
                TUI.safe_addstr(self.scr, y, 0, f'{l_idx + 1:3d} ', curses.color_pair(4) | curses.A_DIM)
            else:
                TUI.safe_addstr(self.scr, y, 0, '    · ', curses.color_pair(4) | curses.A_DIM)
            TUI.safe_addstr(self.scr, y, 6, text)
        footer = 'Esc: Save & Exit  ^X: Export  ^L: Import'
        _, fx = TUI.center(self.scr, content_w=len(footer))
        TUI.safe_addstr(self.scr, h - 1, fx, footer, curses.color_pair(4) | curses.A_DIM)
        
        curses.curs_set(1)
        cur_y = vcy - self.scroll_y + 3 # +2 margin +1 safe_addstr offset
        cur_x = 7 + (self.cx - visual_lines[vcy][2])
        if 0 <= cur_y < h and 0 <= cur_x < w:
            self.scr.move(cur_y, cur_x)
        self.scr.refresh()

    def _get_visual_lines(self, width):
        visual_lines = []
        for l_idx, line in enumerate(self.lines):
            if not line:
                visual_lines.append(('', l_idx, 0))
                continue
            i = 0
            while i < len(line):
                chunk = line[i:i + width]
                if len(chunk) < width:
                    visual_lines.append((chunk, l_idx, i))
                    i += len(chunk)
                else:
                    last_space = chunk.rfind(' ')
                    if last_space != -1:
                        visual_lines.append((chunk[:last_space], l_idx, i))
                        i += last_space + 1
                    else:
                        visual_lines.append((chunk, l_idx, i))
                        i += width
        return visual_lines

    def run(self):
        TUI.disable_flow_control()
        self.refresh()
        self.refresh()
        while True:
            if not TUI.check_terminal_size(self.scr):
                return None
            k = self.scr.getch()
            
            # Delegate to KeyHandler
            handled, res = handle_key_event(k, self.keymap, self)
            if handled:
                if res == 'EXIT_WITH_CONTENT':
                    return '\n'.join(self.lines) if not self.filepath else None
            elif 32 <= k <= 126:
                self.handle_char(k)
            
            self.refresh()

    def handle_char(self, k):
        self.lines[self.cy] = self.lines[self.cy][:self.cx] + chr(k) + self.lines[self.cy][self.cx:]
        self.cx += 1
        self.modified = True
        
    def handle_tab(self, ctx):
        self.lines[self.cy] = self.lines[self.cy][:self.cx] + '    ' + self.lines[self.cy][self.cx:]
        self.cx += 4
        self.modified = True

    def handle_enter(self, ctx):
        self.lines.insert(self.cy + 1, self.lines[self.cy][self.cx:])
        self.lines[self.cy] = self.lines[self.cy][:self.cx]
        self.cy += 1
        self.cx = 0
        self.modified = True

    def handle_backspace(self, ctx):
        if self.cx > 0:
            self.lines[self.cy] = self.lines[self.cy][:self.cx - 1] + self.lines[self.cy][self.cx:]
            self.cx -= 1
            self.modified = True
        elif self.cy > 0:
            pl = len(self.lines[self.cy - 1])
            self.lines[self.cy - 1] += self.lines[self.cy]
            del self.lines[self.cy]
            self.cy -= 1
            self.cx = pl
            self.modified = True

    def handle_delete(self, ctx):
        if self.cx < len(self.lines[self.cy]):
            self.lines[self.cy] = self.lines[self.cy][:self.cx] + self.lines[self.cy][self.cx + 1:]
            self.modified = True
        elif self.cy < len(self.lines) - 1:
            self.lines[self.cy] += self.lines[self.cy + 1]
            del self.lines[self.cy + 1]
            self.modified = True

    def _get_visual_info(self):
        visual_lines = self._get_visual_lines(self.scr.getmaxyx()[1] - 5)
        # Find current visual cursor y (vcy)
        vcy = 0
        for i, (text, l_idx, start_idx) in enumerate(visual_lines):
            if l_idx == self.cy:
                is_last_chunk = True
                if i + 1 < len(visual_lines) and visual_lines[i + 1][1] == l_idx:
                    is_last_chunk = False
                if self.cx >= start_idx and (self.cx < start_idx + len(text) or (self.cx == start_idx + len(text) and is_last_chunk)):
                    vcy = i
                    break
        return visual_lines, vcy

    def move_up(self, ctx):
        visual_lines, vcy = self._get_visual_info()
        if vcy > 0:
            target_vcy = vcy - 1
            t_text, t_lidx, t_start = visual_lines[target_vcy]
            curr_vx = self.cx - visual_lines[vcy][2]
            self.cy = t_lidx
            self.cx = t_start + min(curr_vx, len(t_text))

    def move_down(self, ctx):
        visual_lines, vcy = self._get_visual_info()
        if vcy < len(visual_lines) - 1:
            target_vcy = vcy + 1
            t_text, t_lidx, t_start = visual_lines[target_vcy]
            curr_vx = self.cx - visual_lines[vcy][2]
            self.cy = t_lidx
            self.cx = t_start + min(curr_vx, len(t_text))
            
    def move_pgup(self, ctx):
        h, _ = self.scr.getmaxyx()
        for _ in range(h - 5): self.move_up(ctx)
        
    def move_pgdn(self, ctx):
        h, _ = self.scr.getmaxyx()
        for _ in range(h - 5): self.move_down(ctx)

    def move_left(self, ctx):
        if self.cx > 0:
            self.cx -= 1
        elif self.cy > 0:
            self.cy -= 1
            self.cx = len(self.lines[self.cy])

    def move_right(self, ctx):
        if self.cx < len(self.lines[self.cy]):
            self.cx += 1
        elif self.cy < len(self.lines) - 1:
            self.cy += 1
            self.cx = 0

    def move_home(self, ctx):
        self.cx = 0

    def move_end(self, ctx):
        self.cx = len(self.lines[self.cy])