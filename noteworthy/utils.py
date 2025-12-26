import json
import shutil
import sys
import subprocess
from pathlib import Path
from .config import METADATA_FILE, CONSTANTS_FILE, SETTINGS_FILE, SYSTEM_CONFIG_DIR, INDEXIGNORE_FILE, HIERARCHY_FILE, BASE_DIR

def load_config_safe():
    """Load merged config from both metadata and constants files"""
    config = {}
    try:
        if METADATA_FILE.exists():
            config.update(json.loads(METADATA_FILE.read_text()))
        if CONSTANTS_FILE.exists():
            config.update(json.loads(CONSTANTS_FILE.read_text()))
    except:
        pass
    return config

def save_config(config):
    """Save config to split files (metadata and constants)"""
    metadata_keys = {'title', 'subtitle', 'authors', 'affiliation', 'logo'}
    try:
        metadata = {k: v for k, v in config.items() if k in metadata_keys}
        constants = {k: v for k, v in config.items() if k not in metadata_keys}
        METADATA_FILE.write_text(json.dumps(metadata, indent=4))
        CONSTANTS_FILE.write_text(json.dumps(constants, indent=4))
        return True
    except:
        return False

def load_settings():
    try:
        SYSTEM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if SETTINGS_FILE.exists():
            return json.loads(SETTINGS_FILE.read_text())
    except:
        pass
    return {}

def save_settings(settings):
    try:
        SYSTEM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    except:
        pass

def load_indexignore():
    try:
        if INDEXIGNORE_FILE.exists():
            lines = INDEXIGNORE_FILE.read_text().strip().split('\n')
            return {l.strip() for l in lines if l.strip() and (not l.startswith('#'))}
    except:
        pass
    return set()

def register_key(keymap, bind):
    if isinstance(bind.keys, list):
        for k in bind.keys:
            keymap[k] = bind
    else:
        keymap[bind.keys] = bind

def handle_key_event(key_code, keymap, context=None):
    if key_code in keymap:
        bind = keymap[key_code]
        res = bind(context)
        return True, res
    return False, None

def save_indexignore(ignored_set):
    try:
        SYSTEM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        content = '# Files to ignore during hierarchy sync\n# One file ID per line (e.g., 01.03)\n\n'
        content += '\n'.join(sorted(ignored_set))
        INDEXIGNORE_FILE.write_text(content)
    except:
        pass

def check_dependencies():
    if not shutil.which('typst'):
        print("Error: 'typst' not found. Install from https://typst.app")
        sys.exit(1)
    if not shutil.which('pdfinfo'):
        print("Error: 'pdfinfo' not found. Install with: brew install poppler")
        sys.exit(1)
    if not (shutil.which('pdfunite') or shutil.which('gs')):
        print("Error: Neither 'pdfunite' nor 'gs' (ghostscript) found. Install poppler-utils or ghostscript.")
        sys.exit(1)

def get_formatted_name(path_str, hierarchy, config=None):
    if config is None:
        config = load_config_safe()
    path = Path(path_str)
    if not path.stem.isdigit() or not path.parent.name.isdigit():
        return path.name
    ci = int(path.parent.name)
    pi = int(path.stem)
    total_chapters = len(hierarchy)
    total_pages = 0
    if ci < len(hierarchy):
        total_pages = len(hierarchy[ci].get('pages', []))
    ch_width = len(str(total_chapters))
    pg_width = len(str(total_pages)) if total_pages > 0 else 2

    def get_num(idx, item):
        return str(item.get('number', idx + 1))
    ch_item = hierarchy[ci] if ci < len(hierarchy) else {}
    ch_num_str = get_num(ci, ch_item)
    pg_item = {}
    if ci < len(hierarchy) and pi < len(hierarchy[ci].get('pages', [])):
        pg_item = hierarchy[ci]['pages'][pi]
    pg_num_str = get_num(pi, pg_item)
    ch_disp = ch_num_str.zfill(ch_width) if ch_num_str.isdigit() else ch_num_str
    pg_disp = pg_num_str.zfill(pg_width) if pg_num_str.isdigit() else pg_num_str
    label = config.get('subchap-name', 'Section')
    return f'{label} {ch_disp}.{pg_disp}'

def extract_hierarchy():
    temp_file = Path('extract_hierarchy.typ')
    temp_file.write_text('#import "templates/setup.typ": hierarchy\n#metadata(hierarchy) <hierarchy>')
    try:
        result = subprocess.run(['typst', 'query', str(temp_file), '<hierarchy>'], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)[0]['value']
    except subprocess.CalledProcessError as e:
        print(f'Error extracting hierarchy: {e.stderr}')
        sys.exit(1)
    finally:
        temp_file.unlink(missing_ok=True)