import curses
import json
from pathlib import Path
from ..base import TUI
from ...config import HIERARCHY_FILE
from ...utils import load_config_safe

class HierarchyWizard:

    def __init__(self, scr):
        self.scr = scr

    def run(self):
        try:
            hierarchy = []
            content_dir = Path('content')
            has_content = False
            if content_dir.exists():
                chapters = {}
                for ch_dir in sorted(content_dir.iterdir()):
                    if not ch_dir.is_dir() or not ch_dir.name.isdigit():
                        continue
                    try:
                        ch_id = ch_dir.name  # Folder name is the chapter ID/number
                        pages = []
                        for p in sorted(ch_dir.glob('*.typ')):
                            pages.append({'id': p.stem, 'title': 'Untitled Section'})
                        if pages:
                            config = load_config_safe()
                            chap_name = config.get('chapter-name', 'Chapter')
                            chapters[int(ch_id)] = {'id': ch_id, 'title': f'{chap_name} {ch_id}', 'summary': '', 'pages': pages}
                            has_content = True
                    except:
                        pass
                if has_content:
                    hierarchy = [chapters[k] for k in sorted(chapters.keys())]
            if not has_content:
                config = load_config_safe()
                chap_name = config.get('chapter-name', 'Chapter')
                sect_name = config.get('subchap-name', 'Section')
                hierarchy = [{'id': '0', 'title': f'First {chap_name}', 'summary': 'Getting started', 'pages': [{'id': '0', 'title': f'First {sect_name}'}]}]
            HIERARCHY_FILE.parent.mkdir(parents=True, exist_ok=True)
            HIERARCHY_FILE.write_text(json.dumps(hierarchy, indent=4))
            h, w = self.scr.getmaxyx()
            self.scr.clear()
            msg = 'Hierarchy auto-generated from content' if has_content else 'Created default hierarchy structure'
            TUI.safe_addstr(self.scr, h // 2, (w - len(msg)) // 2, msg, curses.color_pair(1) | curses.A_BOLD)
            self.scr.refresh()
            curses.napms(1000)
            return 'edit'
        except:
            return None