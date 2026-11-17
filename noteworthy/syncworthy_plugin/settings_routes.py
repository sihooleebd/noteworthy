"""Noteworthy's settings API: metadata, constants, hierarchy, preface, snippets,
indexignore, schemes, structure, modules and their blueprints.

Moved from noteworthy/gui/server.py with the routes unchanged; the Syncworthy
plugin mounts this router.  Paths come from noteworthy.config.
"""
import json
import logging

from fastapi import APIRouter, Body

from ..config import (
    BASE_DIR, CONSTANTS_FILE, HIERARCHY_FILE, INDEXIGNORE_FILE, METADATA_FILE,
    PREFACE_FILE, SCHEMES_DIR, SNIPPETS_FILE,
)
from ..utils import scan_content

log = logging.getLogger("noteworthy.syncworthy_plugin")

router = APIRouter()

# ============================================================
# CONFIG API - Specific config file endpoints
# ============================================================

@router.get("/api/metadata")
def get_metadata():
    """Get metadata.json content."""
    try:
        return json.loads(METADATA_FILE.read_text())
    except Exception:
        return {"title": "", "subtitle": "", "authors": [], "affiliation": "", "logo": ""}

@router.post("/api/metadata")
def save_metadata(data: dict = Body(...)):
    """Save metadata.json."""
    METADATA_FILE.write_text(json.dumps(data, indent=2))
    return {"success": True}

@router.get("/api/constants")
def get_constants():
    """Get constants.json content."""
    try:
        return json.loads(CONSTANTS_FILE.read_text())
    except Exception:
        return {}

@router.post("/api/constants")
def save_constants(data: dict = Body(...)):
    """Save constants.json."""
    CONSTANTS_FILE.write_text(json.dumps(data, indent=2))
    return {"success": True}

@router.get("/api/hierarchy")
def get_hierarchy():
    """Get hierarchy.json content."""
    try:
        return {"hierarchy": json.loads(HIERARCHY_FILE.read_text())}
    except Exception:
        return {"hierarchy": []}

def _materialize_hierarchy(hierarchy):
    """Create the content files a hierarchy describes, if they are missing.

    The structure editor used to write hierarchy.json alone, leaving chapters
    and pages with no file behind them -- the document then failed to compile
    with "file not found".

    A hierarchy entry is matched to a chapter folder by POSITION, not by name:
    hierarchy.json carries only titles, and the folder name is the chapter
    number. Naming the folder after the position instead was right only while
    chapters ran 0,1,2,...; with content/8 and content/9 it invented content/0
    and content/1 beside them, so editing the outline silently grew a second,
    empty copy of the book -- and since parser.typ walks the folders in sorted
    order, the stubs displaced the real chapters in the preview.

    Only ever creates: removing an entry leaves its file alone, so nobody
    loses writing by editing the outline.
    """
    created = []
    content_dir = BASE_DIR / "content"
    ch_folders, pg_folders = scan_content(content_dir)

    def _next_name(existing):
        """Continue the existing numbering rather than restarting it."""
        nums = [int(n) for n in existing if str(n).isdigit()]
        return str(max(nums) + 1) if nums else "1"

    for ch_idx, chapter in enumerate(hierarchy):
        if not isinstance(chapter, dict):
            continue
        # The folder this position already means, or the next free number.
        if ch_idx < len(ch_folders):
            ch_name = ch_folders[ch_idx]
        else:
            ch_name = _next_name(ch_folders)
            ch_folders.append(ch_name)
        ch_dir = content_dir / ch_name
        try:
            ch_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.error(f"Could not create chapter directory {ch_dir}: {e}")
            continue
        pages = list(pg_folders.get(ch_name, []))
        for pg_idx, page in enumerate(chapter.get("pages", []) or []):
            # Same rule one level down: a position that already has a file
            # keeps it, whatever it is called.
            if pg_idx < len(pages):
                continue
            pg_name = _next_name(pages)
            pages.append(pg_name)
            page_file = ch_dir / f"{pg_name}.typ"
            if page_file.exists():
                continue
            title = (page or {}).get("title", "") if isinstance(page, dict) else ""
            try:
                page_file.write_text(
                    '#import "../../templates/templater.typ": *\n\n'
                    + (f"= {title}\n" if title else ""),
                    encoding="utf-8")
                created.append(str(page_file.relative_to(BASE_DIR)))
            except OSError as e:
                log.error(f"Could not create page {page_file}: {e}")
    return created


@router.post("/api/hierarchy")
def save_hierarchy(data: dict = Body(...)):
    """Save hierarchy.json and create any content files it introduces."""
    hierarchy = data.get("hierarchy", [])
    HIERARCHY_FILE.write_text(json.dumps(hierarchy, indent=2))
    created = _materialize_hierarchy(hierarchy)
    if created:
        log.info(f"Created content files for new hierarchy entries: {created}")
    return {"success": True, "created": created}

@router.get("/api/preface")
def get_preface():
    """Get preface.typ content."""
    try:
        return {"content": PREFACE_FILE.read_text()}
    except Exception:
        return {"content": "= Preface\n\nEnter your preface here."}

@router.post("/api/preface")
def save_preface(data: dict = Body(...)):
    """Save preface.typ."""
    content = data.get("content", "")
    PREFACE_FILE.write_text(content)
    return {"success": True}

@router.get("/api/snippets")
def get_snippets():
    """Get parsed snippets from snippets.typ."""
    snippets = []
    try:
        content = SNIPPETS_FILE.read_text()
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('#let ') and '=' in line:
                rest = line[5:]
                eq_pos = rest.find('=')
                if eq_pos != -1:
                    name = rest[:eq_pos].strip()
                    definition = rest[eq_pos + 1:].strip()
                    snippets.append({"name": name, "definition": definition})
    except Exception:
        pass
    return {"snippets": snippets}

@router.post("/api/snippets")
def save_snippets(data: dict = Body(...)):
    """Save snippets to snippets.typ."""
    snippets = data.get("snippets", [])
    lines = [f"#let {s['name']} = {s['definition']}" for s in snippets]
    SNIPPETS_FILE.write_text('\n'.join(lines) + '\n')
    return {"success": True}

@router.get("/api/indexignore")
def get_indexignore():
    """Get indexignore patterns."""
    patterns = []
    try:
        content = INDEXIGNORE_FILE.read_text()
        patterns = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
    except Exception:
        pass
    return {"patterns": patterns}

@router.post("/api/indexignore")
def save_indexignore(data: dict = Body(...)):
    """Save indexignore patterns."""
    patterns = data.get("patterns", [])
    INDEXIGNORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEXIGNORE_FILE.write_text('\n'.join(patterns) + '\n')
    return {"success": True}

# ============================================================
# SCHEMES API - Color themes
# ============================================================

@router.get("/api/schemes")
def get_schemes():
    """Get available color schemes."""
    themes = []
    themes_dir = SCHEMES_DIR / "data"
    if themes_dir.exists():
        for f in sorted(themes_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                themes.append({
                    "name": f.stem,
                    "colors": [
                        data.get("page-fill", "#ffffff"),
                        data.get("text-main", "#000000"),
                        data.get("text-accent", "#000000")
                    ]
                })
            except Exception:
                themes.append({"name": f.stem, "colors": []})
    
    active = "default"
    try:
        constants = json.loads(CONSTANTS_FILE.read_text())
        active = constants.get("display-mode", "default")
    except Exception:
        pass
    
    return {"themes": themes, "active": active}

# IMPORTANT: This route must come BEFORE /api/schemes/{name} to avoid conflict
@router.post("/api/schemes/active")
def set_active_scheme(data: dict = Body(...)):
    """Set the active color scheme."""
    theme = data.get("theme")
    if not CONSTANTS_FILE.exists():
        return {"error": "Constants file not found"}
    
    try:
        constants = json.loads(CONSTANTS_FILE.read_text())
        constants["display-mode"] = theme
        CONSTANTS_FILE.write_text(json.dumps(constants, indent=2))
        return {"success": True, "theme": theme}
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/schemes/{name}")
def get_scheme(name: str):
    """Get a specific scheme's data."""
    scheme_file = SCHEMES_DIR / "data" / f"{name}.json"
    try:
        return json.loads(scheme_file.read_text())
    except Exception:
        return {"error": "Scheme not found"}

@router.post("/api/schemes/{name}")
def save_scheme(name: str, data: dict = Body(...)):
    """Save a scheme."""
    scheme_file = SCHEMES_DIR / "data" / f"{name}.json"
    scheme_file.parent.mkdir(parents=True, exist_ok=True)
    scheme_file.write_text(json.dumps(data, indent=2))
    return {"success": True}

# ============================================================
# STRUCTURE API - Content directory scanning
# ============================================================

@router.get("/api/structure")
def get_structure():
    """Scan content/ for chapters and pages."""
    content_dir = BASE_DIR / "content"
    chapters = []
    
    if content_dir.exists():
        ch_dirs = sorted(
            [d for d in content_dir.iterdir() if d.is_dir() and d.name.isdigit()],
            key=lambda d: int(d.name)
        )
        for ch_dir in ch_dirs:
            pages = []
            pg_files = sorted(
                [f for f in ch_dir.glob("*.typ") if f.stem.replace('.', '', 1).isdigit()],
                key=lambda f: float(f.stem) if f.stem.replace('.', '', 1).isdigit() else 999
            )
            for pg_f in pg_files:
                pages.append({
                    "id": pg_f.stem,
                    "path": f"content/{ch_dir.name}/{pg_f.name}"
                })
            chapters.append({
                "id": int(ch_dir.name),
                "pages": pages
            })
    
    return {"chapters": chapters}

# ============================================================
# MODULES API
# ============================================================

@router.get("/api/modules")
def get_modules():
    """Get installed modules."""
    modules = {}
    modules_dir = BASE_DIR / "templates/module"
    if modules_dir.exists():
        for item in modules_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                blueprint_path = item / "blueprint.json"
                modules[item.name] = {
                    "source": "local", 
                    "installed": True,
                    "has_config": blueprint_path.exists()
                }
        
        # Scan core modules
        core_dir = modules_dir / "core"
        if core_dir.exists():
            for item in core_dir.iterdir():
                if item.is_dir():
                    name = f"core/{item.name}"
                    blueprint_path = item / "blueprint.json"
                    modules[name] = {
                        "source": "core", 
                        "installed": True,
                        "has_config": blueprint_path.exists()
                    }
    
    return modules

@router.get("/api/modules/{name:path}/config")
def get_module_config(name: str):
    """Get configuration schema and values for a module."""
    # Locate blueprint
    blueprint_path = BASE_DIR / f"templates/module/{name}/blueprint.json"
    if not blueprint_path.exists():
        blueprint_path = BASE_DIR / f"templates/module/core/{name}/blueprint.json"
    
    if not blueprint_path.exists():
        # Handle case where module exists but has no blueprint (not configurable)
        return {"settings": []}

    try:
        blueprint = json.loads(blueprint_path.read_text())
    except Exception:
        return {"settings": []}

    # Load existing config
    config_path = BASE_DIR / f"config/modules/{name}.json"
    user_config = {}
    if config_path.exists():
        try:
            user_config = json.loads(config_path.read_text())
        except Exception:
            pass

    # Merge values
    settings = []
    for item in blueprint.get("settings", []):
        key = item.get("key")
        if not key: continue
        
        # Use user config value if present, else default
        item["value"] = user_config.get(key, item.get("default"))
        settings.append(item)

    return {"settings": settings}

@router.post("/api/modules/{name:path}/config")
def save_module_config(name: str, data: dict = Body(...)):
    """Save module configuration."""
    config_path = BASE_DIR / f"config/modules/{name}.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # We save the raw dictionary provided by the frontend
    # logic should ensure we only save valid keys if strictness is required,
    # but for now we trust the frontend to send the right structure (key: value)
    
    # However, the frontend might send the whole settings array back?
    # Let's assume the frontend sends a dict of {key: value} pairs.
    
    config_path.write_text(json.dumps(data, indent=4))
    return {"success": True}
