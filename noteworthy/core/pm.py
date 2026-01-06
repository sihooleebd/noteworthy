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
        req = urllib.request.Request(API_BASE)
        req.add_header('User-Agent', 'Noteworthy-PM')
        with urllib.request.urlopen(req, timeout=5) as response:
            contents = json.loads(response.read().decode())
            
        index = {}
        for item in contents:
            if item['type'] == 'dir' and not item['name'].startswith('.'):
                name = item['name']
                idx_entry = {
                    "name": name,
                    "description": "",
                    "dependencies": [],
                    "exports": [],
                    "source": "remote"
                }
                
                # Try to fetch metadata.json for this module
                try:
                    meta_url = f"{API_BASE}/{name}/metadata.json"
                    meta_req = urllib.request.Request(meta_url)
                    meta_req.add_header('User-Agent', 'Noteworthy-PM')
                    with urllib.request.urlopen(meta_req, timeout=3) as meta_resp:
                        meta_data = json.loads(meta_resp.read().decode())
                        # GitHub API returns base64 encoded content
                        if 'content' in meta_data:
                            import base64
                            content = base64.b64decode(meta_data['content']).decode('utf-8')
                            meta = json.loads(content)
                            idx_entry["description"] = meta.get("description", "")
                            idx_entry["dependencies"] = meta.get("dependencies", [])
                            idx_entry["exports"] = meta.get("exports", [])
                except:
                    pass  # No metadata, use defaults
                
                index[name] = idx_entry
        return index
    except Exception as e:
        return {}  # Offline or rate limited

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

