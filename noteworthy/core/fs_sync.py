import shutil
from pathlib import Path

DEFAULT_CONTENT_TEMPLATE = '#import "../../templates/templater.typ": *\n\nWrite your content here.'

def ensure_content_structure(hierarchy, base_dir=Path('content')):
    created = []
    base_dir.mkdir(parents=True, exist_ok=True)
    
    for ci, ch in enumerate(hierarchy):
        ch_dir = base_dir / str(ci)
        ch_dir.mkdir(exist_ok=True)
        
        for pi, pg in enumerate(ch.get('pages', [])):
            pg_file = ch_dir / f'{pi}.typ'
            if not pg_file.exists():
                pg_file.write_text(DEFAULT_CONTENT_TEMPLATE)
                created.append(str(pg_file))
                
    return created

def cleanup_extra_files(hierarchy, base_dir=Path('content')):
    if not base_dir.exists():
        return []
        
    deleted = []
    
    valid_paths = set()
    for ci, ch in enumerate(hierarchy):
        ch_dir = base_dir / str(ci)
        valid_paths.add(ch_dir)
        for pi, _ in enumerate(ch.get('pages', [])):
            valid_paths.add(ch_dir / f'{pi}.typ')
            
    for ch_dir in base_dir.iterdir():
        if ch_dir.is_dir() and ch_dir.name.isdigit():
            for f in ch_dir.glob('*.typ'):
                if f.stem.isdigit():
                    if f not in valid_paths:
                        f.unlink()
                        deleted.append(str(f))
            
            if ch_dir not in valid_paths:
                if not any(ch_dir.iterdir()):
                    ch_dir.rmdir()
                    deleted.append(str(ch_dir))
            else:
                pass
                
    return deleted
