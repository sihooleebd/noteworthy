import curses
from pathlib import Path
from ..base import BaseEditor, TUI

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
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        title_str = f"{self.title}{(' *' if self.modified else '')}"
        TUI.safe_addstr(self.scr, 0, (w - len(title_str)) // 2, title_str, curses.color_pair(1) | curses.A_BOLD)
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
        elif vcy >= self.scroll_y + (h - 2):
            self.scroll_y = vcy - (h - 3)
        for i in range(h - 4):
            idx = self.scroll_y + i
            if idx >= len(visual_lines):
                break
            text, l_idx, start_idx = visual_lines[idx]
            y = i + 1
            if start_idx == 0:
                TUI.safe_addstr(self.scr, y, 0, f'{l_idx + 1:3d} ', curses.color_pair(4) | curses.A_DIM)
            else:
                TUI.safe_addstr(self.scr, y, 0, '    · ', curses.color_pair(4) | curses.A_DIM)
            TUI.safe_addstr(self.scr, y, 6, text)
        footer = 'Esc: Save & Exit  ^X: Export  ^L: Import'
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        curses.curs_set(1)
        cur_y = vcy - self.scroll_y + 2
        cur_x = 6 + (self.cx - visual_lines[vcy][2])
        if 0 <= cur_y < h - 1 and 0 <= cur_x < w:
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
            if k == 27:
                curses.curs_set(0)
                if self.modified:
                    self.save()
                return '\n'.join(self.lines) if not self.filepath else None
            else:
                self._handle_input(k)
            self.refresh()

    def _handle_input(self, k):
        if k == 24: # Ctrl+X
            self.do_export()
            return True
        elif k == 12: # Ctrl+L
            self.do_import()
            return True
        
        visual_lines = self._get_visual_lines(self.scr.getmaxyx()[1] - 5)
        if k == curses.KEY_UP:
            vcy = 0
            for i, (text, l_idx, start_idx) in enumerate(visual_lines):
                if l_idx == self.cy:
                    is_last_chunk = True
                    if i + 1 < len(visual_lines) and visual_lines[i + 1][1] == l_idx:
                        is_last_chunk = False
                    if self.cx >= start_idx and (self.cx < start_idx + len(text) or (self.cx == start_idx + len(text) and is_last_chunk)):
                        vcy = i
                        break
            if vcy > 0:
                target_vcy = vcy - 1
                t_text, t_lidx, t_start = visual_lines[target_vcy]
                curr_vx = self.cx - visual_lines[vcy][2]
                self.cy = t_lidx
                self.cx = t_start + min(curr_vx, len(t_text))
        elif k == curses.KEY_DOWN:
            vcy = 0
            for i, (text, l_idx, start_idx) in enumerate(visual_lines):
                if l_idx == self.cy:
                    is_last_chunk = True
                    if i + 1 < len(visual_lines) and visual_lines[i + 1][1] == l_idx:
                        is_last_chunk = False
                    if self.cx >= start_idx and (self.cx < start_idx + len(text) or (self.cx == start_idx + len(text) and is_last_chunk)):
                        vcy = i
                        break
            if vcy < len(visual_lines) - 1:
                target_vcy = vcy + 1
                t_text, t_lidx, t_start = visual_lines[target_vcy]
                curr_vx = self.cx - visual_lines[vcy][2]
                self.cy = t_lidx
                self.cx = t_start + min(curr_vx, len(t_text))
        elif k == curses.KEY_LEFT:
            if self.cx > 0:
                self.cx -= 1
            elif self.cy > 0:
                self.cy -= 1
                self.cx = len(self.lines[self.cy])
        elif k == curses.KEY_RIGHT:
            if self.cx < len(self.lines[self.cy]):
                self.cx += 1
            elif self.cy < len(self.lines) - 1:
                self.cy += 1
                self.cx = 0
        elif k == curses.KEY_HOME:
            self.cx = 0
        elif k == curses.KEY_END:
            self.cx = len(self.lines[self.cy])
        elif k in (curses.KEY_BACKSPACE, 127, 8):
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
        elif k == curses.KEY_DC:
            if self.cx < len(self.lines[self.cy]):
                self.lines[self.cy] = self.lines[self.cy][:self.cx] + self.lines[self.cy][self.cx + 1:]
                self.modified = True
            elif self.cy < len(self.lines) - 1:
                self.lines[self.cy] += self.lines[self.cy + 1]
                del self.lines[self.cy + 1]
                self.modified = True
        elif k in (ord('\n'), 10):
            self.lines.insert(self.cy + 1, self.lines[self.cy][self.cx:])
            self.lines[self.cy] = self.lines[self.cy][:self.cx]
            self.cy += 1
            self.cx = 0
            self.modified = True
        elif k == 9:
            self.lines[self.cy] = self.lines[self.cy][:self.cx] + '    ' + self.lines[self.cy][self.cx:]
            self.cx += 4
            self.modified = True
        elif 32 <= k <= 126:
            self.lines[self.cy] = self.lines[self.cy][:self.cx] + chr(k) + self.lines[self.cy][self.cx:]
            self.cx += 1
            self.modified = True
        curses.curs_set(0)
        return True