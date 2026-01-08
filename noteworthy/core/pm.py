import json
import urllib.request
import urllib.error
import base64
from pathlib import Path
from ..utils import load_json_safe
from ..config import MODULES_CONFIG_FILE

MODULES_DIR = Path("templates/module")
REPO_OWNER = "sihooleebd"
REPO_NAME = "noteworthy-modules"
API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents"

def fetch_remote_modules():
    """Fetch list of available module directories from remote (excludes 'core')."""
    try:
        req = urllib.request.Request(API_BASE)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=5) as response:
            contents = json.loads(response.read().decode())
        
        modules = []
        for item in contents:
            if item['type'] == 'dir' and not item['name'].startswith('.') and item['name'] != 'core':
                modules.append(item['name'])
        return sorted(modules)
    except Exception:
        return []

def fetch_core_submodules():
    """Fetch list of submodules inside 'core' folder."""
    try:
        req = urllib.request.Request(f"{API_BASE}/core")
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=5) as response:
            contents = json.loads(response.read().decode())
        
        submodules = []
        for item in contents:
            if item['type'] == 'dir' and not item['name'].startswith('.'):
                submodules.append(item['name'])
        return sorted(submodules)
    except Exception:
        return []

def get_installed_modules():
    if not MODULES_CONFIG_FILE.exists():
        return {}
    return load_json_safe(MODULES_CONFIG_FILE).get("modules", {})

def save_modules_config(modules):
    config = load_json_safe(MODULES_CONFIG_FILE) if MODULES_CONFIG_FILE.exists() else {}
    config["modules"] = modules
    MODULES_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MODULES_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def check_dependencies(module_name, index, enabled_modules):
    if module_name not in index:
        return []
    mod_meta = index[module_name]
    deps = mod_meta.get("dependencies", [])
    return [d for d in deps if d not in enabled_modules]

def create_custom_module(name):
    mod_dir = MODULES_DIR / name
    if mod_dir.exists():
        return False
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "mod.typ").write_text(f"// Custom module: {name}\n#let hello() = [Hello from {name}!]\n")
    meta = {"name": name, "version": "0.1.0", "dependencies": [], "exports": ["hello"]}
    (mod_dir / "metadata.json").write_text(json.dumps(meta, indent=4))
    return True

def _download_file(url):
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read()
    except:
        return None

def _recurse_download(api_url, local_base, callback, msg_prefix):
    """Recursively download directory contents from GitHub API."""
    try:
        req = urllib.request.Request(api_url)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=10) as r:
            items = json.loads(r.read().decode())
        
        for item in items:
            name = item['name']
            if name.startswith('.'):
                continue
            
            if item['type'] == 'file':
                if callback:
                    callback(f"{msg_prefix}: {name}")
                content = _download_file(item['download_url'])
                if content is not None:
                    dest = local_base / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(content)
            elif item['type'] == 'dir':
                _recurse_download(item['url'], local_base / name, callback, msg_prefix)
    except Exception as e:
        if callback:
            callback(f"Error: {e}")

def download_modules(modules_to_download, callback=None):
    """Download a list of module names from remote."""
    total = len(modules_to_download)
    for i, name in enumerate(modules_to_download, 1):
        if callback:
            callback(f"Downloading {name} ({i}/{total})...")
        
        target_dir = MODULES_DIR / name
        target_dir.mkdir(parents=True, exist_ok=True)
        api_url = f"{API_BASE}/{name}"
        
        try:
            _recurse_download(api_url, target_dir, callback, f"Downloading {name}")
        except Exception as e:
            if callback:
                callback(f"Failed {name}: {e}")
    
    if callback:
        callback("Download Complete.")

def get_changed_files(old_sha, new_sha):
    """Get list of changed file paths between two commits."""
    if not old_sha or not new_sha:
        return None  # Force full download
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/compare/{old_sha}...{new_sha}"
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        
        changed = set()
        for f in data.get('files', []):
            path = f['filename']
            parts = path.split('/')
            if len(parts) >= 1:
                changed.add(parts[0])  # Top-level module name
        return changed
    except:
        return None

def download_changed_modules(modules, changed_set, callback=None):
    """Download only modules that have changed."""
    to_download = [m for m in modules if m in changed_set]
    if to_download:
        download_modules(to_download, callback)
    return to_download

    # Update SHAs for downloaded modules
    # We need to fetch the tree again or cache it to get the new SHAs? 
    # Or we can just get the latest HEAD sha of the repo? 
    # Ideally we want the sha of the specific folder we just got.
    # Let's fetch the tree one more time or pass it in. Check module_updates already fetches it.
    # For simplicity, we'll fetch latest repo tree and update specific modules.
    try:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/HEAD?recursive=1"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
        
        tree = {i['path']: i['sha'] for i in data.get('tree', [])}
        config = load_json_safe(MODULES_CONFIG_FILE)
        
        for name in modules_to_download:
            if name in tree and "modules" in config and name in config["modules"]:
                config["modules"][name]["sha"] = tree[name]
        
        save_modules_config(config["modules"])
    except:
        pass

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
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits?per_page=5"
    else:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/compare/{since_sha}...{until_sha}"
    
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            
            commits = []
            if 'commits' in data:
                for c in data['commits']:
                    msg = c['commit']['message'].split('\n')[0]
                    commits.append(f"- {msg}")
            elif isinstance(data, list):
                for c in data:
                    msg = c['commit']['message'].split('\n')[0]
                    commits.append(f"- {msg}")
            return list(filter(None, commits))
    except:
        return ["Error fetching commit log"]

def get_modules_meta():
    if not MODULES_CONFIG_FILE.exists():
        return {}
    return load_json_safe(MODULES_CONFIG_FILE).get("meta", {})

def save_modules_meta(meta):
    config = load_json_safe(MODULES_CONFIG_FILE) if MODULES_CONFIG_FILE.exists() else {}
    config["meta"] = meta
    MODULES_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MODULES_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def check_module_updates(installed_modules):
    """
    Check relevant modules for updates by comparing local versions/content with remote.
    Returns a set of module names that have updates.
    """
    # For efficiency, we can fetch the tree of the repo and compare SHAs of module folders/files
    # api.github.com/repos/.../git/trees/HEAD?recursive=1 
    # That gives us sha for every path.
    # But installed_modules doesn't store the installed sha currently, only global meta["commit"].
    # Ideally we should store sha per module in modules.json
    
    # Strategy:
    # 1. Fetch remote tree
    # 2. For each installed remote module, check if remote folder sha != stored sha (if we store it)
    #    OR if not stored, we assume up to date unless we can check version in metadata.json?
    #    Checking version requires downloading metadata.json for each module => slow.
    
    # We will assume "version" field in metadata.json is the source of truth if available,
    # OR we start storing 'sha' in installed_modules.
    
    # Let's try to fetch the remote metadata for all installed remote modules.
    # This might be N requests so we should be careful.
    # Alternatively, fetch repo tree (1 request) and ignore version, just look for change.
    
    # If we don't have local SHAs, we can't do SHA comparison. 
    # Our current module state is just {"source": "remote", "status": "..."}.
    # We should start storing the installed SHA.
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/HEAD?recursive=1"
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
    except:
        return set() # Fail safe
        
    remote_shas = {} # path -> sha
    for item in data.get('tree', []):
        remote_shas[item['path']] = item['sha']
        
    outdated = set()
    current_config = load_json_safe(MODULES_CONFIG_FILE)
    modules_config = current_config.get("modules", {})
    
    # We update the config with SHAs if they are missing (first run after update) 
    # But if they are missing, we can't know if they are outdated without checking content.
    # Use global commit as proxy for "all updated" if we lack granular info?
    # Or just assume fresh install = latest.
    
    # Let's verify against what we have on disk?
    # For now, let's implement the logic to return outdated based on 'sha' field in module config.
    # If 'sha' is missing, we claim update available to force sync once? Or assume updated.
    
    idx_changes = False
    
    for name, state in modules_config.items():
        if state.get("source") != "remote":
            continue
            
        # The path in repo for module 'name' is just 'name' (folder)
        # But 'tree' api returns sha for the folder.
        remote_sha = remote_shas.get(name)
        if not remote_sha: continue # Module might have been renamed or moved
        
        local_sha = state.get("sha")
        
        if local_sha != remote_sha:
            outdated.add(name)
            # We don't update local sha here, only on successful download
            
    return outdated

def update_module_sha(module_name, sha):
    config = load_json_safe(MODULES_CONFIG_FILE)
    if "modules" in config and module_name in config["modules"]:
        config["modules"][module_name]["sha"] = sha
        save_modules_config(config["modules"]) 

