import json
from pathlib import Path
from ..config import HIERARCHY_FILE

def sync_hierarchy_with_content():
    """Compare hierarchy.json with actual content/ folder structure using id fields."""
    hierarchy = json.loads(HIERARCHY_FILE.read_text())
    missing_files = []
    new_files = []
    
    # Build a map of expected files from hierarchy using id fields
    expected_files = set()
    for i, ch in enumerate(hierarchy):
        ch_id = str(ch.get('id', i))  # Use id field (folder name)
        for j, pg in enumerate(ch.get('pages', [])):
            pg_id = str(pg.get('id', j))  # Use id field (filename)
            path = Path(f'content/{ch_id}/{pg_id}.typ')
            expected_files.add(str(path))
            if not path.exists():
                missing_files.append(str(path))
    
    # Build a set of hierarchy (chapter_id, page_id) pairs for quick lookup
    hierarchy_ids = set()
    for ch in hierarchy:
        ch_id = str(ch.get('id', ''))
        for pg in ch.get('pages', []):
            pg_id = str(pg.get('id', ''))
            hierarchy_ids.add((ch_id, pg_id))
    
    # Find new files in content/ that aren't in hierarchy
    content_dir = Path('content')
    if content_dir.exists():
        for ch_dir in sorted(content_dir.iterdir()):
            if ch_dir.is_dir() and ch_dir.name.isdigit():
                ch_folder_id = ch_dir.name
                # Check if this chapter folder exists in hierarchy
                ch_in_hierarchy = any(str(ch.get('id', '')) == ch_folder_id for ch in hierarchy)
                
                for f in sorted(ch_dir.glob('*.typ')):
                    file_id = f.stem
                    if (ch_folder_id, file_id) not in hierarchy_ids:
                        new_files.append(str(f))
    
    return (sorted(missing_files), sorted(new_files))