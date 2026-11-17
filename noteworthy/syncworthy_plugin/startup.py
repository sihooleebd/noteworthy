"""Startup work for a Noteworthy project: modules.json sanity, the imports file, the preface stub."""
import json
import logging
import shutil

from ..config import BASE_DIR, MODULES_CONFIG_FILE

log = logging.getLogger("noteworthy.syncworthy_plugin")


def validate_modules_json():
    """Validate and recover modules.json if corrupted."""
    if not MODULES_CONFIG_FILE.exists():
        log.info("modules.json not found, will be created on first use")
        return
    
    try:
        data = json.loads(MODULES_CONFIG_FILE.read_text())
        
        # Validate structure
        if not isinstance(data, dict):
            raise ValueError("modules.json root must be an object")
        if 'modules' not in data or not isinstance(data.get('modules'), dict):
            raise ValueError("modules.json must have 'modules' object")
        
        log.info(f"modules.json validated: {len(data['modules'])} modules")
        
    except (json.JSONDecodeError, ValueError) as e:
        log.warning(f"modules.json is corrupted ({e}). Regenerating...")
        
        # Backup corrupted file
        backup_path = MODULES_CONFIG_FILE.with_suffix('.json.bak')
        try:
            shutil.copy2(MODULES_CONFIG_FILE, backup_path)
            log.info(f"Backed up corrupted modules.json to {backup_path.name}")
        except Exception:
            pass
        
        # Regenerate from disk state
        regenerate_modules_json()


def regenerate_modules_json():
    """Regenerate modules.json by scanning templates/module directory."""
    modules_dir = BASE_DIR / "templates/module"
    modules = {}
    core_modules = {}
    
    if modules_dir.exists():
        for item in modules_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if item.name == 'core':
                    # Scan core modules
                    for core_item in item.iterdir():
                        if core_item.is_dir():
                            core_modules[core_item.name] = {
                                "source": "core",
                                "sha": None
                            }
                else:
                    modules[item.name] = {
                        "source": "local",
                        "sha": None
                    }
    
    new_data = {
        "meta": {"recovered": True},
        "modules": modules,
        "core_modules": core_modules,
        "local_modules": {}
    }
    
    try:
        MODULES_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        MODULES_CONFIG_FILE.write_text(json.dumps(new_data, indent=4))
        log.info(f"Regenerated modules.json with {len(modules)} modules + {len(core_modules)} core modules")
    except Exception as e:
        log.error(f"Failed to regenerate modules.json: {e}")


def ensure_preface():
    """Ensure preface.typ exists to prevent build errors."""
    from ..config import PREFACE_FILE
    if PREFACE_FILE.parent.exists() and not PREFACE_FILE.exists():
        try:
            PREFACE_FILE.write_text('')
        except Exception as e:
            log.warning(f"Could not create default preface: {e}")


def sync_imports():
    """Sync imports.typ with installed modules."""
    try:
        from ..core.modules import generate_imports_file
        generate_imports_file()
    except Exception as e:
        log.warning(f"Could not sync module imports: {e}")
