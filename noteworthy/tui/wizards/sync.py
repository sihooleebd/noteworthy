import curses
import json
from pathlib import Path
from ..base import TUI
from ...config import HIERARCHY_FILE, INDEXIGNORE_FILE
from ..components.common import LineEditor
from ...core.sync import sync_hierarchy_with_content

class SyncWizard:
    def __init__(self, scr):
        self.scr = scr
        self.hierarchy = json.loads(HIERARCHY_FILE.read_text())
        self.modified = False
        
    def run(self):
        # We run the sync check loop until no issues or user cancels
        while True:
            missing, new_files = sync_hierarchy_with_content()
            
            # Filter ignored files from new_files
            ignored = []
            if INDEXIGNORE_FILE.exists():
                ignored = [l.strip() for l in INDEXIGNORE_FILE.read_text().splitlines() if l.strip()]
            new_files = [f for f in new_files if f not in ignored]
            
            if not missing and not new_files:
                return self.modified

            # Sort issues for stable UI
            issues = []
            for m in missing: issues.append(('missing', m))
            for n in new_files: issues.append(('new', n))
            
            if not issues: return self.modified
            
            # Handle first issue
            issue_type, path_str = issues[0]
            
            if issue_type == 'missing':
                if not self.handle_missing(path_str, new_files):
                    return self.modified # Cancelled
            else:
                if not self.handle_new(path_str):
                    return self.modified # Cancelled
                    
            # Reload hierarchy in case it changed
            # (Note: handle_* methods are responsible for updating self.hierarchy variable AND file)
            self.hierarchy = json.loads(HIERARCHY_FILE.read_text())

    def handle_missing(self, fpath, available_candidates):
        path = Path(fpath)
        ch_id = path.parent.name
        pg_id = path.stem
        
        # Find the hierarchy entry responsible for this
        target_ch = None
        target_pg = None
        target_ch_idx = -1
        target_pg_idx = -1
        
        for ci, ch in enumerate(self.hierarchy):
            if str(ch.get('id', ci)) == ch_id:
                target_ch = ch
                target_ch_idx = ci
                for pi, pg in enumerate(ch.get('pages', [])):
                    if str(pg.get('id', pi)) == pg_id:
                        target_pg = pg
                        target_pg_idx = pi
                        break
                break
                
        if not target_pg:
            # Should not happen if core.sync is correct
            return True # Skip
            
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        TUI.draw_box(self.scr, h//2 - 6, w//2 - 30, 12, 60, "Missing File Detected")
        
        msg = f"Expected: {fpath}"
        TUI.safe_addstr(self.scr, h//2 - 4, (w-len(msg))//2, msg, curses.color_pair(1)|curses.A_BOLD)
        
        TUI.safe_addstr(self.scr, h//2 - 2, w//2 - 28, "Actions:", curses.color_pair(4))
        TUI.safe_addstr(self.scr, h//2 - 1, w//2 - 26, "[C] Create this file (scaffold)", curses.color_pair(2))
        TUI.safe_addstr(self.scr, h//2 + 0, w//2 - 26, "[M] Map to existing file...", curses.color_pair(2))
        TUI.safe_addstr(self.scr, h//2 + 1, w//2 - 26, "[R] Rename entry (change ID)", curses.color_pair(2))
        TUI.safe_addstr(self.scr, h//2 + 2, w//2 - 26, "[D] Delete entry from hierarchy", curses.color_pair(1))
        TUI.safe_addstr(self.scr, h//2 + 3, w//2 - 26, "[S] Skip / Ignore for now", curses.color_pair(4))
        
        while True:
            k = self.scr.getch()
            if k in (ord('c'), ord('C')):
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('#import "../../templates/templater.typ": *\n\nWrite your content here.')
                    self.modified = True
                    return True
                except:
                    return False
                    
            elif k in (ord('m'), ord('M')):
                # Show list of available new_files to map to
                if not available_candidates:
                    TUI.safe_addstr(self.scr, h//2 + 4, w//2 - 20, "No unmapped files found!", curses.color_pair(1))
                    curses.napms(1000)
                    continue
                    
                sel = self.select_file(available_candidates, "Select file to map to:")
                if sel:
                    # Update hierarchy ID to match selected file
                    new_path = Path(sel)
                    new_pg_id = new_path.stem
                    # We assume chapter handling is correct or we move? 
                    # If strictly mapping file ID:
                    self.hierarchy[target_ch_idx]['pages'][target_pg_idx]['id'] = new_pg_id
                    HIERARCHY_FILE.write_text(json.dumps(self.hierarchy, indent=4))
                    self.modified = True
                    return True
                else:
                    self.scr.clear() # Redraw needed
                    return self.handle_missing(fpath, available_candidates) # Recursion/Retry
                    
            elif k in (ord('r'), ord('R')):
                # Rename ID manually
                new_id = LineEditor(self.scr, initial_value=pg_id, title="Enter New File Name (ID)").run()
                if new_id and new_id != pg_id:
                    self.hierarchy[target_ch_idx]['pages'][target_pg_idx]['id'] = new_id
                    
                    # Logic: If we rename the ENTRY, do we create the file? 
                    # Usually yes, user wants to rename expectations.
                    # check if new file exists?
                    new_f = path.parent / f"{new_id}.typ"
                    if new_f.exists():
                        pass # Mapped!
                    else:
                        # Create it? Or let next loop catch it?
                        # Let's create it for convenience
                        if TUI.prompt_confirm(self.scr, f"Create {new_id}.typ?"):
                            new_f.write_text('#import "../../templates/templater.typ": *\n\nWrite your content here.')
                            
                    HIERARCHY_FILE.write_text(json.dumps(self.hierarchy, indent=4))
                    self.modified = True
                    return True
                return True
                
            elif k in (ord('d'), ord('D')):
                del self.hierarchy[target_ch_idx]['pages'][target_pg_idx]
                HIERARCHY_FILE.write_text(json.dumps(self.hierarchy, indent=4))
                self.modified = True
                return True
                
            elif k in (ord('s'), ord('S')):
                return True
            
            elif k == 27: # Esc
                return False

    def handle_new(self, fpath):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        
        TUI.draw_box(self.scr, h//2 - 5, w//2 - 30, 10, 60, "Unmapped File Detected")
        
        msg = f"Found: {fpath}"
        TUI.safe_addstr(self.scr, h//2 - 3, (w-len(msg))//2, msg, curses.color_pair(2)|curses.A_BOLD)
        
        TUI.safe_addstr(self.scr, h//2 - 1, w//2 - 28, "Actions:", curses.color_pair(4))
        TUI.safe_addstr(self.scr, h//2 + 0, w//2 - 26, "[A] Add as new Page", curses.color_pair(2))
        TUI.safe_addstr(self.scr, h//2 + 1, w//2 - 26, "[I] Add to Ignore List", curses.color_pair(1))
        TUI.safe_addstr(self.scr, h//2 + 2, w//2 - 26, "[S] Skip", curses.color_pair(4))
        
        while True:
            k = self.scr.getch()
            if k in (ord('a'), ord('A')):
                path = Path(fpath)
                ch_dir = path.parent.name
                pg_id = path.stem
                
                # Find chapter
                target_ch = None
                for ch in self.hierarchy:
                    if str(ch.get('id', '')) == ch_dir:
                        target_ch = ch
                        break
                
                if not target_ch:
                    target_ch = {'id': ch_dir, 'title': f'Chapter {ch_dir}', 'pages': []}
                    self.hierarchy.append(target_ch)
                    
                target_ch['pages'].append({'id': pg_id, 'title': f'Section {pg_id}'})
                HIERARCHY_FILE.write_text(json.dumps(self.hierarchy, indent=4))
                self.modified = True
                return True
                
            elif k in (ord('i'), ord('I')):
                with open(INDEXIGNORE_FILE, 'a') as f:
                    f.write(f'\n{fpath}')
                self.modified = True
                return True
                
            elif k in (ord('s'), ord('S')):
                return True
                
            elif k == 27:
                return False

    def select_file(self, files, prompt):
        # reuse list editor logic or simple menu?
        # Simple menu for now
        from ..menus import Menu
        # files is list of strings
        mapped = [{'label': f, 'value': f} for f in files]
        return Menu(self.scr, mapped, prompt).run()
