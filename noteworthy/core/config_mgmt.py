import shutil
from pathlib import Path
from datetime import datetime
from ..config import BASE_DIR
EXPORT_DIR = BASE_DIR / 'exports'

def export_file(file_path, suffix=None):
    p = Path(file_path)
    if not p.exists():
        return None
    EXPORT_DIR.mkdir(exist_ok=True, parents=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    name = f'{p.stem}_{ts}'
    if suffix:
        name += f'_{suffix}'
    name += p.suffix
    out = EXPORT_DIR / name
    try:
        shutil.copy(p, out)
        return str(out)
    except:
        return None

def import_file(export_path, target_path):
    src = Path(export_path)
    dst = Path(target_path)
    if not src.exists():
        return False
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        return True
    except:
        return False

def list_exports_for(filename):
    if not EXPORT_DIR.exists():
        return []
    stem = Path(filename).stem
    ext = Path(filename).suffix
    res = []
    for f in EXPORT_DIR.glob(f'{stem}_*{ext}'):
        res.append(f.name)
    return sorted(res, reverse=True)