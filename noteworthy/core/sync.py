import json
from pathlib import Path
from ..config import HIERARCHY_FILE

def sync_hierarchy_with_content():
    hierarchy = json.loads(HIERARCHY_FILE.read_text())
    missing_files = []
    new_files = []
    for i, ch in enumerate(hierarchy):
        for j, pg in enumerate(ch.get('pages', [])):
            path = Path(f'content/{i}/{j}.typ')
            if not path.exists():
                missing_files.append(str(path))
    content_dir = Path('content')
    if content_dir.exists():
        for ch_dir in content_dir.iterdir():
            if ch_dir.is_dir() and ch_dir.name.isdigit():
                i = int(ch_dir.name)
                if i >= len(hierarchy):
                    for f in ch_dir.glob('*.typ'):
                        new_files.append(str(f))
                else:
                    for f in ch_dir.glob('*.typ'):
                        if f.stem.isdigit():
                            j = int(f.stem)
                            pages = hierarchy[i].get('pages', [])
                            if j >= len(pages):
                                new_files.append(str(f))
    return (sorted(missing_files), sorted(new_files))