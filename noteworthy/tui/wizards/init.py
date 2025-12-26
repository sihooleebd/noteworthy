import curses
import json
from ..base import TUI
from ...config import METADATA_FILE, CONSTANTS_FILE, LOGO
from ...utils import load_config_safe, save_config, register_key, handle_key_event
from ..editors.schemes import extract_themes
from ..keybinds import KeyBind, NavigationBind, ConfirmBind

class InitWizard:

    def __init__(self, scr):
        self.scr = scr
        themes = extract_themes()
        self.config = {'title': '', 'subtitle': '', 'authors': [], 'affiliation': '', 'logo': None, 'show-solution': True, 'solutions-text': 'Solutions', 'problems-text': 'Problems', 'chapter-name': 'Chapter', 'subchap-name': 'Section', 'font': 'IBM Plex Serif', 'title-font': 'Noto Sans Adlam', 'display-cover': True, 'display-outline': True, 'display-chap-cover': True, 'box-margin': '5pt', 'box-inset': '15pt', 'render-sample-count': 5000, 'render-implicit-count': 100, 'display-mode': 'rose-pine', 'pad-chapter-id': True, 'pad-page-id': True, 'heading-numbering': None}
        self.steps = [('title', 'Document Title', 'Enter the main title of your document:', 'str'), ('subtitle', 'Subtitle', 'Enter a subtitle (optional, press Enter to skip):', 'str'), ('authors', 'Authors', 'Enter author names (comma-separated):', 'list'), ('affiliation', 'Affiliation', 'Enter your organization/affiliation:', 'str'), ('display-mode', 'Color Theme', 'Use ←/→ to select, Enter to confirm:', 'choice', themes), ('font', 'Body Font', 'Enter body font name:', 'str'), ('title-font', 'Title Font', 'Enter title font name:', 'str'), ('chapter-name', 'Chapter Label', "What to call chapters (e.g., 'Chapter', 'Unit'):", 'str'), ('subchap-name', 'Section Label', "What to call sections (e.g., 'Section', 'Lesson'):", 'str')]
        self.current_step = 0
        self.choice_index = 0
        self.input_y = 0
        self.input_x = 0
        input_w = 50
        TUI.init_colors()
        
        self.keymap = {}
        
        register_key(self.keymap, KeyBind(27, self.action_cancel, "Cancel"))
        register_key(self.keymap, KeyBind([curses.KEY_BACKSPACE, 127, 8], self.action_prev, "Previous Step"))
        register_key(self.keymap, ConfirmBind(self.action_next))
        register_key(self.keymap, NavigationBind('LEFT', self.action_choice_left))
        register_key(self.keymap, NavigationBind('RIGHT', self.action_choice_right))
        
    def action_cancel(self, ctx):
        return 'EXIT'

    def action_prev(self, ctx):
        if self.current_step > 0:
            self.current_step -= 1
            if self.steps[self.current_step][3] == 'choice':
                choices = self.steps[self.current_step][4]
                curr = self.config.get(self.steps[self.current_step][0], choices[0])
                self.choice_index = choices.index(curr) if curr in choices else 0

    def action_choice_left(self, ctx):
        step = self.steps[self.current_step]; stype = step[3]
        if stype == 'choice':
            choices = step[4]
            self.choice_index = (self.choice_index - 1) % len(choices)

    def action_choice_right(self, ctx):
        step = self.steps[self.current_step]; stype = step[3]
        if stype == 'choice':
            choices = step[4]
            self.choice_index = (self.choice_index + 1) % len(choices)
            
    def action_next(self, ctx):
        step = self.steps[self.current_step]
        key, stype = (step[0], step[3])
        
        if stype == 'choice':
            choices = step[4]
            self.config[key] = choices[self.choice_index]
            self.current_step += 1
            self.choice_index = 0
        else:
            value = self.get_input()
            if value or key != 'title':
                if stype == 'list':
                    self.config[key] = [s.strip() for s in value.split(',') if s.strip()] if value else []
                else:
                    self.config[key] = value if value else self.config.get(key, '')
                self.current_step += 1
            elif not value and key == 'title':
                h, w = self.scr.getmaxyx()
                TUI.safe_addstr(self.scr, h - 2, (w - 20) // 2, 'Title is required!', curses.color_pair(6) | curses.A_BOLD)
                self.scr.refresh()
                curses.napms(1000)

    def refresh(self):
        h_raw, w_raw = self.scr.getmaxyx()
        h, w = (h_raw - 2, w_raw - 2)
        self.scr.clear()
        layout = 'vert'
        if w > 100:
            layout = 'horz'
        if layout == 'horz':
            lh = len(LOGO)
            ly = max(0, (h - lh) // 2)
            lx = max(0, (w - 16 - 60) // 2)
            for i, line in enumerate(LOGO):
                if ly + i < h:
                    TUI.safe_addstr(self.scr, ly + i, lx, line, curses.color_pair(1) | curses.A_BOLD)
            sy = ly + lh + 2
            footer_y = h - 3
            
            # Use columns if list is too long for vertical space?
            # Or scroll the list if current step is out of view
            max_steps_visible = footer_y - 1 - sy
            if max_steps_visible < 1: max_steps_visible = 1
            
            start_step = 0
            if self.current_step >= max_steps_visible:
                start_step = self.current_step - max_steps_visible + 1
            
            for i in range(min(len(self.steps) - start_step, max_steps_visible)):
                step_idx = start_step + i
                step = self.steps[step_idx]
                y_pos = sy + i
                
                marker = '>' if step_idx == self.current_step else ' '
                style = curses.color_pair(3) | curses.A_BOLD if step_idx == self.current_step else curses.color_pair(4)
                
                if y_pos < footer_y:
                    TUI.safe_addstr(self.scr, y_pos, lx + 2, f'{marker} {step[1]}', style)
            
            dx = lx + 20 + 4
            dw = 55
            dy = max(0, (h - 16) // 2)
            TUI.draw_box(self.scr, dy, dx, 16, dw, 'Setup Wizard')
            step = self.steps[self.current_step]
            key, label, prompt, stype = (step[0], step[1], step[2], step[3])
            TUI.safe_addstr(self.scr, dy + 2, dx + 2, f'Step {self.current_step + 1}/{len(self.steps)}: {label}', curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, dy + 4, dx + 2, prompt[:dw - 4], curses.color_pair(4))
            if stype == 'choice':
                choices = step[4]
                choice_text = f'◀  {choices[self.choice_index]}  ▶'
                TUI.safe_addstr(self.scr, dy + 7, dx + (dw - len(choice_text)) // 2, choice_text, curses.color_pair(5) | curses.A_BOLD)
                dots = ''.join(('●' if i == self.choice_index else '○' for i in range(len(choices))))
                TUI.safe_addstr(self.scr, dy + 8, dx + (dw - len(dots)) // 2, dots, curses.color_pair(4) | curses.A_DIM)
            else:
                curr_val = self.config.get(key, '')
                if isinstance(curr_val, list):
                    curr_val = ', '.join(curr_val)
                if curr_val:
                    TUI.safe_addstr(self.scr, dy + 7, dx + 2, f'Default: {str(curr_val)[:dw - 12]}', curses.color_pair(4) | curses.A_DIM)
            self.input_y, self.input_x, self.input_w = (dy + 10, dx + 2, dw - 4)
            footer = 'Enter:Next  Back:Prev  Esc:Cancel'
            TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        else:
            total_h = 16
            start_y = max(1, (h - total_h) // 2)
            TUI.safe_addstr(self.scr, start_y, (w - 22) // 2, 'NOTEWORTHY SETUP WIZARD', curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, start_y + 1, (w - 40) // 2, "Let's set up your document configuration", curses.color_pair(4) | curses.A_DIM)
            prog = f'Step {self.current_step + 1} of {len(self.steps)}'
            TUI.safe_addstr(self.scr, start_y + 3, (w - len(prog)) // 2, prog, curses.color_pair(5))
            step = self.steps[self.current_step]
            key, label, prompt, stype = (step[0], step[1], step[2], step[3])
            bw = min(60, w - 4)
            bx = (w - bw) // 2
            TUI.draw_box(self.scr, start_y + 5, bx, 7, bw, label)
            TUI.safe_addstr(self.scr, start_y + 6, bx + 2, prompt[:bw - 4], curses.color_pair(4))
            if stype == 'choice':
                choices = step[4]
                choice_text = f'◀  {choices[self.choice_index]}  ▶'
                TUI.safe_addstr(self.scr, start_y + 8, (w - len(choice_text)) // 2, choice_text, curses.color_pair(5) | curses.A_BOLD)
                dots = ''.join(('●' if i == self.choice_index else '○' for i in range(len(choices))))
                TUI.safe_addstr(self.scr, start_y + 9, (w - len(dots)) // 2, dots, curses.color_pair(4) | curses.A_DIM)
                footer = '←→:Select  Enter:Confirm  Backspace:Back  Esc:Cancel'
            else:
                curr_val = self.config.get(key, '')
                if isinstance(curr_val, list):
                    curr_val = ', '.join(curr_val)
                if curr_val:
                    TUI.safe_addstr(self.scr, start_y + 8, bx + 2, f'Default: {str(curr_val)[:bw - 12]}', curses.color_pair(4) | curses.A_DIM)
                footer = 'Enter:Input  Backspace:Back  Esc:Cancel'
            self.input_y, self.input_x, self.input_w = (start_y + 10, bx + 2, bw - 4)
            TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()

    def get_input(self):
        curses.echo()
        curses.curs_set(1)
        y, x = (self.input_y, self.input_x)
        try:
            real_y = y + 1
            real_x = x + 1
            TUI.safe_addstr(self.scr, y, x, ' ' * self.input_w)
            TUI.safe_addstr(self.scr, y, x, '> ', curses.color_pair(3) | curses.A_BOLD)
            self.scr.refresh()
            value = self.scr.getstr(real_y, real_x + 2, self.input_w - 6).decode('utf-8').strip()
        except:
            value = ''
        curses.noecho()
        curses.curs_set(0)
        return value

    def run(self):
        while True:
            if not TUI.check_terminal_size(self.scr):
                return None
            h, w = self.scr.getmaxyx()
            self.scr.clear()
            bh, bw = (8, min(60, w - 4))
            bx, by = ((w - bw) // 2, (h - bh) // 2)
            TUI.draw_box(self.scr, by, bx, bh, bw, ' Welcome ')
            TUI.safe_addstr(self.scr, by + 2, bx + 2, 'welcome to noteworthy!', curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, by + 3, bx + 2, 'We will guide you to initializing your project.', curses.color_pair(4))
            footer = 'Press Enter to begin...'
            TUI.safe_addstr(self.scr, by + 6, bx + (bw - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)
            self.scr.refresh()
            k = self.scr.getch()
            if k == 27:
                return None
            if k in (ord('\n'), 10, curses.KEY_ENTER):
                break
                
        while self.current_step < len(self.steps):
            if not TUI.check_terminal_size(self.scr):
                return None
            self.refresh()
            k = self.scr.getch()
            
            handled, res = handle_key_event(k, self.keymap, self)
            if handled and res == 'EXIT':
                return None
                
        try:
            METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            return save_config(self.config)
        except:
            return None