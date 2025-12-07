import urllib.request
import urllib.parse
import json
import curses
import shutil
from pathlib import Path
from ..config import SCHEMES_FILE
from ..tui.base import TUI

def restore_templates(scr):
    EXCLUDE_FILES = {'templates/config/config.json', 'templates/config/hierarchy.json'}
    try:
        api_url = 'https://api.github.com/repos/sihooleebd/noteworthy/git/trees/master?recursive=1'
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Noteworthy-Builder'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        if 'tree' not in data:
            return
        missing_files = []
        for item in data['tree']:
            if item['type'] == 'blob' and item['path'].startswith('templates/'):
                path_str = item['path']
                if path_str in EXCLUDE_FILES:
                    continue
                if path_str == 'templates/config/preface.typ':
                    local_path = Path(path_str)
                    if not local_path.exists():
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                        local_path.write_text('')
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
        base_raw_url = 'https://raw.githubusercontent.com/sihooleebd/noteworthy/master/'
        for fpath in missing_files:
            local_path = Path(fpath)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path = urllib.parse.quote(fpath)
            file_url = f'{base_raw_url}{safe_path}'
            with urllib.request.urlopen(file_url, timeout=10) as response, open(local_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        msg = 'Restoration complete!'
        TUI.safe_addstr(scr, h // 2 + 3, (w - len(msg)) // 2, msg, curses.color_pair(2))
        scr.refresh()
        curses.napms(1000)
    except Exception:
        pass