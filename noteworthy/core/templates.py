import urllib.request
import urllib.parse
import json
import curses
import shutil
from pathlib import Path
from ..config import SCHEMES_FILE
from ..tui.base import TUI

def restore_templates(scr):
    EXCLUDE_FILES = {
        'templates/config/config.json',
        'templates/config/hierarchy.json',
        'templates/config/snippets.typ',
    }
    
    # OPTIMIZATION: Check if templates already exist locally to avoid network delay
    # We check a core file that should always be present
    if Path('templates/templater.typ').exists():
        return

    try:
        api_url = 'https://api.github.com/repos/sihooleebd/noteworthy/git/trees/master?recursive=1'
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Noteworthy-Builder'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        if 'tree' not in data:
            return
        # Helper to fetch file content
        def fetch_content(path):
            safe_path = urllib.parse.quote(path)
            url = f'https://raw.githubusercontent.com/sihooleebd/noteworthy/master/{safe_path}'
            with urllib.request.urlopen(url, timeout=10) as response:
                return response.read()

        missing_files = []
        for item in data['tree']:
            if item['type'] == 'blob' and item['path'].startswith('templates/'):
                path_str = item['path']
                
                # Special handling for schemes.json (Smart Merge)
                if path_str == 'templates/config/schemes.json':
                    local_path = Path(path_str)
                    try:
                        remote_json = json.loads(fetch_content(path_str))
                        if local_path.exists():
                            try:
                                local_json = json.loads(local_path.read_text())
                            except:
                                local_json = {}
                        else:
                            local_json = {}
                        
                        # Merge: Add missing defaults, preserve local changes/customs
                        modified = False
                        for name, scheme in remote_json.items():
                            if name not in local_json:
                                local_json[name] = scheme
                                modified = True
                        
                        if modified or not local_path.exists():
                            local_path.parent.mkdir(parents=True, exist_ok=True)
                            local_path.write_text(json.dumps(local_json, indent=4))
                    except:
                        pass
                    continue

                if path_str in EXCLUDE_FILES:
                    continue
                    
                if path_str == 'templates/config/preface.typ':
                    local_path = Path(path_str)
                    if not local_path.exists():
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                        local_path.write_text('')
                    continue
                    
                if path_str == 'templates/config/snippets.typ':
                    local_path = Path(path_str)
                    if not local_path.exists():
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                        local_path.write_text('// Custom snippets - define your own shortcuts here\n')
                    continue
                    
                local_path = Path(path_str)
                if not local_path.exists():
                    missing_files.append(path_str)
                    
        if not missing_files:
            return

        scr.clear()
        h, w = scr.getmaxyx()
        msg = f'Restoring {len(missing_files)} missing templates...'
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