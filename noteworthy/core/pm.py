import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from ..utils import load_json_safe
from ..config import MODULES_CONFIG_FILE

MODULES_DIR = Path("templates/module")
REPO_OWNER = "sihooleebd"
REPO_NAME = "noteworthy-modules"
REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}.git"
CACHE_DIR = Path.home() / ".cache/noteworthy/modules-repo"


# ============================================================================
# Git-based Module Cache
# ============================================================================

def ensure_module_cache(callback=None):
    """Clone or update the modules repo cache. Returns cache path or None on failure."""
    try:
        if not CACHE_DIR.exists():
            if callback:
                callback("Cloning module repository...")
            CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "clone", "--depth", "1", REPO_URL, str(CACHE_DIR)],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                return None
        else:
            if callback:
                callback("Fetching updates...")
            # Fetch latest changes
            subprocess.run(
                ["git", "-C", str(CACHE_DIR), "fetch", "--depth", "1", "origin", "main"],
                capture_output=True, text=True, timeout=30
            )
            subprocess.run(
                ["git", "-C", str(CACHE_DIR), "reset", "--hard", "origin/main"],
                capture_output=True, text=True, timeout=10
            )
        return CACHE_DIR
    except Exception:
        return None


def get_cache_commit_sha():
    """Get current commit SHA from the cache."""
    try:
        result = subprocess.run(
            ["git", "-C", str(CACHE_DIR), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_module_sha_from_cache(module_name, is_core=False):
    """Get the tree SHA for a specific module folder from git."""
    try:
        if is_core:
            path = f"core/{module_name}"
        else:
            path = module_name
        
        result = subprocess.run(
            ["git", "-C", str(CACHE_DIR), "rev-parse", f"HEAD:{path}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def check_module_updates(config):
    """
    Check which modules have updates available.
    Compares stored SHA with current cache SHA.
    Returns set of module names that have updates.
    """
    outdated = set()
    
    # Check default modules - only those with a sha (installed)
    for name, state in config.get("modules", {}).items():
        stored_sha = state.get("sha")
        if not stored_sha:
            continue  # Not installed
        current_sha = get_module_sha_from_cache(name, is_core=False)
        if current_sha and stored_sha != current_sha:
            outdated.add(name)
    
    # Check core modules
    for name, state in config.get("core_modules", {}).items():
        stored_sha = state.get("sha")
        current_sha = get_module_sha_from_cache(name, is_core=True)
        if current_sha and stored_sha != current_sha:
            outdated.add(f"core/{name}")
    
    return outdated


# ============================================================================
# Module Discovery
# ============================================================================

def parse_metadata(meta_path):
    """Parse a metadata.json file, return dict or None if invalid."""
    try:
        if meta_path.exists():
            with open(meta_path, 'r') as f:
                data = json.load(f)
            # Validate required fields
            if isinstance(data, dict) and "name" in data:
                return data
    except Exception:
        pass
    return None


def discover_modules_from_cache():
    """
    Discover all modules from cached repo.
    Returns: (core_modules, default_modules) dicts with metadata.
    """
    core_modules = {}
    default_modules = {}
    
    if not CACHE_DIR.exists():
        return core_modules, default_modules
    
    # Core modules (under core/ directory)
    core_dir = CACHE_DIR / "core"
    if core_dir.exists():
        for d in core_dir.iterdir():
            if d.is_dir() and not d.name.startswith('.'):
                meta = parse_metadata(d / "metadata.json")
                if meta:
                    core_modules[d.name] = meta
                else:
                    core_modules[d.name] = {"name": d.name, "dependencies": [], "exports": []}
    
    # Default modules (top-level, excluding core, .git, etc.)
    skip_dirs = {'core', '.git'}
    for d in CACHE_DIR.iterdir():
        if d.is_dir() and d.name not in skip_dirs and not d.name.startswith('.'):
            meta = parse_metadata(d / "metadata.json")
            if meta:
                default_modules[d.name] = meta
            else:
                default_modules[d.name] = {"name": d.name, "dependencies": [], "exports": []}
    
    return core_modules, default_modules


def discover_local_modules(remote_module_names):
    """
    Discover locally created modules (not in remote repo).
    Returns dict of local module name -> metadata.
    """
    local_modules = {}
    
    if not MODULES_DIR.exists():
        return local_modules
    
    skip_dirs = set(remote_module_names) | {'core', '.git'}
    
    for d in MODULES_DIR.iterdir():
        if d.is_dir() and d.name not in skip_dirs and not d.name.startswith('.'):
            meta = parse_metadata(d / "metadata.json")
            if meta:
                local_modules[d.name] = meta
    
    return local_modules


# ============================================================================
# Dependency Resolution
# ============================================================================

def get_module_dependencies(module_name, is_core=False):
    """
    Get dependencies for a module from its metadata.json.
    First checks the cache, then falls back to local installation.
    """
    # Try cache first
    if is_core:
        meta_path = CACHE_DIR / "core" / module_name / "metadata.json"
    else:
        meta_path = CACHE_DIR / module_name / "metadata.json"
    
    meta = parse_metadata(meta_path)
    if meta:
        return meta.get("dependencies", [])
    
    # Fallback to local installation
    if is_core:
        meta_path = MODULES_DIR / "core" / module_name / "metadata.json"
    else:
        meta_path = MODULES_DIR / module_name / "metadata.json"
    
    meta = parse_metadata(meta_path)
    if meta:
        return meta.get("dependencies", [])
    
    return []


def resolve_all_dependencies(module_names, include_requested=True):
    """
    Resolve all dependencies for a list of modules using DFS with cycle detection.
    Returns topologically sorted list (dependencies first, then dependents).
    
    Args:
        module_names: List of module names to resolve
        include_requested: If True, include the requested modules in the result
    
    Returns:
        Tuple of (ordered_modules, cycles_detected)
        - ordered_modules: List of module names in install order (deps first)
        - cycles_detected: List of detected cycles as tuples
    
    Raises:
        Nothing - cycles are returned, not raised
    """
    # Track visited nodes and current recursion stack for cycle detection
    visited = set()
    in_stack = set()
    result = []
    cycles = []
    
    def dfs(module, path):
        """DFS with cycle detection. Returns True if cycle detected."""
        if module in in_stack:
            # Cycle detected - find the cycle in the path
            cycle_start = path.index(module)
            cycle = tuple(path[cycle_start:] + [module])
            cycles.append(cycle)
            return True
        
        if module in visited:
            return False
        
        visited.add(module)
        in_stack.add(module)
        path.append(module)
        
        # Get dependencies for this module
        deps = get_module_dependencies(module, is_core=False)
        
        for dep in deps:
            dfs(dep, path)
        
        path.pop()
        in_stack.remove(module)
        result.append(module)
        return False
    
    # Run DFS from each requested module
    for module in module_names:
        if module not in visited:
            dfs(module, [])
    
    # Result is in reverse topological order, so reverse it
    # Dependencies will be at the front, dependents at the back
    ordered = list(reversed(result))
    
    if not include_requested:
        # Filter out the originally requested modules
        ordered = [m for m in ordered if m not in module_names]
    
    return ordered, cycles


def get_required_dependencies(module_names):
    """
    Get all required dependencies for a list of modules.
    These dependencies MUST be installed regardless of user selection.
    
    Returns:
        List of module names that must also be installed (not including the input modules)
    """
    all_needed, cycles = resolve_all_dependencies(module_names, include_requested=True)
    
    # Warn about cycles in logs (but don't fail)
    for cycle in cycles:
        print(f"[Warning] Dependency cycle detected: {' -> '.join(cycle)}")
    
    # Return only the dependencies, not the originally requested modules
    requested_set = set(module_names)
    return [m for m in all_needed if m not in requested_set]


# ============================================================================
# Config Management
# ============================================================================

def load_full_config():
    """Load the full modules.json config."""
    if not MODULES_CONFIG_FILE.exists():
        return {
            "core_modules": {},
            "modules": {},
            "local_modules": {},
            "meta": {}
        }
    config = load_json_safe(MODULES_CONFIG_FILE)
    # Ensure all sections exist
    config.setdefault("core_modules", {})
    config.setdefault("modules", {})
    config.setdefault("local_modules", {})
    config.setdefault("meta", {})
    return config


def save_full_config(config):
    """Save the full modules.json config after normalizing."""
    MODULES_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_config(config)
    with open(MODULES_CONFIG_FILE, "w") as f:
        json.dump(normalized, f, indent=4)


def normalize_config(config):
    """
    Normalize config to only contain required fields.
    Strips runtime metadata (description, dependencies, exports, version).
    
    Required fields per module:
    - source: "local" | "remote" | "core"
    - sha: string (for installed modules) or null (not installed)
    """
    normalized = {
        "meta": config.get("meta", {}),
        "modules": {},
        "core_modules": {},
        "local_modules": {}
    }
    
    # Get core module names to exclude from regular modules
    core_names = set(config.get("core_modules", {}).keys())
    
    # Normalize regular modules
    for name, state in config.get("modules", {}).items():
        # Skip entries that got duplicated (e.g., "core/block" in modules)
        if name.startswith("core/"):
            continue
        # Skip entries that share a name with core modules (duplicates)
        if name in core_names:
            continue
        normalized["modules"][name] = {
            "source": state.get("source", "remote"),
            "sha": state.get("sha")
        }
    
    # Normalize core modules
    for name, state in config.get("core_modules", {}).items():
        normalized["core_modules"][name] = {
            "source": "core",
            "sha": state.get("sha")
        }
    
    # Normalize local modules (no sha needed)
    for name, state in config.get("local_modules", {}).items():
        normalized["local_modules"][name] = {
            "source": "local"
        }
    
    return normalized


def sync_modules_config(callback=None):
    """
    Sync modules.json with git repo and local filesystem.
    This is the main sanity check function.
    Returns the synchronized config.
    """
    # Ensure cache is up to date
    cache = ensure_module_cache(callback)
    
    # Discover modules from cache
    if cache:
        core_remote, default_remote = discover_modules_from_cache()
    else:
        core_remote, default_remote = {}, {}
    
    # Load current config
    config = load_full_config()
    
    # Sync core modules (always enabled)
    for name, meta in core_remote.items():
        if name not in config["core_modules"]:
            config["core_modules"][name] = {}
        
        # Only save essential fields
        cm = config["core_modules"][name]
        cm["source"] = "core"
        # Preserve existing SHA if present
    
    # Remove core modules that no longer exist in remote
    for name in list(config["core_modules"].keys()):
        if name not in core_remote:
            del config["core_modules"][name]
    
    # Sync default modules
    for name, meta in default_remote.items():
        # Skip if this module is already a core module
        if name in config["core_modules"]:
            continue
        if name not in config["modules"]:
            # New module, not installed yet (no sha)
            config["modules"][name] = {
                "source": "remote",
                "sha": None
            }
        else:
            # Ensure source is correct
            config["modules"][name]["source"] = "remote"
    
    # Mark modules that were removed from remote as orphaned
    for name in list(config["modules"].keys()):
        if name.startswith("core/"):
            # Remove old duplicate core entries (prefixed)
            del config["modules"][name]
        elif name in config["core_modules"]:
            # Remove duplicates that exist in core_modules
            del config["modules"][name]
        elif name not in default_remote and config["modules"][name].get("source") == "remote":
            config["modules"][name]["source"] = "orphaned"
            
    # Discover and sync local modules
    local_discovered = discover_local_modules(set(default_remote.keys()))
    for name, meta in local_discovered.items():
        if name not in config["local_modules"]:
            config["local_modules"][name] = {
                "source": "local"
            }
    
    # Remove local modules that no longer have valid metadata
    for name in list(config["local_modules"].keys()):
        if name not in local_discovered:
            local_path = MODULES_DIR / name
            if not local_path.exists() or not parse_metadata(local_path / "metadata.json"):
                del config["local_modules"][name]
    
    # Update meta
    config["meta"]["last_sync"] = datetime.now().isoformat()
    if cache:
        config["meta"]["repo_commit"] = get_cache_commit_sha()
    
    save_full_config(config)
    return config


# ============================================================================
# Module Installation
# ============================================================================

def copy_module_from_cache(module_name, is_core=False, callback=None, current_local_sha=None):
    """
    Copy a module from cache to templates/module/.
    If current_local_sha is provided, only copy changed files (git diff).
    """
    if is_core:
        src = CACHE_DIR / "core" / module_name
        dest = MODULES_DIR / "core" / module_name
        rel_path = f"core/{module_name}"
    else:
        src = CACHE_DIR / module_name
        dest = MODULES_DIR / module_name
        rel_path = module_name
    
    if not src.exists():
        if callback:
            callback(f"Module {module_name} not found in cache")
        return False
    
    # Check if we can do differential update
    if current_local_sha:
        try:
            # Get changed files between stored SHA and HEAD
            cmd = ["git", "-C", str(CACHE_DIR), "diff", "--name-only", current_local_sha, "HEAD", "--", rel_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                changed_files = [f for f in result.stdout.splitlines() if f.strip()]
                if not changed_files:
                    if callback: callback(f"No changes for {module_name}")
                    return True # Already up to date
                
                if callback:
                    callback(f"Updating {module_name} ({len(changed_files)} files changed)...")
                
                # Copy only changed files
                for changed_file in changed_files:
                    # changed_file is relative to repo root, e.g. "core/block/mod.typ"
                    # We need to map it to dest
                    file_rel_path = Path(changed_file).relative_to(rel_path)
                    src_file = CACHE_DIR / changed_file
                    dest_file = dest / file_rel_path
                    
                    if src_file.exists():
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dest_file)
                    elif dest_file.exists():
                        # File deleted in remote
                        dest_file.unlink()
                
                return True
        except Exception:
            # Fallback to full copy if diff fails
            pass

    if callback:
        callback(f"Installing {module_name}...")
    
    # Remove existing and copy fresh (full install)
    if dest.exists():
        shutil.rmtree(dest)
    
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    return True


def install_modules(module_names, callback=None, current_config=None):
    """
    Install a list of default modules from cache.
    Automatically resolves and installs dependencies first (force-installed).
    Returns dict of {module_name: sha} for successfully installed modules.
    """
    # Ensure cache exists
    if not ensure_module_cache(callback):
        if callback:
            callback("Failed to access module cache")
        return {}
    
    # Resolve all dependencies (topologically sorted - deps first)
    all_modules, cycles = resolve_all_dependencies(module_names, include_requested=True)
    
    # Log any cycles detected
    for cycle in cycles:
        if callback:
            callback(f"Warning: dependency cycle detected: {' -> '.join(cycle)}")
        else:
            print(f"[Warning] Dependency cycle detected: {' -> '.join(cycle)}")
    
    # Report if additional dependencies were added
    deps_added = set(all_modules) - set(module_names)
    if deps_added and callback:
        callback(f"Installing dependencies: {', '.join(deps_added)}")
    
    installed = {}
    total = len(all_modules)
    for i, name in enumerate(all_modules, 1):
        if callback:
            callback(f"Installing {name} ({i}/{total})...")
            
        # Get current local SHA if available for differential update
        current_sha = None
        if current_config and name in current_config.get("modules", {}):
            current_sha = current_config["modules"][name].get("sha")
            
        if copy_module_from_cache(name, is_core=False, callback=callback, current_local_sha=current_sha):
            # Get the SHA for this module
            sha = get_module_sha_from_cache(name, is_core=False)
            if sha:
                installed[name] = sha
    
    if callback:
        callback("Installation complete.")
    
    return installed


def install_core_modules_with_sha(callback=None, current_config=None):
    """
    Install all core modules from cache.
    Returns dict of {module_name: sha} for installed core modules.
    """
    # Ensure cache exists
    if not ensure_module_cache(callback):
        return {}
    
    installed = {}
    core_dir = CACHE_DIR / "core"
    if not core_dir.exists():
        return installed
    
    for d in core_dir.iterdir():
        if d.is_dir() and not d.name.startswith('.'):
            # Get current local SHA if available
            current_sha = None
            if current_config and d.name in current_config.get("core_modules", {}):
                current_sha = current_config["core_modules"][d.name].get("sha")
            
            if copy_module_from_cache(d.name, is_core=True, callback=callback, current_local_sha=current_sha):
                sha = get_module_sha_from_cache(d.name, is_core=True)
                if sha:
                    installed[d.name] = sha
    
    return installed



def install_core_modules(callback=None):
    """Install all core modules from cache."""
    # Ensure cache exists
    if not ensure_module_cache(callback):
        return
    
    core_dir = CACHE_DIR / "core"
    if not core_dir.exists():
        return
    
    for d in core_dir.iterdir():
        if d.is_dir() and not d.name.startswith('.'):
            copy_module_from_cache(d.name, is_core=True, callback=callback)


def ensure_core_modules_installed(callback=None):
    """Ensure all core modules are installed locally."""
    # Ensure cache exists
    if not ensure_module_cache(callback):
        return
    
    core_local = MODULES_DIR / "core"
    core_remote, _ = discover_modules_from_cache()
    
    for name in core_remote:
        local_path = core_local / name
        if not local_path.exists():

            copy_module_from_cache(name, is_core=True, callback=callback)


# ============================================================================
# Legacy compatibility functions
# ============================================================================

def get_installed_modules():
    """Get installed default modules (legacy compatibility)."""
    config = load_full_config()
    return config.get("modules", {})


def save_modules_config(modules):
    """Save default modules (legacy compatibility)."""
    config = load_full_config()
    config["modules"] = modules
    save_full_config(config)


def get_modules_meta():
    """Get meta section (legacy compatibility)."""
    config = load_full_config()
    return config.get("meta", {})


def save_modules_meta(meta):
    """Save meta section (legacy compatibility)."""
    config = load_full_config()
    config["meta"] = meta
    save_full_config(config)


def fetch_remote_modules():
    """Fetch list of default module names from cache (legacy compatibility)."""
    _, default_modules = discover_modules_from_cache()
    return sorted(default_modules.keys())


def fetch_core_submodules():
    """Fetch list of core module names from cache (legacy compatibility)."""
    core_modules, _ = discover_modules_from_cache()
    return sorted(core_modules.keys())


# ============================================================================
# Module helpers
# ============================================================================

def check_dependencies(module_name, index, enabled_modules):
    """Check if module's dependencies are enabled."""
    if module_name not in index:
        return []
    mod_meta = index[module_name]
    deps = mod_meta.get("dependencies", [])
    return [d for d in deps if d not in enabled_modules]


def create_custom_module(name):
    """Create a new custom/local module."""
    mod_dir = MODULES_DIR / name
    if mod_dir.exists():
        return False
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "mod.typ").write_text(f"// Custom module: {name}\n#let hello() = [Hello from {name}!]\n")
    meta = {"name": name, "version": "0.1.0", "dependencies": [], "exports": ["hello"]}
    (mod_dir / "metadata.json").write_text(json.dumps(meta, indent=4))
    
    # Add to config
    config = load_full_config()
    config["local_modules"][name] = {"source": "local"}
    save_full_config(config)
    return True


def get_all_enabled_modules():
    """Get list of all installed module names (core + default + local)."""
    config = load_full_config()
    enabled = []
    
    # Core modules are always enabled
    enabled.extend(config.get("core_modules", {}).keys())
    
    # Installed default modules (have sha)
    for name, state in config.get("modules", {}).items():
        if state.get("sha"):
            enabled.append(name)
    
    # Local modules are always enabled
    enabled.extend(config.get("local_modules", {}).keys())
    
    return enabled
