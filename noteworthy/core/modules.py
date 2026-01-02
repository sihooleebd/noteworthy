import re
import json
from pathlib import Path
from ..config import MODULES_CONFIG_FILE
from ..utils import load_json_safe

MODULES_DIR = Path("templates/module")
IMPORTS_FILE = Path("templates/core/imports.typ")

def generate_imports_file():
    """Generates templates/core/imports.typ based on enabled modules."""
    if not MODULES_CONFIG_FILE.exists():
        return
        
    config = load_json_safe(MODULES_CONFIG_FILE).get("modules", {})
    lines = []
    
    lines.append("// =====================================================")
    lines.append("// AUTO-GENERATED IMPORTS - DO NOT EDIT MANUALLY")
    lines.append("// Managed by Noteworthy Module Config")
    lines.append("// =====================================================")
    lines.append("")
    
    # Sort for deterministic output
    for name in sorted(config.keys()):
        state = config[name]
        status = state.get("status", "disabled")
        
        # Verify module exists on disk
        mod_path = MODULES_DIR / name / "mod.typ"
        if not mod_path.exists():
            continue
            
        # Path relative to templates/core/imports.typ -> templates/module/name/mod.typ
        # core/.. -> templates -> module -> name -> mod.typ
        # So: "../module/name/mod.typ"
        import_path = f"../module/{name}/mod.typ"
        
        if status == "global":
            lines.append(f"// Module: {name} (Global)")
            lines.append(f'#import "{import_path}": *')
            lines.append("")
        elif status == "qualified":
            lines.append(f"// Module: {name} (Qualified)")
            lines.append(f'#import "{import_path}" as {name}')
            lines.append("")
        elif status == "disabled":
            lines.append(f"// Module: {name} (Disabled)")
            
    IMPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    IMPORTS_FILE.write_text("\n".join(lines))

def get_module_conflicts():
    """
    Check for naming collisions between GLOBAL modules.
    Returns dict { "symbol_name": ["mod1", "mod2"] }
    """
    if not MODULES_CONFIG_FILE.exists(): return {}
    config = load_json_safe(MODULES_CONFIG_FILE).get("modules", {})
    
    sym_map = {} # symbol -> list of modules
    
    for name, state in config.items():
        if state.get("status") != "global":
            continue
            
        mod_dir = MODULES_DIR / name
        if not mod_dir.exists(): continue
        
        # Try reading metadata.json first
        meta_file = mod_dir / "metadata.json"
        exports = []
        if meta_file.exists():
            try:
                exports = json.loads(meta_file.read_text()).get("exports", [])
            except: pass
        
        # If no metadata, fallback to regex scan of mod.typ (simple)
        if not exports and (mod_dir / "mod.typ").exists():
             content = (mod_dir / "mod.typ").read_text()
             # Simple scan for #let
             exports = re.findall(r'#let\s+([a-zA-Z][a-zA-Z0-9_-]*)', content)
             
        for sym in exports:
            if sym not in sym_map: sym_map[sym] = []
            sym_map[sym].append(name)
            
    # Filter for actual conflicts
    return {k: v for k, v in sym_map.items() if len(v) > 1}
