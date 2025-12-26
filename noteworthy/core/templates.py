import urllib.request
import urllib.parse
import json
import curses
import shutil
from pathlib import Path
from ..config import SCHEMES_DIR
from ..tui.base import TUI

def restore_templates(scr):
    """Restore missing templates and config files from GitHub."""
    # User config files that should NOT be overwritten if they exist locally
    USER_CONFIG_FILES = {
        'config/metadata.json',
        'config/constants.json',
        'config/hierarchy.json',
        'config/snippets.typ',
        'config/preface.typ',
    }
    
    # OPTIMIZATION: Check if templates already exist locally to avoid network delay
    if Path('templates/templater.typ').exists():
        return

    try:
        api_url = 'https://api.github.com/repos/sihooleebd/noteworthy/git/trees/master?recursive=1'
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Noteworthy-Builder'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        if 'tree' not in data:
            return
            
        def fetch_content(path):
            safe_path = urllib.parse.quote(path)
            url = f'https://raw.githubusercontent.com/sihooleebd/noteworthy/master/{safe_path}'
            with urllib.request.urlopen(url, timeout=10) as response:
                return response.read()

        missing_files = []
        for item in data['tree']:
            if item['type'] != 'blob':
                continue
                
            path_str = item['path']
            
            # Handle templates/ files
            if path_str.startswith('templates/'):
                local_path = Path(path_str)
                if not local_path.exists():
                    missing_files.append(path_str)
                continue
            
            # Handle config/ files
            if path_str.startswith('config/'):
                local_path = Path(path_str)
                
                # Skip user config files if they exist
                if path_str in USER_CONFIG_FILES:
                    if not local_path.exists():
                        # Create blank user files
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                        if path_str.endswith('.json'):
                            local_path.write_text('{}')
                        elif path_str == 'config/snippets.typ':
                            local_path.write_text('// Custom snippets - define your own shortcuts here\n')
                        else:
                            local_path.write_text('')
                    continue
                
                # Handle schemes - individual theme files in config/schemes/data/
                if path_str.startswith('config/schemes/data/') and path_str.endswith('.json'):
                    if not local_path.exists():
                        missing_files.append(path_str)
                    continue
                    
                # Handle names.json manifest (can be regenerated, skip)
                if path_str == 'config/schemes/names.json':
                    continue
                    
                # Other config files
                if not local_path.exists():
                    missing_files.append(path_str)
                    
        if not missing_files:
            return

        scr.clear()
        h, w = scr.getmaxyx()
        msg = f'Restoring {len(missing_files)} missing files...'
        TUI.safe_addstr(scr, h // 2 + 2, (w - len(msg)) // 2, msg, curses.color_pair(4))
        scr.refresh()
        
        for fpath in missing_files:
            try:
                content = fetch_content(fpath)
                local_path = Path(fpath)
                local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(content)
            except:
                pass
                
        msg = 'Restoration complete!'
        TUI.safe_addstr(scr, h // 2 + 3, (w - len(msg)) // 2, msg, curses.color_pair(2))
        scr.refresh()
        curses.napms(1000)
    except Exception:
        pass