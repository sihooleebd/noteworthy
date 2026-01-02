from pathlib import Path

DEFAULT_CONTENT_TEMPLATE = '#import "../../templates/templater.typ": *\n\nWrite your content here.'

def ensure_content_structure(hierarchy, base_dir=Path('content')):
    """Create content folders and files for hierarchy entries that don't exist on disk."""
    created = []
    base_dir.mkdir(parents=True, exist_ok=True)
    
    for ci, ch in enumerate(hierarchy):
        ch_id = str(ch.get('id', ci))
        ch_dir = base_dir / ch_id
        ch_dir.mkdir(exist_ok=True)
        
        for pi, pg in enumerate(ch.get('pages', [])):
            pg_id = str(pg.get('id', pi))
            pg_file = ch_dir / f'{pg_id}.typ'
            if not pg_file.exists():
                pg_file.write_text(DEFAULT_CONTENT_TEMPLATE)
                created.append(str(pg_file))
                
    return created
