"""
Noteworthy GUI Server - FastAPI backend
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
from .preview import PreviewManager
from .crdt_manager import crdt_manager, get_crdt_manager

app = FastAPI(title="Noteworthy GUI")

# Add CORS middleware to allow all origins
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
preview_manager = PreviewManager()

# Emacs Client State
emacs_clients: dict = {}  # user_id -> {"websocket": ws, "name": str, "color": str, "file": str}
EMACS_USER_COLORS = [
    "#FF6B6B", "#4ECDC4", "#FFE66D", "#95E1D3",
    "#F38181", "#AA96DA", "#FCBAD3", "#A8D8EA"
]
emacs_color_index = 0

# DocumentHub - Unified sync manager
from .document_hub import document_hub
import uuid

# Connect preview manager to document hub
document_hub.preview_manager = preview_manager

# Share emacs_clients with document_hub for unified broadcasting
document_hub.emacs_clients = emacs_clients

@app.on_event("startup")
async def startup_event():
    """Register global preview callback on startup."""
    loop = asyncio.get_running_loop()
    
    def on_preview_bridge(updates, source_path):
        """Bridge thread callback to asyncio loop."""
        asyncio.run_coroutine_threadsafe(
            document_hub.on_preview_update(updates, source_path),
            loop
        )
            
    preview_manager.add_callback(on_preview_bridge)
    
    # Register log callback to broadcast to all clients
    def on_log_bridge(level, message):
        """Bridge log messages to asyncio loop for broadcasting."""
        asyncio.run_coroutine_threadsafe(
            document_hub.broadcast_log(level, message),
            loop
        )
    
    preview_manager.add_log_callback(on_log_bridge)
    
    # Sanity check modules.json
    validate_modules_json()


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
    # Log connection attempt
    # print(f"[Server] WS Connect attempt from {websocket.client}")
    try:
        await websocket.accept()
        # print(f"[Server] WS Connected: {websocket.client}")
    except Exception as e:
        print(f"[Server] WS Accept failed: {e}")
        return

    """
    Unified document WebSocket.
    
    Handles:
    - Document sync (content updates)
    - Cursor sharing
    - Diagnostics updates
    - Preview updates
    - Chat
    """
    user_name = websocket.query_params.get("name", "Anonymous")
    user_id = websocket.query_params.get("id", None)
    # await websocket.accept() - ALREADY ACCEPTED ABOVE
    
    user = await document_hub.connect(websocket, user_name, user_id)
    
    try:
        # Send initial state
        await websocket.send_text(json.dumps({
            "type": "joined",
            "userId": user.id,
            "color": user.color,
            "users": document_hub.get_users()
        }))
        
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg["type"] == "join":
                # User opens a file
                path = msg.get("path", "")
                import time
                t0 = time.time()
                doc = await document_hub.join_file(user.id, path)
                t1 = time.time()
                
                if doc:
                    # Get other users on this file for cursor sync
                    other_cursors = document_hub.get_users_on_file(path, exclude_user_id=user.id)
                    
                    # Send file content + cursors together
                    payload = json.dumps({
                        "type": "init",
                        "content": doc.content,
                        "version": doc.version,
                        "cursors": other_cursors
                    })
                    t2 = time.time()
                    await websocket.send_text(payload)
                    t3 = time.time()
                    
                    print(f"[Profiling] Join {path}:")
                    print(f"  Load Doc: {(t1-t0)*1000:.2f}ms")
                    print(f"  Serialize: {(t2-t1)*1000:.2f}ms")
                    print(f"  Send WS: {(t3-t2)*1000:.2f}ms")
                    print(f"  Total: {(t3-t0)*1000:.2f}ms")
                    print(f"  Content Len: {len(doc.content)} chars")
            
            elif msg["type"] == "edit":
                # User edited content
                path = msg.get("path", "")
                content = msg.get("content", "")
                await document_hub.update_content(user.id, path, content)

            elif msg["type"] == "delta":
                # User sent direct delta ops
                path = msg.get("path", "")
                ops = msg.get("ops", [])
                if path and ops:
                    await document_hub.update_content(user.id, path, None, ops=ops)
            
            elif msg["type"] == "cursor":
                await document_hub.update_cursor(
                    user.id,
                    msg.get("line", 1),
                    msg.get("column", 1),
                    msg.get("selectionStartLine"),
                    msg.get("selectionStartColumn"),
                    msg.get("selectionEndLine"),
                    msg.get("selectionEndColumn")
                )
            
            elif msg["type"] == "identity":
                await document_hub.update_identity(
                    user.id, 
                    msg.get("name", "Anonymous")
                )
            
            elif msg["type"] == "chat":
                await document_hub.send_chat(
                    user.id,
                    msg.get("text", ""),
                    msg.get("timestamp", 0)
                )
                
    except WebSocketDisconnect:
        await document_hub.disconnect(user.id, websocket)
    except Exception as e:
        print(f"[Doc] Error: {e}")
        await document_hub.disconnect(user.id, websocket)


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
            # Return file directly for binary content (PDF, images)
            import mimetypes
            mime_type, _ = mimetypes.guess_type(str(target))
            return FileResponse(target, media_type=mime_type or 'application/octet-stream')
        try:
            return {"content": target.read_text(encoding='utf-8')}
        except:
            return {"content": "", "error": "Could not read file"}
    return {"error": "File not found"}

@app.post("/api/file")
async def save_file(data: dict = Body(...)):
    """
    Write a file relative to project root.
    
    Updated to use DocumentHub for unified sync. 
    This ensures changes via HTTP (Web App) are broadcast to Emacs/CRDT.
    """
    path = data.get("path")
    content = data.get("content", "")
    
    # Use DocumentHub to update content
    # This will:
    # 1. Update CRDT state
    # 2. Broadcast to Emacs and other Web clients
    # 3. Trigger debounced save to disk via YjsProvider
    await document_hub.update_content("http_api", path, content)
    
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
    
    # Security check - ensure path is within project
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
    """Rename a file relative to project root."""
    path = data.get("path")
    new_name = data.get("newName")
    
    if not path or not new_name:
        return {"success": False, "error": "Missing path or newName"}
    
    source = BASE_DIR / path
    if not source.exists():
        return {"success": False, "error": "File not found"}
    
    # Security check - ensure path is within project
    try:
        source.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        return {"success": False, "error": "Invalid path"}
    
    # Calculate new path
    parent_dir = source.parent
    dest = parent_dir / new_name
    
    # Check if destination already exists
    if dest.exists():
        return {"success": False, "error": "A file with that name already exists"}
    
    try:
        source.rename(dest)
        new_path = str(dest.relative_to(BASE_DIR))
        return {"success": True, "newPath": new_path}
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

# IMPORTANT: This route must come BEFORE /api/schemes/{name} to avoid conflict
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
                # Only show config, content, templates
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
        # Import core build components
        from ..core.build_manager import BuildManager
        from ..core.build import merge_pdfs, create_pdf_metadata, apply_pdf_metadata, get_pdf_page_count
        from ..utils import scan_content, load_config_safe
        
        targets = data.get("targets", [])
        options = data.get("options", {})
        
        # Load data
        hierarchy = json.loads(HIERARCHY_FILE.read_text())
        config = load_config_safe() or {}
        
        # Prepare build directory
        if BUILD_DIR.exists():
            shutil.rmtree(BUILD_DIR)
        BUILD_DIR.mkdir()
        
        # Group targets by chapter
        # targets is list of {chapter: int, page: int} (indices)
        selected_pages = []
        target_chapters = set()
        for t in targets:
            c, p = t.get('chapter'), t.get('page')
            if c is not None and p is not None:
                selected_pages.append((c, p))
                target_chapters.add(c)
                
        # Prepare chapters list for BuildManager
        # We filter the hierarchy to only include selected pages to avoid building everything
        # However, BuildManager logic runs based on chapters list.
        # We will reconstruct a temporary hierarchy-like list.
        # Note: To preserve file naming consistency, we might want to respect original indices if BuildManager allows.
        # BuildManager uses `enumerate(ch['pages'])` so indices are 0, 1, 2...
        # If we change the list, indices change.
        # For simplicity in this fix, we will build what is requested.
        
        filtered_chapters = []
        for ci, ch in enumerate(hierarchy):
            if ci in target_chapters:
                # Get selected pages for this chapter
                pages_indices = [p for c, p in selected_pages if c == ci]
                # If we want to only build selected pages, we would filter here.
                # But BuildManager logic is coupled with file naming.
                # Use a simplified approach: pass the whole hierarchy subset for now
                # allowing BuildManager to build full chapters if selected. 
                # (Refining this to page-level is safer left for a deeper refactor if needed, 
                # but let's try to just pass the relevant chapters).
                filtered_chapters.append((ci, ch))

        # Scan folders (needed for flags)
        ch_folders, pg_folders = scan_content()
        
        # Build options
        opts = {
            'frontmatter': options.get("frontmatter", True),
            'typst_flags': [],
            'threads': max(1, (os.cpu_count() or 1) // 2),
            'display-cover': options.get("covers", True),   # Map 'covers' to display-cover
            'display-chap-cover': options.get("covers", True)
        }

        # Initialize BuildManager
        bm = BuildManager(BUILD_DIR)
        callbacks = {} 
        
        # Run Build
        pdfs = bm.build_parallel(filtered_chapters, config, opts, callbacks)
        
        # Merge
        current_page_count = sum([get_pdf_page_count(p) for p in pdfs]) + 1
        page_map = bm.page_map
        
        # Outline
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
            
        # Final Merge
        if merge_pdfs(pdfs, OUTPUT_FILE):
            # Metadata
            bm_file = BUILD_DIR / 'bookmarks.txt'
            # We pass filtered_chapters here so bookmarks match what was built
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

# Legacy endpoints - prevent crash if old clients connect
@app.websocket("/ws/collab")
async def legacy_collab(websocket: WebSocket):
    await websocket.close()

@app.websocket("/ws/sync")
async def legacy_sync(websocket: WebSocket):
    await websocket.close()

@app.websocket("/ws")
async def legacy_ws(websocket: WebSocket):
    print(f"[Server] LEGACY /ws HIT by {websocket.client}. Client is likely OUTDATED.")
    await websocket.accept()
    await websocket.send_text("Error: Endpoint moved to /ws/doc. Please reload.")
    await websocket.close()

@app.post("/api/watch")
def start_watch(data: dict = Body(...)):
    """Start watching a file for preview."""
    path = data.get("path")
    preview_manager.start_watch(path)
    return {"success": True}

# ============================================================
# FULL PREVIEW API
# ============================================================

@app.get("/api/preview/full/url")
def get_full_preview_url():
    """Get the URL for the full document preview (tinymist)."""
    url = preview_manager.get_full_preview_url()
    return {"url": url, "running": preview_manager.full_preview_running}

@app.post("/api/preview/full/start")
def start_full_preview():
    """Start the full document preview."""
    url = preview_manager.start_full_preview()
    return {"success": url is not None, "url": url}

@app.post("/api/preview/full/stop")
def stop_full_preview():
    """Stop the full document preview."""
    preview_manager.stop_full_preview()
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
        
        # Scan core modules
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
    # Locate blueprint
    blueprint_path = BASE_DIR / f"templates/module/{name}/blueprint.json"
    if not blueprint_path.exists():
        blueprint_path = BASE_DIR / f"templates/module/core/{name}/blueprint.json"
    
    if not blueprint_path.exists():
        # Handle case where module exists but has no blueprint (not configurable)
        return {"settings": []}

    try:
        blueprint = json.loads(blueprint_path.read_text())
    except:
        return {"settings": []}

    # Load existing config
    config_path = BASE_DIR / f"config/modules/{name}.json"
    user_config = {}
    if config_path.exists():
        try:
            user_config = json.loads(config_path.read_text())
        except:
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

@app.post("/api/modules/{name:path}/config")
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

@app.post("/api/check")
async def check_diagnostics(data: dict = Body(...)):
    """Run typst compile to get diagnostics."""
    import shutil
    
    # Find typst binary
    typst_bin = shutil.which("typst")
    if not typst_bin:
        # Try common paths
        for path in ["/opt/homebrew/bin/typst", "/usr/local/bin/typst", os.path.expanduser("~/.cargo/bin/typst")]:
            if os.path.exists(path):
                typst_bin = path
                break
    
    if not typst_bin:
        print("[LSP] typst binary not found!")
        return {"diagnostics": [], "error": "typst not found"}
    
    # Create temp file for output
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # Scan content directory to get actual chapter/page structure
        content_dir = BASE_DIR / "content"
        chapter_folders = []
        page_folders = {}
        
        if content_dir.exists():
            # Get sorted chapter directories (numeric order)
            ch_dirs = sorted(
                [d for d in content_dir.iterdir() if d.is_dir() and d.name.replace('.', '', 1).lstrip('-').isdigit()],
                key=lambda d: float(d.name) if d.name.replace('.', '', 1).lstrip('-').isdigit() else 999
            )
            for idx, ch_dir in enumerate(ch_dirs):
                chapter_folders.append(ch_dir.name)
                # Get sorted page files (numeric order, without .typ extension)
                pg_files = sorted(
                    [f.stem for f in ch_dir.glob("*.typ") if f.stem.replace('.', '', 1).lstrip('-').isdigit()],
                    key=lambda s: float(s) if s.replace('.', '', 1).lstrip('-').isdigit() else 999
                )
                page_folders[str(idx)] = pg_files
        
        # Run typst compile with folder info
        result = subprocess.run(
            [
                typst_bin, "compile", str(RENDERER_FILE), tmp_path, 
                "--root", str(BASE_DIR),
                "--input", f"chapter-folders={json.dumps(chapter_folders)}",
                "--input", f"page-folders={json.dumps(page_folders)}"
            ],
            capture_output=True,
            text=True
        )
        
        print(f"[LSP] typst stderr: {result.stderr}")
        print(f"[LSP] typst returncode: {result.returncode}")
        
        diagnostics = []
        lines = result.stderr.split('\n')
        current_error = None
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith("error:"):
                msg = stripped[6:].strip()
                current_error = {"message": msg, "severity": "error"}
            
            # Typst uses Unicode box-drawing: ┌─ file:line:col
            elif ("┌" in stripped or "├" in stripped) and current_error:
                # Extract location after the box character
                # Format: ┌─ file.typ:line:col or ├─ file.typ:line:col
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
        
        print(f"[LSP] Parsed diagnostics: {diagnostics}")
        return {"diagnostics": diagnostics}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================================================
# EMACS CRDT WebSocket - Real-time collaboration for Emacs
# ============================================================

@app.websocket("/ws/emacs")
async def emacs_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Emacs clients.
    
    Uses simple JSON protocol for CRDT synchronization as a bridge to YjsProvider.
    """
    global emacs_color_index
    
    await websocket.accept()
    
    # Assign user identity
    user_name = websocket.query_params.get("name", "Emacs User")
    user_id = str(uuid.uuid4())[:8]
    user_color = EMACS_USER_COLORS[emacs_color_index % len(EMACS_USER_COLORS)]
    emacs_color_index += 1
    
    current_file = None
    observer_callback = None
    
    # Register client
    emacs_clients[user_id] = {
        "websocket": websocket,
        "name": user_name,
        "color": user_color,
        "file": None
    }
    
    print(f"[Emacs] Client connected: {user_name} ({user_id})")

    # Connect to DocumentHub to enable cursor/presence sharing
    # We pass the same websocket so Hub can broadcast to it if needed
    hub_user = await document_hub.connect(websocket, user_name, user_id)
    # Override color to match Emacs specific color if desirable, or let Hub decide
    hub_user.color = user_color

    # Send welcome message
    await websocket.send_json({
        "type": "welcome",
        "userId": user_id,
        "color": user_color
    })
    
    async def send_log(level: str, message: str):
        try:
            await websocket.send_json({
                "type": "log",
                "level": level,
                "message": message
            })
        except:
            pass
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "join":
                file_path = data.get("file", "")

                try:
                    if os.path.isabs(file_path):
                        file_path = str(Path(file_path).relative_to(BASE_DIR))
                except ValueError:
                    pass
                
                # Leave previous file
                if current_file and observer_callback:
                    crdt_manager.remove_observer(current_file, observer_callback)
                
                # Update Hub state for this user so get_users_on_file works
                if current_file:
                    hub_user.current_file = None
                
                current_file = file_path
                emacs_clients[user_id]["file"] = file_path
                hub_user.current_file = file_path # CRITICAL for cursor broadcast routing
                
                # Ensure document room exists via adapter
                await crdt_manager.get_or_create_room(file_path)
                content = await crdt_manager.get_content(file_path)
                version = await crdt_manager.get_version(file_path)
                
                # Restore observer to get updates from Yjs (Web) -> Emacs
                # This callback runs in the Yjs thread/context, so we need to bridge to async
                loop = asyncio.get_running_loop()
                
                def observer_callback_sync(fpath, delta, ver):
                    # Only send if it's for our file
                    if fpath == file_path:
                        print(f"[EmacsObserver] Sending delta to {user_id} for {fpath}: {delta}")
                        # Schedule sending on the event loop
                        asyncio.run_coroutine_threadsafe(
                            websocket.send_json({
                                "type": "delta",
                                "file": fpath,
                                "ops": delta,
                                "version": ver,
                                "source": "web" # Indicate this came from web/others
                            }),
                            loop
                        )
                    else:
                        print(f"[EmacsObserver] Ignoring update for {fpath} (watching {file_path})")
                
                observer_callback = observer_callback_sync
                crdt_manager.add_observer(file_path, observer_callback)
                
                # Send initial content
                await websocket.send_json({
                    "type": "sync", 
                    "file": file_path, 
                    "content": content, 
                    "version": version
                })
                
                await send_log("info", f"Joined: {file_path}")
                
                # Notify others
                await broadcast_to_emacs_file(file_path, {
                    "type": "users",
                    "file": file_path,
                    "users": get_emacs_users_in_file(file_path)
                }, exclude=user_id)
            
            elif msg_type == "delta":
                file_from_msg = data.get("file")
                ops = data.get("ops", [])
                target_file = file_from_msg or current_file
                
                if target_file and ops:
                    # Normalize path: Emacs might send absolute path
                    try:
                        if os.path.isabs(target_file):
                            target_file = str(Path(target_file).relative_to(BASE_DIR))
                    except ValueError:
                        pass

                    # Apply delta to CRDT (updates the document)
                    success = await crdt_manager.apply_delta(target_file, ops, source_user=user_id)
                    if success:
                        # Get updated content and broadcast via unified hub
                        content = await crdt_manager.get_content(target_file)
                        
                        # PASS OPS SO THEY CAN BE BROADCAST AS DELTAS
                        await document_hub.update_content(user_id, target_file, content, skip_crdt=True, ops=ops)
                    else:
                        await send_log("error", f"Failed to apply delta to {target_file}, sending full sync")
                        # Send full sync so client can recover
                        content = await crdt_manager.get_content(target_file)
                        version = await crdt_manager.get_version(target_file)
                        await websocket.send_json({
                            "type": "sync",
                            "file": target_file,
                            "content": content,
                            "version": version
                        })
            
            elif msg_type == "cursor":
                current_file = emacs_clients[user_id].get("file")
                if current_file:
                    # Update hub state and broadcast to ALL clients (Web + Emacs)
                    await document_hub.update_cursor(
                        user_id, 
                        data.get("line", 1), 
                        data.get("col", 1)
                    )
            
            elif msg_type == "leave":
                current_file = emacs_clients[user_id].get("file")
                observer_callback = emacs_clients[user_id].get("observer_callback")
                if current_file and observer_callback:
                    crdt_manager.remove_observer(current_file, observer_callback)
                emacs_clients[user_id]["file"] = None
                emacs_clients[user_id]["observer_callback"] = None
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[Emacs] Error for {user_id}: {e}")
    finally:
        if current_file and observer_callback:
            crdt_manager.remove_observer(current_file, observer_callback)
        if user_id in emacs_clients:
            del emacs_clients[user_id]
        
        # Cleanup from DocumentHub (broadcasts user_left)
        await document_hub.disconnect(user_id)
            
        print(f"[Emacs] Disconnected: {user_name}")


async def broadcast_to_emacs_file(file_path: str, message: dict, exclude: str = None):
    msg_json = json.dumps(message)
    for uid, client in list(emacs_clients.items()):
        if uid == exclude: continue
        if client.get("file") == file_path:
            try:
                await client["websocket"].send_text(msg_json)
            except: pass

def get_emacs_users_in_file(file_path: str) -> list:
    users = []
    for uid, client in emacs_clients.items():
        if client.get("file") == file_path:
            users.append({
                "id": uid, 
                "name": client["name"], 
                "color": client["color"]
            })
    return users


# ============================================================
# STATUS API
# ============================================================

@app.get("/api/status")
def get_status():
    """Get system status."""
    return {
        "project": BASE_DIR.name,
        "path": str(BASE_DIR),
        "preview": preview_manager.get_status()
    }

# ============================================================
# Mount Yjs CRDT WebSocket (for collaborative editing)
# ============================================================

try:
    from .yjs_provider import get_yjs_asgi_app
    app.mount("/yjs", get_yjs_asgi_app())
    print("[Server] Yjs CRDT WebSocket mounted at /yjs")
except ImportError as e:
    print(f"[Server] Yjs CRDT not available (pycrdt-websocket not installed): {e}")
    print("[Server] Collaborative editing will use fallback sync mechanism")

# ============================================================
# Mount Static Files (must be last!)
# ============================================================

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

