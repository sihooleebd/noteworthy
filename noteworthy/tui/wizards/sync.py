import curses
import json
from pathlib import Path
from ..base import TUI
from ...config import HIERARCHY_FILE, CONFIG_FILE
from ...utils import load_config_safe, get_formatted_name, load_indexignore, save_indexignore

class SyncWizard:

    def __init__(self, scr, missing_files, new_files):
        self.scr = scr
        self.missing_files = missing_files  # In hierarchy but not on disk
        self.new_files = new_files          # On disk but not in hierarchy
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
        list_h = h - 15
        
        # Left column: Missing on disk (in hierarchy but file doesn't exist)
        TUI.draw_box(self.scr, 5, left_x, list_h + 2, col_w, f' Missing on Disk ({len(self.missing_files)}) ')
        for i, f in enumerate(self.missing_files[:list_h]):
            name = get_formatted_name(f, self.hierarchy, self.config)
            TUI.safe_addstr(self.scr, 6 + i, left_x + 2, f'- {name} ({f})', curses.color_pair(4))
        
        # Right column: New on disk (file exists but not in hierarchy)
        TUI.draw_box(self.scr, 5, right_x, list_h + 2, col_w, f' New on Disk ({len(self.new_files)}) ')
        for i, f in enumerate(self.new_files[:list_h]):
            TUI.safe_addstr(self.scr, 6 + i, right_x + 2, f'+ {f}', curses.color_pair(2))
        
        opts_y = h - 7
        
        # Context-sensitive options
        if self.missing_files:
            TUI.safe_addstr(self.scr, opts_y, 4, '[A] Create Missing Files', curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, opts_y + 1, 8, 'Creates scaffold .typ files for entries in hierarchy', curses.color_pair(4))
        
        if self.new_files:
            TUI.safe_addstr(self.scr, opts_y, w // 2 + 4, '[B] Add to Hierarchy', curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, opts_y + 1, w // 2 + 8, 'Adds new disk files to hierarchy.json', curses.color_pair(4))
        
        if self.missing_files:
            TUI.safe_addstr(self.scr, opts_y + 2, 4, '[R] Remove from Hierarchy', curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, opts_y + 3, 8, 'Removes missing entries from hierarchy', curses.color_pair(4))
        
        if self.new_files:
            TUI.safe_addstr(self.scr, opts_y + 2, w // 2 + 4, '[I] Ignore New Files', curses.color_pair(1) | curses.A_BOLD)
            TUI.safe_addstr(self.scr, opts_y + 3, w // 2 + 8, 'Adds new files to .indexignore', curses.color_pair(4))
        
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
            if k in (ord('a'), ord('A')) and self.missing_files:
                return self.create_missing_files()
            elif k in (ord('b'), ord('B')) and self.new_files:
                return self.add_to_hierarchy()
            elif k in (ord('r'), ord('R')) and self.missing_files:
                return self.remove_from_hierarchy()
            elif k in (ord('i'), ord('I')) and self.new_files:
                return self.add_to_ignored()

    def create_missing_files(self):
        """Create .typ scaffold files for entries in hierarchy that don't exist on disk."""
        from ...core.fs_sync import ensure_content_structure
        try:
            ensure_content_structure(self.hierarchy)
            return True
        except:
            return False

    def add_to_hierarchy(self):
        """Add new disk files to hierarchy.json, preserving existing numbering."""
        try:
            content_dir = Path('content')
            if not content_dir.exists():
                return False
            
            # Build new hierarchy from disk, preserving existing metadata
            ch_idxs = []
            for d in content_dir.iterdir():
                if d.is_dir() and d.name.isdigit():
                    ch_idxs.append(int(d.name))
            ch_idxs.sort()
            
            new_hierarchy = []
            for i in ch_idxs:
                old_ch = self.hierarchy[i] if i < len(self.hierarchy) else {}
                title = old_ch.get('title', f'Chapter {i + 1}')
                summary = old_ch.get('summary', '')
                # Preserve chapter number if it exists
                ch_number = old_ch.get('number', None)
                
                pages = []
                ch_dir = content_dir / str(i)
                pg_idxs = []
                for f in ch_dir.glob('*.typ'):
                    if f.stem.isdigit():
                        pg_idxs.append(int(f.stem))
                pg_idxs.sort()
                
                old_pages = old_ch.get('pages', [])
                for j in pg_idxs:
                    if j < len(old_pages):
                        # Preserve existing page metadata (title, number, etc.)
                        old_pg = old_pages[j]
                        pages.append(old_pg.copy())
                    else:
                        # New page - create with default title
                        pages.append({'title': 'Untitled Section'})
                
                ch_entry = {'title': title, 'summary': summary, 'pages': pages}
                if ch_number is not None:
                    ch_entry['number'] = ch_number
                new_hierarchy.append(ch_entry)
            
            HIERARCHY_FILE.write_text(json.dumps(new_hierarchy, indent=4))
            return True
        except Exception as e:
            return False

    def remove_from_hierarchy(self):
        """Remove entries from hierarchy that don't have corresponding files on disk."""
        try:
            content_dir = Path('content')
            new_hierarchy = []
            
            for ci, chapter in enumerate(self.hierarchy):
                ch_dir = content_dir / str(ci)
                if not ch_dir.exists():
                    # Skip entire chapter if directory doesn't exist
                    continue
                
                new_pages = []
                for pi, page in enumerate(chapter.get('pages', [])):
                    page_file = ch_dir / f'{pi}.typ'
                    if page_file.exists():
                        new_pages.append(page)
                
                if new_pages:
                    new_ch = chapter.copy()
                    new_ch['pages'] = new_pages
                    new_hierarchy.append(new_ch)
            
            HIERARCHY_FILE.write_text(json.dumps(new_hierarchy, indent=4))
            return True
        except:
            return False

    def add_to_ignored(self):
        """Add new disk files to .indexignore."""
        try:
            ignored = load_indexignore()
            for f in self.new_files:
                # Convert path like content/1/2.typ to ID like 1.2
                path = Path(f)
                if path.stem.isdigit() and path.parent.name.isdigit():
                    file_id = f'{path.parent.name}.{path.stem}'
                    ignored.add(file_id)
            save_indexignore(ignored)
            return True
        except:
            return False