import curses
import json
from pathlib import Path
from ..base import TUI
from ...config import HIERARCHY_FILE, CONFIG_FILE

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
                        ch_num = int(ch_dir.name)
                        pages = []
                        for p in sorted(ch_dir.glob('*.typ')):
                            pages.append({'id': p.stem, 'title': 'Untitled Section'})
                        if pages:
                            try:
                                config = json.loads(CONFIG_FILE.read_text())
                                chap_name = config.get('chapter-name', 'Chapter')
                            except:
                                chap_name = 'Chapter'
                            chapters[ch_num] = {'title': f'{chap_name} {ch_num}', 'summary': '', 'pages': pages}
                            has_content = True
                    except:
                        pass
                if has_content:
                    hierarchy = [chapters[k] for k in sorted(chapters.keys())]
            if not has_content:
                try:
                    config = json.loads(CONFIG_FILE.read_text())
                    chap_name = config.get('chapter-name', 'Chapter')
                    sect_name = config.get('subchap-name', 'Section')
                except:
                    chap_name = 'Chapter'
                    sect_name = 'Section'
                hierarchy = [{'title': f'First {chap_name}', 'summary': 'Getting started', 'pages': [{'id': '01.01', 'title': f'First {sect_name}'}]}]
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