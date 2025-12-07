import curses
import json
from pathlib import Path
from ..base import TUI
from ...config import HIERARCHY_FILE, CONFIG_FILE
from ...utils import load_config_safe, get_formatted_name

class SyncWizard:

    def __init__(self, scr, missing_files, new_files):
        self.scr = scr
        self.missing_files = missing_files
        self.new_files = new_files
        self.config = load_config_safe()
        try:
            self.hierarchy = json.loads(HIERARCHY_FILE.read_text())
        except:
            self.hierarchy = []

    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        TUI.safe_addstr(self.scr, 2, (w - 25) // 2, 'HIERARCHY SYNC REQUIRED', curses.color_pair(6) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, 3, (w - 45) // 2, 'The hierarchy.json does not match your content folder.', curses.color_pair(4))
        col_w = (w - 8) // 2
        left_x = 2
        right_x = left_x + col_w + 4
        list_h = h - 13
        TUI.draw_box(self.scr, 5, left_x, list_h + 2, col_w, f' Missing on Disk ({len(self.missing_files)}) ')
        for i, f in enumerate(self.missing_files[:list_h]):
            name = get_formatted_name(f, self.hierarchy, self.config)
            TUI.safe_addstr(self.scr, 6 + i, left_x + 2, f'- {name} ({f})', curses.color_pair(4))
        TUI.draw_box(self.scr, 5, right_x, list_h + 2, col_w, f' New on Disk ({len(self.new_files)}) ')
        for i, f in enumerate(self.new_files[:list_h]):
            name = get_formatted_name(f, self.hierarchy, self.config)
            TUI.safe_addstr(self.scr, 6 + i, right_x + 2, f'+ {name} ({f})', curses.color_pair(2))
        opts_y = h - 5
        TUI.safe_addstr(self.scr, opts_y, 4, '[A] Adopt Disk State (Update Hierarchy)', curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, opts_y + 1, 8, 'Removes missing, Adds new', curses.color_pair(4))
        TUI.safe_addstr(self.scr, opts_y, w // 2 + 4, '[B] Create Missing Files', curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, opts_y + 1, w // 2 + 8, 'Creates scaffold for missing files', curses.color_pair(4))
        TUI.safe_addstr(self.scr, opts_y + 3, 4, '[D] Delete Extra Files', curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, opts_y + 4, 8, 'Deletes files not in hierarchy', curses.color_pair(4))
        TUI.safe_addstr(self.scr, h - 3, (w - 20) // 2, 'Esc: Cancel  Q: Quit', curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()

    def run(self):
        while True:
            if not TUI.check_terminal_size(self.scr):
                return None
            self.refresh()
            k = self.scr.getch()
            if k == 27 or k == ord('q'):
                return None
            if k in (ord('a'), ord('A')):
                return self.adopt_disk()
            elif k in (ord('b'), ord('B')):
                return self.adopt_hierarchy()
            elif k in (ord('d'), ord('D')):
                return self.delete_extra()

    def adopt_disk(self):
        try:
            new_hierarchy = []
            content_dir = Path('content')
            if not content_dir.exists():
                return False
            ch_idxs = []
            for d in content_dir.iterdir():
                if d.is_dir() and d.name.isdigit():
                    ch_idxs.append(int(d.name))
            ch_idxs.sort()
            for i in ch_idxs:
                old_ch = self.hierarchy[i] if i < len(self.hierarchy) else {}
                title = old_ch.get('title', f'Chapter {i + 1}')
                summary = old_ch.get('summary', '')
                pages = []
                ch_dir = content_dir / str(i)
                pg_idxs = []
                for f in ch_dir.glob('*.typ'):
                    if f.stem.isdigit():
                        pg_idxs.append(int(f.stem))
                pg_idxs.sort()
                for j in pg_idxs:
                    old_pg = old_ch.get('pages', [])[j] if 'pages' in old_ch and j < len(old_ch['pages']) else {}
                    pg_title = old_pg.get('title', 'Untitled Section')
                    pages.append({'title': pg_title})
                new_hierarchy.append({'title': title, 'summary': summary, 'pages': pages})
            HIERARCHY_FILE.write_text(json.dumps(new_hierarchy, indent=4))
            return True
        except Exception as e:
            return False

    def adopt_hierarchy(self):
        try:
            for missing in self.missing_files:
                path = Path(missing)
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    path.write_text(f'#import "../../templates/templater.typ": *\n\nWrite your content here.')
            return True
        except:
            return False

    def delete_extra(self):
        try:
            for f in self.new_files:
                path = Path(f)
                if path.exists():
                    path.unlink()
                try:
                    if path.parent.exists() and (not any(path.parent.iterdir())):
                        path.parent.rmdir()
                except:
                    pass
            return True
        except:
            return False