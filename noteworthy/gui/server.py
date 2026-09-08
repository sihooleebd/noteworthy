"""
Noteworthy GUI Server - FastAPI backend
Works directly on project files via noteworthy.config paths
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, File, Form, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
import json
import asyncio
import logging
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

log = logging.getLogger("noteworthy.gui")

# FastAPI's File()/Form() params need python-multipart to parse multipart
# bodies — and it inspects this at route-registration time, so a missing
# dependency would otherwise take down the whole module import, not just
# the upload endpoint. See /api/upload below.
try:
    from python_multipart import __version__ as _  # noqa: F401
    _MULTIPART_AVAILABLE = True
except ImportError:
    _MULTIPART_AVAILABLE = False

# Track the WebSocket server background task
_yjs_server_task: asyncio.Task | None = None

# The asyncio loop owning the websockets, captured at startup so sync
# handlers running in FastAPI's threadpool (e.g. run_build) can hand
# broadcasts back to it via run_coroutine_threadsafe.
_main_loop: asyncio.AbstractEventLoop | None = None


class SafeStaticFiles(StaticFiles):
    """Static file mount that safely ignores websocket fallthrough."""

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1000})
            return
        await super().__call__(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: preview bridge + Yjs server. Shutdown: stop Yjs server."""
    global _yjs_server_task, _main_loop

    loop = asyncio.get_running_loop()
    _main_loop = loop

    def on_preview_bridge(updates, source_path):
        """Bridge thread callback to asyncio loop."""
        asyncio.run_coroutine_threadsafe(
            document_hub.on_preview_update(updates, source_path),
            loop
        )

    def on_preview_log(level, message, source_path=None):
        """Bridge preview logs from worker threads to connected clients."""
        asyncio.run_coroutine_threadsafe(
            document_hub.on_preview_log(level, message, source_path),
            loop
        )

    preview_manager.stop_full_preview()
    preview_manager.add_callback(on_preview_bridge)
    preview_manager.add_log_callback(on_preview_log)

    # Sanity check modules.json
    validate_modules_json()

    # Start Yjs WebSocket Server as a background task.
    # In pycrdt-websocket 0.16+, the server must be explicitly started
    # and we must wait for it to be ready before accepting connections.
    if yjs_provider.server:
        log.info("Starting Yjs WebSocket Server...")
        _yjs_server_task = asyncio.create_task(yjs_provider.server.start())
        await yjs_provider.server.started.wait()
        log.info("Yjs WebSocket Server started and ready")

    yield

    if yjs_provider.server:
        log.info("Stopping Yjs WebSocket Server...")
        await yjs_provider.server.stop()

    if _yjs_server_task and not _yjs_server_task.done():
        _yjs_server_task.cancel()
        try:
            await _yjs_server_task
        except asyncio.CancelledError:
            pass

    preview_manager.stop_full_preview()
    log.info("Shutdown complete.")


app = FastAPI(title="Noteworthy GUI", lifespan=lifespan)
preview_manager = PreviewManager()

# DocumentHub - Unified sync manager
from .document_hub import document_hub

# Connect preview manager to document hub
document_hub.preview_manager = preview_manager

# Mount Yjs WebSocket endpoint
from .yjs_provider import get_yjs_asgi_app, yjs_provider
app.mount("/yjs", get_yjs_asgi_app())


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


@app.websocket("/ws/doc")
async def doc_endpoint(websocket: WebSocket):
    """
    Doc-socket: Chat, Preview, File Presence, Identity.

    Strict packet separation — does NOT handle content sync or cursors.
    Those are exclusively handled by the Yjs WebSocket (/yjs).
    """
    user_name = websocket.query_params.get("name", "Anonymous")
    user_id = websocket.query_params.get("id", None)
    user_token = websocket.query_params.get("token", None)
    await websocket.accept()
    
    user = await document_hub.connect(websocket, user_name, user_id, token=user_token)
    
    try:
        # Send initial state
        await websocket.send_text(json.dumps({
            "type": "welcome",
            "userId": user.id,
            "color": user.color,
            "users": document_hub.get_users()
        }))
        
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                log.warning(f"Ignoring malformed JSON from {user.id}")
                continue
            msg_type = msg.get("type")
            
            if msg_type == "join":
                path = msg.get("path") or msg.get("file", "")
                await document_hub.join_file(user.id, path)

            elif msg_type == "identity":
                await document_hub.update_identity(
                    user.id,
                    msg.get("name", "Anonymous")
                )

            elif msg_type == "chat":
                await document_hub.send_chat(
                    user.id,
                    msg.get("text") or msg.get("message", ""),
                    msg.get("timestamp", 0)
                )
            elif msg_type == "cursor":
                # Real-time cursor position broadcast.
                # Build a canonical payload from server-owned identity fields.
                file_path = msg.get("file")
                if not file_path:
                    continue

                def int_field(key: str, default: int) -> int:
                    try:
                        return int(msg.get(key, default))
                    except (TypeError, ValueError):
                        return default

                line = int_field("line", 1)
                col = int_field("col", 1)
                sel_start_line = int_field("selStartLine", line)
                sel_start_col = int_field("selStartCol", col)
                sel_end_line = int_field("selEndLine", line)
                sel_end_col = int_field("selEndCol", col)

                cursor_msg = {
                    "type": "cursor",
                    "userId": user.id,
                    "file": file_path,
                    "line": line,
                    "col": col,
                    "selStartLine": sel_start_line,
                    "selStartCol": sel_start_col,
                    "selEndLine": sel_end_line,
                    "selEndCol": sel_end_col,
                    "name": user.name,
                    "color": msg.get("color") or user.color,
                    "token": user.token,
                }
                await document_hub._broadcast(cursor_msg, exclude=user.id)

            # delta, users, content, operation, ack, resync are
            # Yjs-layer packets — silently ignored on this socket.
                
    except WebSocketDisconnect:
        await document_hub.disconnect(user.id, websocket)
    except Exception as e:
        log.error(f"Doc socket error: {e}")
        await document_hub.disconnect(user.id, websocket)


# Static files
STATIC_DIR = Path(__file__).parent / "static"

# ============================================================
# FILE API - Generic file read/write
# ============================================================

def _resolve_in_project(path: str):
    """Resolve a user-supplied path, rejecting anything outside BASE_DIR."""
    if not path:
        return None
    target = BASE_DIR / path
    try:
        target.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        return None
    return target


@app.get("/api/file")
def get_file(path: str, raw: int = 0):
    """Read a file relative to project root. If raw=1, return file directly."""
    target = _resolve_in_project(path)
    if target is None:
        return {"error": "Invalid path"}
    if target.exists() and target.is_file():
        if raw:
            # Return file directly for binary content (PDF, images)
            import mimetypes
            mime_type, _ = mimetypes.guess_type(str(target))
            return FileResponse(target, media_type=mime_type or 'application/octet-stream')
        try:
            return {"content": target.read_text(encoding='utf-8')}
        except Exception:
            return {"content": "", "error": "Could not read file"}
    return {"error": "File not found"}

@app.post("/api/file")
def save_file(data: dict = Body(...)):
    """Write a file relative to project root."""
    path = data.get("path")
    content = data.get("content", "")
    target = _resolve_in_project(path)
    if target is None:
        return {"success": False, "error": "Invalid path"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    return {"success": True}

if _MULTIPART_AVAILABLE:
    @app.post("/api/upload")
    async def upload_files(files: list[UploadFile] = File(...), directory: str = Form("")):
        """Upload one or more files into a project-relative directory."""
        saved = []
        errors = []
        for f in files:
            # Only trust the basename — a crafted filename like "../../x" must
            # not be able to walk out of `directory`.
            filename = os.path.basename(f.filename or "")
            if not filename:
                errors.append("Skipped a file with no name")
                continue
            rel_path = f"{directory}/{filename}" if directory else filename
            dest = _resolve_in_project(rel_path)
            if dest is None:
                errors.append(f"Rejected unsafe path: {f.filename}")
                continue
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                content = await f.read()
                dest.write_bytes(content)
                saved.append(str(dest.relative_to(BASE_DIR)))
            except Exception as e:
                errors.append(f"{filename}: {e}")

        return {"success": bool(saved) and not errors, "saved": saved, "errors": errors}
else:
    # FastAPI's File()/Form() params require python-multipart to even be
    # *registered* (it inspects the signature at route-decoration time), so
    # we can't define the real route unless the dependency is present. Fall
    # back to a route that fails cleanly instead of the module failing to
    # import.
    @app.post("/api/upload")
    async def upload_files():
        return {"success": False, "error": "Server is missing the python-multipart dependency for uploads"}

@app.post("/api/delete")
async def delete_file(data: dict = Body(...)):
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

    # Close any live Yjs room(s) for this path (or nested under it, for a
    # directory delete) BEFORE touching disk. Otherwise a client that still
    # has the file open keeps its debounced save timer running and
    # resurrects the file on its next keystroke.
    await yjs_provider.close_rooms_under(path)

    try:
        if target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/rename")
async def rename_file(data: dict = Body(...)):
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
    
    # Check if destination already exists
    if dest.exists():
        return {"success": False, "error": "A file with that name already exists"}
    
    try:
        # Create destination directory if it doesn't exist
        dest.parent.mkdir(parents=True, exist_ok=True)
        source.rename(dest)
        result_path = str(dest.relative_to(BASE_DIR))
        # Rebind any live Yjs room(s) (or nested under it, for a directory
        # move) to the new path. Otherwise the old path's room keeps saving
        # to a location that no longer exists — and a fresh room opened at
        # the new path would start split-brained against it.
        await yjs_provider.rename_rooms_under(path, result_path)
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
    except Exception:
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
    except Exception:
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
    except Exception:
        return {"hierarchy": []}

def _materialize_hierarchy(hierarchy):
    """Create the content files a hierarchy describes, if they are missing.

    The structure editor used to write hierarchy.json alone, leaving chapters
    and pages with no file behind them -- the document then failed to compile
    with "file not found". Chapter folders are numbered by position and pages
    1..n inside them, matching what `noteworthy.py --print-inputs` scans for.

    Only ever creates: removing an entry leaves its file alone, so nobody
    loses writing by editing the outline.
    """
    created = []
    content_dir = BASE_DIR / "content"
    for ch_idx, chapter in enumerate(hierarchy):
        if not isinstance(chapter, dict):
            continue
        ch_dir = content_dir / str(ch_idx)
        try:
            ch_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.error(f"Could not create chapter directory {ch_dir}: {e}")
            continue
        for pg_idx, page in enumerate(chapter.get("pages", []) or []):
            page_file = ch_dir / f"{pg_idx + 1}.typ"
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


@app.post("/api/hierarchy")
def save_hierarchy(data: dict = Body(...)):
    """Save hierarchy.json and create any content files it introduces."""
    hierarchy = data.get("hierarchy", [])
    HIERARCHY_FILE.write_text(json.dumps(hierarchy, indent=2))
    created = _materialize_hierarchy(hierarchy)
    if created:
        log.info(f"Created content files for new hierarchy entries: {created}")
    return {"success": True, "created": created}

@app.get("/api/preface")
def get_preface():
    """Get preface.typ content."""
    try:
        return {"content": PREFACE_FILE.read_text()}
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
        except Exception:
            pass
        return items
    
    return {"root": BASE_DIR.name, "items": scan(BASE_DIR, BASE_DIR)}

# ============================================================
# BUILD API
# ============================================================

def _broadcast_build_event(payload: dict):
    """Push a build-progress message to all doc-socket clients.

    run_build (and the BuildManager callbacks it passes down) execute in
    FastAPI's sync threadpool, not the asyncio loop that owns the
    websockets, so the broadcast has to be handed off via
    run_coroutine_threadsafe rather than awaited directly.
    """
    if _main_loop is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(document_hub._broadcast(payload), _main_loop)
    except Exception as e:
        log.error(f"[Build] Failed to broadcast progress: {e}")


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

        # Real progress, driven by BuildManager's own callbacks (no fake
        # timer). `total` is learned from the "Generated N tasks" log line —
        # BuildManager doesn't expose the task count directly — and
        # `completed` is incremented once per successfully compiled task.
        # Pagination-correction passes can push `completed` past `total`;
        # the client clamps the percentage rather than trust it blindly.
        progress = {"completed": 0, "total": 0}
        task_count_re = re.compile(r"Generated (\d+) tasks")

        def on_log(message, ok):
            m = task_count_re.match(message)
            if m:
                progress["total"] = int(m.group(1))
            _broadcast_build_event({
                "type": "build_progress",
                "phase": "log",
                "message": message,
                "ok": bool(ok),
                "completed": progress["completed"],
                "total": progress["total"],
            })

        def on_progress():
            progress["completed"] += 1
            _broadcast_build_event({
                "type": "build_progress",
                "phase": "progress",
                "completed": progress["completed"],
                "total": progress["total"],
            })
            return True

        callbacks = {"on_log": on_log, "on_progress": on_progress}

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

            _broadcast_build_event({
                "type": "build_progress", "phase": "done",
                "completed": progress["completed"],
                "total": progress["total"] or progress["completed"],
            })
            return {"success": True, "output": f"Build complete! ({current_page_count-1} pages)"}
        else:
            _broadcast_build_event({"type": "build_progress", "phase": "error", "message": "Merge failed"})
            return {"success": False, "output": "Merge failed"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        _broadcast_build_event({"type": "build_progress", "phase": "error", "message": str(e)})
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
    await websocket.close()

@app.post("/api/watch")
def start_watch(data: dict = Body(...)):
    """Start watching a file for preview."""
    path = data.get("path")
    preview_manager.start_watch(path)
    return {"success": True}


# ============================================================
# TINYMIST PREVIEW API
# ============================================================

def _tinymist_status() -> dict:
    """Build the tinymist status block shared by /api/status and /api/tinymist/status."""
    running = preview_manager.full_preview_running
    return {
        "running": running,
        "url": preview_manager.get_full_preview_url() if running else None,
        "control_url": preview_manager.get_full_preview_control_url() if running else None,
        "target": preview_manager.full_preview_target,
    }


@app.post("/api/tinymist/start")
def start_tinymist_preview(data: dict = Body(default={})):
    """Start tinymist preview server for source/preview synchronization.

    Idempotent by default — a preview session is shared by every connected
    client, so if one is already running we just hand back its details
    instead of killing and retargeting it out from under whoever is using
    it. Pass `restart: true` to explicitly retarget/restart it.
    """
    file_path = data.get("path")
    restart = bool(data.get("restart"))

    if preview_manager.full_preview_running and not restart:
        status = _tinymist_status()
        status["success"] = True
        return status

    if restart:
        preview_manager.stop_full_preview()

    url = preview_manager.start_full_preview(file_path)
    if url:
        return {
            "success": True,
            "url": url,
            "control_url": preview_manager.get_full_preview_control_url(),
            "target": preview_manager.full_preview_target,
        }
    return {"success": False, "error": "Failed to start tinymist preview"}


@app.post("/api/tinymist/stop")
def stop_tinymist_preview():
    """Stop tinymist preview server."""
    preview_manager.stop_full_preview()
    return {"success": True}


@app.get("/api/tinymist/status")
def get_tinymist_status():
    """Get tinymist preview status."""
    return _tinymist_status()

# ============================================================
# MODULES API
# ============================================================

@app.get("/api/modules")
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
        log.error("typst binary not found")
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
        
        log.debug(f"typst stderr: {result.stderr}")
        log.debug(f"typst returncode: {result.returncode}")
        
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
        
        log.debug(f"Parsed diagnostics: {diagnostics}")
        return {"diagnostics": diagnostics}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# ============================================================
# STATUS API
# ============================================================

@app.get("/api/debug/yjs")
async def debug_yjs_state():
    """Debug endpoint to inspect Yjs rooms state."""
    from .yjs_provider import yjs_provider
    from pycrdt import Text
    
    status = {
        "yjs_rooms": []
    }
    
    for name, room in yjs_provider.rooms.items():
        try:
            text = room.ydoc.get("content", type=Text)
            content_len = len(text)
            content_preview = str(text)[:50] + "..." if content_len > 0 else ""
            
            room_info = {
                "name": name,
                "initialized": getattr(room, "_initialized", False),
                "content_length": content_len,
                "content_preview": content_preview,
                "file_exists": room._file_path.exists() if hasattr(room, "_file_path") else "Unknown"
            }
            status["yjs_rooms"].append(room_info)
        except Exception as e:
            status["yjs_rooms"].append({"name": name, "error": str(e)})
            
    return status

@app.get("/api/status")
def get_status():
    """Get system status."""
    return {
        "project": BASE_DIR.name,
        "path": str(BASE_DIR),
        "preview": preview_manager.get_status(),
        # Clients probe status.tinymist.{running,url} for preview discovery.
        "tinymist": _tinymist_status(),
    }

# ============================================================
# Mount Static Files (must be last!)
# ============================================================

if STATIC_DIR.exists():
    app.mount("/", SafeStaticFiles(directory=str(STATIC_DIR), html=True), name="static")
