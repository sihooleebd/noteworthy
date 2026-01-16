"""
Noteworthy GUI Solo Server - FastAPI backend (Single-user mode)
No Yjs CRDT, no chat, no collaboration - direct file editing

Works directly on project files via noteworthy.config paths
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import json
import asyncio
import subprocess
import shutil
import os
import re
import tempfile

from ..config import (
    BASE_DIR, BUILD_DIR, OUTPUT_FILE, RENDERER_FILE,
    METADATA_FILE, CONSTANTS_FILE, HIERARCHY_FILE,
    PREFACE_FILE, SNIPPETS_FILE, SCHEMES_DIR,
    MODULES_CONFIG_FILE, INDEXIGNORE_FILE
)
from ..gui.preview import PreviewManager

app = FastAPI(title="Noteworthy Solo GUI")
preview_manager = PreviewManager()

# Store for WebSocket connections (simple single-user presence)
_active_websocket: WebSocket = None
_current_watched_file: str = None  # Track current file for cleanup on switch


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    loop = asyncio.get_running_loop()
    
    def on_preview_bridge(updates, source_path):
        """Bridge thread callback to asyncio loop."""
        asyncio.run_coroutine_threadsafe(
            broadcast_preview(updates, source_path),
            loop
        )
            
    preview_manager.add_callback(on_preview_bridge)
    
    # Sanity check modules.json
    validate_modules_json()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("[Solo Server] Shutdown complete.")


async def broadcast_preview(updates: list, source_path: str):
    """Send preview updates to the client."""
    global _active_websocket
    if _active_websocket:
        try:
            await _active_websocket.send_text(json.dumps({
                "type": "preview",
                "updates": updates,
                "file": source_path
            }))
            print(f"[Debug] Sent preview update for {source_path} ({len(updates)} pages)")
        except Exception as e:
            print(f"[Debug] Broadcast error: {e}")


def validate_modules_json():
    """Validate and recover modules.json if corrupted."""
    if not MODULES_CONFIG_FILE.exists():
        print("[Startup] modules.json not found, will be created on first use")
        return
    
    try:
        data = json.loads(MODULES_CONFIG_FILE.read_text())
        
        # Validate structure
        if not isinstance(data, dict):
            raise ValueError("modules.json root must be an object")
        if 'modules' not in data or not isinstance(data.get('modules'), dict):
            raise ValueError("modules.json must have 'modules' object")
        
        print(f"[Startup] modules.json validated: {len(data['modules'])} modules")
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[Startup] WARNING: modules.json is corrupted ({e}). Regenerating...")
        
        # Backup corrupted file
        backup_path = MODULES_CONFIG_FILE.with_suffix('.json.bak')
        try:
            shutil.copy2(MODULES_CONFIG_FILE, backup_path)
            print(f"[Startup] Backed up corrupted file to {backup_path.name}")
        except Exception:
            pass
        
        # Regenerate from disk state
        regenerate_modules_json()


def regenerate_modules_json():
    """Regenerate modules.json by scanning templates/module directory."""
    modules_dir = BASE_DIR / "templates/module"
    modules = {}
    
    if modules_dir.exists():
        for item in modules_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if item.name == 'core':
                    # Scan core modules
                    for core_item in item.iterdir():
                        if core_item.is_dir():
                            modules[f"core/{core_item.name}"] = {
                                "source": "local",
                                "status": "installed"
                            }
                else:
                    modules[item.name] = {
                        "source": "local",
                        "status": "installed"
                    }
    
    new_data = {
        "meta": {"recovered": True},
        "modules": modules
    }
    
    try:
        MODULES_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        MODULES_CONFIG_FILE.write_text(json.dumps(new_data, indent=4))
        print(f"[Startup] Regenerated modules.json with {len(modules)} modules")
    except Exception as e:
        print(f"[Startup] ERROR: Failed to regenerate modules.json: {e}")


@app.websocket("/ws/doc")
async def doc_endpoint(websocket: WebSocket):
    """
    Simplified document WebSocket for solo mode.
    
    Handles only:
    - Diagnostics updates
    - Preview updates
    
    No collaboration features (cursors, chat, user presence).
    """
    global _active_websocket
    
    await websocket.accept()
    _active_websocket = websocket
    
    try:
        # Send welcome
        await websocket.send_text(json.dumps({
            "type": "welcome",
            "userId": "solo",
            "mode": "solo"
        }))
        
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg["type"] == "join":
                # User joins a file - start watching for preview
                path = msg.get("path") or msg.get("file", "")
                if path:
                    global _current_watched_file
                    _current_watched_file = path
                    
                    # Start watching (will reuse existing watcher if already running)
                    preview_manager.start_watch(path)
                    
                    # Cleanup old watchers but keep recent ones warm (LRU)
                    preview_manager.cleanup_old_watchers(keep_paths=[path], max_watchers=3)
                    
                    # Run diagnostics in BACKGROUND - don't block preview!
                    asyncio.create_task(send_diagnostics_async(websocket, path))
                    
    except WebSocketDisconnect:
        _active_websocket = None
    except Exception as e:
        print(f"[Solo Doc] Error: {e}")
        _active_websocket = None


async def send_diagnostics_async(websocket: WebSocket, path: str):
    """Run diagnostics in background and send to client."""
    try:
        diags = await run_diagnostics_check()
        await websocket.send_text(json.dumps({
            "type": "diagnostics",
            "diagnostics": diags,
            "file": path
        }))
    except Exception as e:
        print(f"[Diagnostics] Background check failed: {e}")


async def run_diagnostics_check():
    """Run typst compile to check for errors."""
    typst_bin = shutil.which("typst")
    if not typst_bin:
        for path in ["/opt/homebrew/bin/typst", "/usr/local/bin/typst", os.path.expanduser("~/.cargo/bin/typst")]:
            if os.path.exists(path):
                typst_bin = path
                break
    
    if not typst_bin:
        return []
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        content_dir = BASE_DIR / "content"
        chapter_folders = []
        page_folders = {}
        
        if content_dir.exists():
            ch_dirs = sorted(
                [d for d in content_dir.iterdir() if d.is_dir() and d.name.replace('.', '', 1).lstrip('-').isdigit()],
                key=lambda d: float(d.name) if d.name.replace('.', '', 1).lstrip('-').isdigit() else 999
            )
            for idx, ch_dir in enumerate(ch_dirs):
                chapter_folders.append(ch_dir.name)
                pg_files = sorted(
                    [f.stem for f in ch_dir.glob("*.typ") if f.stem.replace('.', '', 1).lstrip('-').isdigit()],
                    key=lambda s: float(s) if s.replace('.', '', 1).lstrip('-').isdigit() else 999
                )
                page_folders[str(idx)] = pg_files
        
        # Run in thread pool to avoid blocking event loop
        result = await asyncio.to_thread(
            subprocess.run,
            [
                typst_bin, "compile", str(RENDERER_FILE), tmp_path, 
                "--root", str(BASE_DIR),
                "--input", f"chapter-folders={json.dumps(chapter_folders)}",
                "--input", f"page-folders={json.dumps(page_folders)}"
            ],
            capture_output=True,
            text=True
        )
        
        diagnostics = []
        lines = result.stderr.split('\n')
        current_error = None
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith("error:"):
                msg = stripped[6:].strip()
                current_error = {"message": msg, "severity": "error"}
            
            elif ("┌" in stripped or "├" in stripped) and current_error:
                idx = stripped.find("─")
                if idx != -1:
                    location = stripped[idx+1:].strip()
                    parts = location.split(':')
                    if len(parts) >= 3:
                        try:
                            line_num = int(parts[-2])
                            col_num = int(parts[-1])
                            path_str = ":".join(parts[:-2]).strip()
                            
                            current_error["line"] = line_num
                            current_error["col"] = col_num
                            current_error["file"] = path_str
                            diagnostics.append(current_error)
                            current_error = None
                        except ValueError:
                            pass
        
        return diagnostics
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# Static files
STATIC_DIR = Path(__file__).parent / "static"

# ============================================================
# FILE API - Generic file read/write
# ============================================================

@app.get("/api/file")
def get_file(path: str, raw: int = 0):
    """Read a file relative to project root. If raw=1, return file directly."""
    target = BASE_DIR / path
    if target.exists() and target.is_file():
        if raw:
            import mimetypes
            mime_type, _ = mimetypes.guess_type(str(target))
            return FileResponse(target, media_type=mime_type or 'application/octet-stream')
        try:
            return {"content": target.read_text(encoding='utf-8')}
        except:
            return {"content": "", "error": "Could not read file"}
    return {"error": "File not found"}

@app.post("/api/file")
def save_file(data: dict = Body(...)):
    """Write a file relative to project root."""
    path = data.get("path")
    content = data.get("content", "")
    target = BASE_DIR / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    
    # Preview update is handled by typst watch via file system events
    # No need to manual trigger start_watch which restarts process if ref counting is off
    
    return {"success": True}

@app.post("/api/delete")
def delete_file(data: dict = Body(...)):
    """Delete a file relative to project root."""
    path = data.get("path")
    if not path:
        return {"success": False, "error": "No path provided"}
    
    target = BASE_DIR / path
    if not target.exists():
        return {"success": False, "error": "File not found"}
    
    try:
        target.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        return {"success": False, "error": "Invalid path"}
    
    try:
        if target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/rename")
def rename_file(data: dict = Body(...)):
    """Rename or move a file relative to project root."""
    path = data.get("path")
    new_name = data.get("newName")
    new_path = data.get("newPath")  # Optional: full new path for move operations
    
    if not path:
        return {"success": False, "error": "Missing path"}
    
    if not new_name and not new_path:
        return {"success": False, "error": "Missing newName or newPath"}
    
    source = BASE_DIR / path
    if not source.exists():
        return {"success": False, "error": "File not found"}
    
    # Security check - ensure path is within project
    try:
        source.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        return {"success": False, "error": "Invalid path"}
    
    # Calculate destination path
    if new_path:
        # Full path move
        dest = BASE_DIR / new_path
    else:
        # Simple rename in same directory
        parent_dir = source.parent
        dest = parent_dir / new_name
    
    # Security check - ensure destination is within project
    try:
        dest.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        return {"success": False, "error": "Invalid destination path"}
    
    if dest.exists():
        return {"success": False, "error": "A file with that name already exists"}
    
    try:
        # Create destination directory if it doesn't exist
        dest.parent.mkdir(parents=True, exist_ok=True)
        source.rename(dest)
        result_path = str(dest.relative_to(BASE_DIR))
        return {"success": True, "newPath": result_path}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================
# CONFIG API - Specific config file endpoints
# ============================================================

@app.get("/api/metadata")
def get_metadata():
    """Get metadata.json content."""
    try:
        return json.loads(METADATA_FILE.read_text())
    except:
        return {"title": "", "subtitle": "", "authors": [], "affiliation": "", "logo": ""}

@app.post("/api/metadata")
def save_metadata(data: dict = Body(...)):
    """Save metadata.json."""
    METADATA_FILE.write_text(json.dumps(data, indent=2))
    return {"success": True}

@app.get("/api/constants")
def get_constants():
    """Get constants.json content."""
    try:
        return json.loads(CONSTANTS_FILE.read_text())
    except:
        return {}

@app.post("/api/constants")
def save_constants(data: dict = Body(...)):
    """Save constants.json."""
    CONSTANTS_FILE.write_text(json.dumps(data, indent=2))
    return {"success": True}

@app.get("/api/hierarchy")
def get_hierarchy():
    """Get hierarchy.json content."""
    try:
        return {"hierarchy": json.loads(HIERARCHY_FILE.read_text())}
    except:
        return {"hierarchy": []}

@app.post("/api/hierarchy")
def save_hierarchy(data: dict = Body(...)):
    """Save hierarchy.json."""
    hierarchy = data.get("hierarchy", [])
    HIERARCHY_FILE.write_text(json.dumps(hierarchy, indent=2))
    return {"success": True}

@app.get("/api/preface")
def get_preface():
    """Get preface.typ content."""
    try:
        return {"content": PREFACE_FILE.read_text()}
    except:
        return {"content": "= Preface\n\nEnter your preface here."}

@app.post("/api/preface")
def save_preface(data: dict = Body(...)):
    """Save preface.typ."""
    content = data.get("content", "")
    PREFACE_FILE.write_text(content)
    return {"success": True}

@app.get("/api/snippets")
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
    except:
        pass
    return {"snippets": snippets}

@app.post("/api/snippets")
def save_snippets(data: dict = Body(...)):
    """Save snippets to snippets.typ."""
    snippets = data.get("snippets", [])
    lines = [f"#let {s['name']} = {s['definition']}" for s in snippets]
    SNIPPETS_FILE.write_text('\n'.join(lines) + '\n')
    return {"success": True}

@app.get("/api/indexignore")
def get_indexignore():
    """Get indexignore patterns."""
    patterns = []
    try:
        content = INDEXIGNORE_FILE.read_text()
        patterns = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
    except:
        pass
    return {"patterns": patterns}

@app.post("/api/indexignore")
def save_indexignore(data: dict = Body(...)):
    """Save indexignore patterns."""
    patterns = data.get("patterns", [])
    INDEXIGNORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEXIGNORE_FILE.write_text('\n'.join(patterns) + '\n')
    return {"success": True}

# ============================================================
# SCHEMES API - Color themes
# ============================================================

@app.get("/api/schemes")
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
            except:
                themes.append({"name": f.stem, "colors": []})
    
    active = "default"
    try:
        constants = json.loads(CONSTANTS_FILE.read_text())
        active = constants.get("display-mode", "default")
    except:
        pass
    
    return {"themes": themes, "active": active}

@app.post("/api/schemes/active")
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

@app.get("/api/schemes/{name}")
def get_scheme(name: str):
    """Get a specific scheme's data."""
    scheme_file = SCHEMES_DIR / "data" / f"{name}.json"
    try:
        return json.loads(scheme_file.read_text())
    except:
        return {"error": "Scheme not found"}

@app.post("/api/schemes/{name}")
def save_scheme(name: str, data: dict = Body(...)):
    """Save a scheme."""
    scheme_file = SCHEMES_DIR / "data" / f"{name}.json"
    scheme_file.parent.mkdir(parents=True, exist_ok=True)
    scheme_file.write_text(json.dumps(data, indent=2))
    return {"success": True}

# ============================================================
# STRUCTURE API - Content directory scanning
# ============================================================

@app.get("/api/structure")
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

@app.get("/api/tree")
def get_file_tree():
    """Get complete file tree for editor."""
    def scan(path: Path, rel_base: Path):
        items = []
        try:
            for entry in sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name)):
                if entry.name.startswith('.') or entry.name in ['__pycache__', 'venv', 'build']:
                    continue
                if path == BASE_DIR and entry.name not in ['config', 'content', 'templates']:
                    continue
                
                rel_path = str(entry.relative_to(rel_base))
                item = {"name": entry.name, "path": rel_path, "is_dir": entry.is_dir()}
                if entry.is_dir():
                    item["children"] = scan(entry, rel_base)
                items.append(item)
        except:
            pass
        return items
    
    return {"root": BASE_DIR.name, "items": scan(BASE_DIR, BASE_DIR)}

# ============================================================
# BUILD API
# ============================================================

@app.post("/api/build")
def run_build(data: dict = Body(...)):
    """Execute build process."""
    try:
        from ..core.build_manager import BuildManager
        from ..core.build import merge_pdfs, create_pdf_metadata, apply_pdf_metadata, get_pdf_page_count
        from ..utils import scan_content, load_config_safe
        
        targets = data.get("targets", [])
        options = data.get("options", {})
        
        hierarchy = json.loads(HIERARCHY_FILE.read_text())
        config = load_config_safe() or {}
        
        if BUILD_DIR.exists():
            shutil.rmtree(BUILD_DIR)
        BUILD_DIR.mkdir()
        
        selected_pages = []
        target_chapters = set()
        for t in targets:
            c, p = t.get('chapter'), t.get('page')
            if c is not None and p is not None:
                selected_pages.append((c, p))
                target_chapters.add(c)
        
        filtered_chapters = []
        for ci, ch in enumerate(hierarchy):
            if ci in target_chapters:
                filtered_chapters.append((ci, ch))

        ch_folders, pg_folders = scan_content()
        
        opts = {
            'frontmatter': options.get("frontmatter", True),
            'typst_flags': [],
            'threads': max(1, (os.cpu_count() or 1) // 2),
            'display-cover': options.get("covers", True),
            'display-chap-cover': options.get("covers", True)
        }

        bm = BuildManager(BUILD_DIR)
        callbacks = {} 
        
        pdfs = bm.build_parallel(filtered_chapters, config, opts, callbacks)
        
        current_page_count = sum([get_pdf_page_count(p) for p in pdfs]) + 1
        page_map = bm.page_map
        
        if opts['frontmatter'] and config.get('display-outline', True):
            from ..core.build import compile_target
            out = BUILD_DIR / '02_outline.pdf'
            folder_flags = list(opts['typst_flags'])
            folder_flags.extend(['--input', f'chapter-folders={json.dumps(ch_folders)}'])
            folder_flags.extend(['--input', f'page-folders={json.dumps(pg_folders)}'])
            
            compile_target(
                'outline', out, 
                page_offset=page_map.get('outline', 0), 
                page_map=page_map, 
                extra_flags=folder_flags
            )
            
        if merge_pdfs(pdfs, OUTPUT_FILE):
            bm_file = BUILD_DIR / 'bookmarks.txt'
            bookmarks_list = create_pdf_metadata(filtered_chapters, page_map, bm_file)
            apply_pdf_metadata(OUTPUT_FILE, bm_file, 
                             data.get('meta_title', 'Noteworthy'), 
                             data.get('meta_author', ''), 
                             bookmarks_list)
            
            return {"success": True, "output": f"Build complete! ({current_page_count-1} pages)"}
        else:
            return {"success": False, "output": "Merge failed"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "output": str(e)}

@app.get("/api/download/output.pdf")
def download_output():
    """Download the built PDF."""
    if OUTPUT_FILE.exists():
        return FileResponse(
            OUTPUT_FILE, 
            filename="output.pdf",
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=output.pdf"}
        )
    return {"error": "No output file found"}

@app.post("/api/watch")
def start_watch(data: dict = Body(...)):
    """Start watching a file for preview."""
    path = data.get("path")
    preview_manager.start_watch(path)
    return {"success": True}

# ============================================================
# MODULES API
# ============================================================

@app.get("/api/modules")
def get_modules():
    """Get installed modules and their status."""
    modules = {}
    modules_dir = BASE_DIR / "templates/module"
    if modules_dir.exists():
        for item in modules_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                blueprint_path = item / "blueprint.json"
                modules[item.name] = {
                    "source": "local", 
                    "status": "installed",
                    "has_config": blueprint_path.exists()
                }
        
        core_dir = modules_dir / "core"
        if core_dir.exists():
            for item in core_dir.iterdir():
                if item.is_dir():
                    name = f"core/{item.name}"
                    blueprint_path = item / "blueprint.json"
                    modules[name] = {
                        "source": "core", 
                        "status": "installed",
                        "has_config": blueprint_path.exists()
                    }
    
    return modules

@app.get("/api/modules/{name:path}/config")
def get_module_config(name: str):
    """Get configuration schema and values for a module."""
    blueprint_path = BASE_DIR / f"templates/module/{name}/blueprint.json"
    if not blueprint_path.exists():
        blueprint_path = BASE_DIR / f"templates/module/core/{name}/blueprint.json"
    
    if not blueprint_path.exists():
        return {"settings": []}

    try:
        blueprint = json.loads(blueprint_path.read_text())
    except:
        return {"settings": []}

    config_path = BASE_DIR / f"config/modules/{name}.json"
    user_config = {}
    if config_path.exists():
        try:
            user_config = json.loads(config_path.read_text())
        except:
            pass

    settings = []
    for item in blueprint.get("settings", []):
        key = item.get("key")
        if not key: continue
        
        item["value"] = user_config.get(key, item.get("default"))
        settings.append(item)

    return {"settings": settings}

@app.post("/api/modules/{name:path}/config")
def save_module_config(name: str, data: dict = Body(...)):
    """Save module configuration."""
    config_path = BASE_DIR / f"config/modules/{name}.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config_path.write_text(json.dumps(data, indent=4))
    return {"success": True}

@app.post("/api/check")
async def check_diagnostics(data: dict = Body(...)):
    """Run typst compile to get diagnostics."""
    diagnostics = await run_diagnostics_check()
    return {"diagnostics": diagnostics}

# ============================================================
# STATUS API
# ============================================================

@app.get("/api/status")
def get_status():
    """Get system status."""
    return {
        "project": BASE_DIR.name,
        "path": str(BASE_DIR),
        "preview": preview_manager.get_status(),
        "mode": "solo"
    }

# ============================================================
# Mount Static Files (must be last!)
# ============================================================

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
