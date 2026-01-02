import json
import urllib.request
import urllib.error
from pathlib import Path
from ..utils import load_json_safe
from ..config import MODULES_CONFIG_FILE

MODULES_DIR = Path("templates/module")
REPO_OWNER = "sihooleebd"
REPO_NAME = "noteworthy-modules"
API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents"

def fetch_index():
    """Fetch list of available modules from remote using GitHub API."""
    try:
        # 1. Fetch root contents
        req = urllib.request.Request(API_BASE)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=5) as response:
            contents = json.loads(response.read().decode())
            
        index = {}
        for item in contents:
            if item['type'] == 'dir' and not item['name'].startswith('.'):
                idx_entry = {
                    "name": item['name'],
                    "dependencies": [], # Can't know deps without fetching metadata
                    "exports": []
                }
                # Try to pre-fetch metadata? Too slow for index. 
                # We'll rely on lazy fetching or just assume no deps for listing.
                index[item['name']] = idx_entry
        return index
    except Exception as e:
        return {} # Offline or rate limited

def get_installed_modules():
    if not MODULES_CONFIG_FILE.exists():
        return {}
    return load_json_safe(MODULES_CONFIG_FILE).get("modules", {})

def save_modules_config(modules):
    MODULES_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MODULES_CONFIG_FILE, "w") as f:
        json.dump({"modules": modules}, f, indent=4)

def check_dependencies(module_name, index, enabled_modules):
    if module_name not in index:
        return []
    mod_meta = index[module_name]
    deps = mod_meta.get("dependencies", [])
    missing = []
    for d in deps:
        if d not in enabled_modules:
            missing.append(d)
    return missing

def create_custom_module(name):
    mod_dir = MODULES_DIR / name
    if mod_dir.exists():
        return False
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "mod.typ").write_text(f"// Custom module: {name}\n#let hello() = [Hello from {name}!]\n")
    meta = {
        "name": name,
        "version": "0.1.0",
        "dependencies": [],
        "exports": ["hello"]
    }
    (mod_dir / "metadata.json").write_text(json.dumps(meta, indent=4))
    return True

def _download_file(url, params):
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=10) as r:
            content = r.read()
            return content
    except:
        return None

def _recurse_download(api_url, local_base, callback, current_msg):
    """Recursively download directory contents from GitHub API."""
    try:
        req = urllib.request.Request(api_url)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=10) as r:
            items = json.loads(r.read().decode())
            
        for item in items:
            name = item['name']
            if name.startswith('.'): continue
            
            if item['type'] == 'file':
                if callback: callback(f"{current_msg}: {name}")
                
                content = _download_file(item['download_url'], None)
                if content is not None:
                    dest = local_base / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(content)
                    
            elif item['type'] == 'dir':
                _recurse_download(item['url'], local_base / name, callback, current_msg)
                
    except Exception as e:
        if callback: callback(f"Error: {e}")

def download_modules(modules_to_download, callback=None):
    """
    Download a list of module names from remote.
    modules_to_download: list of strings (module names)
    callback: function(current_status_string)
    """
    total = len(modules_to_download)
    for i, name in enumerate(modules_to_download, 1):
        if callback: callback(f"Downloading {name} ({i}/{total})...")
        
        # Target dir
        target_dir = MODULES_DIR / name
        # We don't wipe it, we overwrite/merge
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Use API to list contents of the module folder
        api_url = f"{API_BASE}/{name}" 
        
        try:
             _recurse_download(api_url, target_dir, callback, f"Downloading {name}")
        except Exception as e:
             if callback: callback(f"Failed {name}: {e}")

    if callback: callback("Download Complete.")

def get_latest_commit_sha():
    """Fetch the latest commit SHA from the GitHub repository."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/HEAD"
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            return data['sha']
    except:
        return None

def get_commit_log(since_sha, until_sha):
    """Fetch commit messages between two SHAs."""
    if not since_sha:
        # If no history, just show latest or a few?
        # api.github.com/repos/.../commits?per_page=5
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits?per_page=5"
    else:
        # compare view: api.github.com/repos/.../compare/base...head
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/compare/{since_sha}...{until_sha}"
        
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            
            commits = []
            if 'commits' in data: # Compare view
                for c in data['commits']:
                    msg = c['commit']['message'].split('\n')[0]
                    commits.append(f"- {msg}")
            elif isinstance(data, list): # List view (initial)
                for c in data:
                    msg = c['commit']['message'].split('\n')[0]
                    commits.append(f"- {msg}")
            return filter(None, commits) # list
    except:
        return ["Error fetching commit log"]

def get_modules_meta():
    if not MODULES_CONFIG_FILE.exists():
        return {}
    return load_json_safe(MODULES_CONFIG_FILE).get("meta", {})

def save_modules_meta(meta):
    config = load_json_safe(MODULES_CONFIG_FILE)
    config["meta"] = meta
    MODULES_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MODULES_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
