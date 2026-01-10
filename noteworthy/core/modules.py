import re
import json
from pathlib import Path
from ..config import MODULES_CONFIG_FILE
from ..utils import load_json_safe

MODULES_DIR = Path("templates/module")
CORE_DIR = Path("templates/module/core")
IMPORTS_FILE = Path("templates/core/imports.typ")


def generate_imports_file():
    """Generates templates/core/imports.typ based on enabled modules."""
    lines = []
    
    lines.append("// =====================================================")
    lines.append("// AUTO-GENERATED IMPORTS - DO NOT EDIT MANUALLY")
    lines.append("// Managed by Noteworthy Module Config")
    lines.append("// =====================================================")
    lines.append("")
    
    # Always import core modules (from core/ directory)
    lines.append("// Core Modules (always enabled)")
    if CORE_DIR.exists():
        for core_mod in sorted(CORE_DIR.iterdir()):
            if core_mod.is_dir() and (core_mod / "mod.typ").exists():
                name = core_mod.name
                import_path = f"../module/core/{name}/mod.typ"
                lines.append(f'#import "{import_path}": *')
    lines.append("")
    
    # Load full config with new structure
    config = {}
    if MODULES_CONFIG_FILE.exists():
        config = load_json_safe(MODULES_CONFIG_FILE)
    
    # Get default modules
    modules = config.get("modules", {})
    local_modules = config.get("local_modules", {})
    
    # Combine default and local modules
    all_optional = {}
    all_optional.update(modules)
    all_optional.update(local_modules)
    
    lines.append("// Optional Modules")
    for name in sorted(all_optional.keys()):
        state = all_optional[name]
        status = state.get("status", "disabled")
        
        if status == "disabled":
            continue
        
        # Verify module exists on disk
        mod_path = MODULES_DIR / name / "mod.typ"
        if not mod_path.exists():
            continue
        
        import_path = f"../module/{name}/mod.typ"
        
        if status == "global":
            lines.append(f'#import "{import_path}": *  // {name}')
        elif status == "qualified":
            lines.append(f'#import "{import_path}" as {name}')
    
    IMPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    IMPORTS_FILE.write_text("\n".join(lines) + "\n")


def get_module_conflicts(enabled_modules=None):
    """
    Check for naming collisions between GLOBAL modules.
    Returns dict { "symbol_name": ["mod1", "mod2"] }
    """
    config = {}
    if MODULES_CONFIG_FILE.exists():
        config = load_json_safe(MODULES_CONFIG_FILE)
    
    modules = config.get("modules", {})
    local_modules = config.get("local_modules", {})
    
    sym_map = {}
    
    # Include core modules (always global)
    all_modules = []
    if CORE_DIR.exists():
        for d in CORE_DIR.iterdir():
            if d.is_dir():
                all_modules.append((d.name, d))
    
    # Add global default modules
    for name, state in modules.items():
        if state.get("status") != "global":
            continue
        mod_dir = MODULES_DIR / name
        if mod_dir.exists():
            all_modules.append((name, mod_dir))
    
    # Add global local modules
    for name, state in local_modules.items():
        if state.get("status") != "global":
            continue
        mod_dir = MODULES_DIR / name
        if mod_dir.exists():
            all_modules.append((name, mod_dir))
    
    for name, mod_dir in all_modules:
        meta_file = mod_dir / "metadata.json"
        exports = []
        if meta_file.exists():
            try:
                exports = json.loads(meta_file.read_text()).get("exports", [])
            except:
                pass
        
        if not exports and (mod_dir / "mod.typ").exists():
            content = (mod_dir / "mod.typ").read_text()
            exports = re.findall(r'#let\s+([a-zA-Z][a-zA-Z0-9_-]*)', content)
        
        for sym in exports:
            if sym not in sym_map:
                sym_map[sym] = []
            sym_map[sym].append(name)
    
    return {k: v for k, v in sym_map.items() if len(v) > 1}
