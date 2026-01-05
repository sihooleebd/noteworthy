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

# Re-export from core.deps for backwards compatibility
from .core.deps import check_dependencies

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

def load_json_safe(file_path):
    """Safely load JSON file, returning empty dict on failure."""
    try:
        if file_path.exists():
            return json.loads(file_path.read_text())
    except:
        pass
    return {}


def scan_content(content_dir=None):
    """
    Scan content/ folder to get sorted folder/file names.
    
    Returns:
        Tuple of (ch_folders, pg_folders) where:
        - ch_folders: List of chapter folder names (sorted numerically)
        - pg_folders: Dict mapping chapter index to list of page file stems
    """
    if content_dir is None:
        content_dir = Path('content')
    elif isinstance(content_dir, str):
        content_dir = Path(content_dir)
        
    ch_folders = []
    pg_folders = {}
    
    if content_dir.exists():
        ch_dirs = sorted(
            [d for d in content_dir.iterdir() if d.is_dir() and d.name.isdigit()],
            key=lambda d: int(d.name)
        )
        idx = 0
        for ch_dir in ch_dirs:
            pg_files = sorted(
                [f.stem for f in ch_dir.glob('*.typ') if f.stem.isdigit()],
                key=lambda s: int(s)
            )
            if pg_files:
                ch_folders.append(ch_dir.name)
                pg_folders[str(idx)] = pg_files
                idx += 1
                
    return ch_folders, pg_folders

def generate_updater(branch='master', force=False, relaunch_script='noteworthy.py'):
    script = f"""#!/usr/bin/env python3
import sys
import os
import json
import urllib.request
import urllib.parse
import shutil
from pathlib import Path

BRANCH = '{branch}'
FORCE = {force}
RELAUNCH_SCRIPT = '{relaunch_script}'

def bootstrap(branch='master'):
    repo_api = f'https://api.github.com/repos/sihooleebd/noteworthy/git/trees/{{branch}}?recursive=1'
    raw_base = f'https://raw.githubusercontent.com/sihooleebd/noteworthy/{{branch}}/'

    print(f'Fetching file list from {{branch}}...')
    try:
        req = urllib.request.Request(repo_api, headers={{'User-Agent': 'Noteworthy-Loader'}})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f'Error fetching file list: {{e}}')
        return False

    USER_CONFIG_FILES = {{
        'config/metadata.json',
        'config/constants.json',
        'config/hierarchy.json',
        'config/snippets.typ',
        'config/preface.typ',
    }}

    files = []
    for item in data.get('tree', []):
        if item.get('type') != 'blob':
            continue
        p = item['path']
        
        if p.startswith('noteworthy/') or p.startswith('templates/'):
            files.append(p)
            continue
            
        if p.startswith('config/'):
            if p not in USER_CONFIG_FILES:
                files.append(p)
            continue
            
        if p in ('noteworthy.py', 'noteworthy_cli.py'):
            files.append(p)

    print(f'Downloading {{len(files)}} files...')
    success_count = 0
    for p in files:
        target = Path(p)
        url = raw_base + urllib.parse.quote(p)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url) as r, open(target, 'wb') as f:
                f.write(r.read())
            print(f'Downloaded {{p}}')
            success_count += 1
        except Exception as e:
            print(f'Failed {{p}}: {{e}}')
            
    return success_count > 0

def main():
    print(f"External Updater Running (Branch: {{BRANCH}}, Force: {{FORCE}})")
    
    backups = []
    if FORCE:
        print("Force updating: Removing existing directories...")
        files_to_save = ['config/metadata.json', 'config/constants.json', 'config/hierarchy.json', 'config/preface.typ']
        for fpath in files_to_save:
            src = Path(fpath)
            if src.exists():
                dst = Path(f'{{src.name}}.bak')
                try:
                    shutil.copy2(src, dst)
                    backups.append((dst, src))
                    print(f"Backed up {{src.name}}")
                except Exception as e:
                    print(f"Warning: Failed to backup {{src.name}}: {{e}}")

        if Path('noteworthy').exists():
            shutil.rmtree('noteworthy')
        if Path('templates').exists():
            shutil.rmtree('templates')
            
    success = bootstrap(BRANCH)
    
    if FORCE and backups:
        print("Restoring configuration files...")
        for dst, src in backups:
            try:
                if dst.exists():
                    src.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dst), str(src))
                    print(f"Restored {{src.name}}")
            except Exception as e:
                print(f"Error restoring {{src.name}}: {{e}}")
    
    if success:
        print(f"Update complete. Launching {{RELAUNCH_SCRIPT}}...")
        if os.path.exists('_update_runner.py'):
            try:
                os.remove('_update_runner.py')
            except:
                pass
        
        # Re-launch script
        os.execv(sys.executable, [sys.executable, RELAUNCH_SCRIPT])
    else:
        print("Update failed.")
        sys.exit(1)

if __name__ == '__main__':
    main()
"""
    return script