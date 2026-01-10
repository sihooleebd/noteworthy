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

from ..config import (
    BASE_DIR, BUILD_DIR, OUTPUT_FILE, RENDERER_FILE,
    METADATA_FILE, CONSTANTS_FILE, HIERARCHY_FILE,
    PREFACE_FILE, SNIPPETS_FILE, SCHEMES_DIR,
    MODULES_CONFIG_FILE, INDEXIGNORE_FILE
)
from .preview import PreviewManager
from .crdt_manager import CRDTManager, init_crdt_manager, get_crdt_manager
import uuid

app = FastAPI(title="Noteworthy GUI")
preview_manager = PreviewManager()

# Initialize CRDT Manager (low save_delay for responsive tinymist preview)
CRDT_SAVE_DELAY = float(os.environ.get("CRDT_SAVE_DELAY", "0.15"))
crdt_manager = init_crdt_manager(BASE_DIR, save_delay=CRDT_SAVE_DELAY)

# Collaboration Manager (legacy web collab)
from .collaboration import collab_manager

# User colors for Emacs clients
EMACS_USER_COLORS = [
    "#FF6B6B", "#4ECDC4", "#FFE66D", "#95E1D3",
    "#F38181", "#AA96DA", "#FCBAD3", "#A8D8EA"
]
emacs_color_index = 0

# Track connected Emacs clients
emacs_clients: dict = {}  # user_id -> {"websocket": ws, "name": str, "color": str, "file": str}

@app.websocket("/ws/collab")
async def collab_endpoint(websocket: WebSocket):
    user_name = websocket.query_params.get("name", "Anonymous")
    
    await websocket.accept()
    
    try:
        user = await collab_manager.connect(websocket, user_name)
        
        # Send initial global state
        await websocket.send_text(json.dumps({
            "type": "joined",
            "userId": user.id,
            "color": user.color,
            "users": collab_manager.get_global_users()
        }))
        
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg["type"] == "file_focus":
                # User switched file
                await collab_manager.set_active_file(user.id, msg.get("path"))
            
            elif msg["type"] == "cursor":
                await collab_manager.update_cursor(
                    user.id, 
                    msg.get("line", 1), 
                    msg.get("column", 1),
                    msg.get("selectionStart"),
                    msg.get("selectionEnd")
                )
            elif msg["type"] == "edit":
                # Apply edit to CRDT and broadcast to all clients
                changes = msg.get("changes", [])
                file_path = user.active_file
                
                if file_path and changes:
                    print(f"[Web] RECV edit from {user.name}: file={file_path}, changes={changes}")
                    
                    # Convert web changes to CRDT ops and apply
                    # Web format: {from: {line, ch}, to: {line, ch}, text: [...], removed: [...]}
                    for change in changes:
                        try:
                            from_offset = change.get("fromOffset")  # Character offset
                            to_offset = change.get("toOffset")      # Character offset
                            text = change.get("text", [""])
                            
                            if isinstance(text, list):
                                text = "\n".join(text)
                            
                            if from_offset is not None:
                                ops = []
                                if from_offset > 0:
                                    ops.append({"retain": from_offset})
                                if to_offset and to_offset > from_offset:
                                    ops.append({"delete": to_offset - from_offset})
                                if text:
                                    ops.append({"insert": text})
                                
                                if ops:
                                    success = crdt_manager.apply_delta(file_path, ops, source_user=user.id)
                                    print(f"[Web] apply_delta result: {success}")
                        except Exception as e:
                            print(f"[Web] Error converting change: {e}")
                    
                    # Broadcast edit to web clients (original behavior)
                    await collab_manager.broadcast_edit(user.id, changes)
                    
                    # Broadcast full content to Emacs clients
                    content = crdt_manager.get_content(file_path)
                    version = crdt_manager.get_version(file_path)
                    if content is not None:
                        await broadcast_to_emacs_file(file_path, {
                            "type": "sync",
                            "file": file_path,
                            "content": content,
                            "version": version,
                            "source": "web",
                            "userId": user.id
                        })
            elif msg["type"] == "identity":
                await collab_manager.update_user(
                    user.id, msg.get("name", "Anonymous")
                )
            elif msg["type"] == "chat":
                await collab_manager.broadcast_global(
                    {
                        "type": "chat",
                        "userId": user.id,
                        "name": user.name,
                        "color": user.color,
                        "text": msg.get("text", ""),
                        "timestamp": msg.get("timestamp", 0)
                    }
                )
                
    except WebSocketDisconnect:
        await collab_manager.disconnect(user.id)


# ============================================================
# EMACS CRDT WebSocket - Real-time collaboration for Emacs
# ============================================================

# Tinymist preview process
tinymist_process: subprocess.Popen = None
TINYMIST_PORT = int(os.environ.get("TINYMIST_PORT", "23625"))

@app.on_event("startup")
async def startup_crdt():
    """Initialize CRDT manager with event loop."""
    loop = asyncio.get_running_loop()
    crdt_manager.set_event_loop(loop)
    print("[Server] CRDT manager initialized")

@app.on_event("startup")
async def startup_tinymist_preview():
    """Start tinymist preview server for Emacs xwidget integration."""
    global tinymist_process
    
    # Find main typst file
    master_candidates = [
        BASE_DIR / "templates" / "core" / "parser.typ",
        BASE_DIR / "templates" / "parser.typ",
        BASE_DIR / "main.typ",
    ]
    
    master_file = None
    for candidate in master_candidates:
        if candidate.exists():
            master_file = candidate
            break
    
    if not master_file:
        # Try to find any .typ file
        typ_files = list(BASE_DIR.glob("**/*.typ"))
        if typ_files:
            master_file = typ_files[0]
    
    if not master_file:
        print("[Tinymist] No .typ file found, preview disabled")
        return
    
    # Check if tinymist is available
    tinymist_bin = shutil.which("tinymist")
    if not tinymist_bin:
        print("[Tinymist] tinymist not found in PATH, preview disabled")
        return
    
    try:
        cmd = [
            tinymist_bin, "preview",
            str(master_file),
            "--root", str(BASE_DIR),
            "--no-open",  # Don't open browser
        ]
        print(f"[Tinymist] Starting: {' '.join(cmd)}")
        print(f"[Tinymist] Preview will be at http://127.0.0.1:{TINYMIST_PORT}")
        
        tinymist_process = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        
        # Give it a moment to start
        await asyncio.sleep(1)
        
        if tinymist_process.poll() is None:
            print(f"[Tinymist] Preview running on http://127.0.0.1:{TINYMIST_PORT}")
        else:
            print(f"[Tinymist] Failed to start (exit code: {tinymist_process.returncode})")
            tinymist_process = None
    except Exception as e:
        print(f"[Tinymist] Error starting preview: {e}")
        tinymist_process = None

@app.on_event("shutdown")
async def shutdown_tinymist():
    """Stop tinymist preview server."""
    global tinymist_process
    if tinymist_process:
        print("[Tinymist] Stopping preview server...")
        tinymist_process.terminate()
        try:
            tinymist_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            tinymist_process.kill()
        tinymist_process = None


@app.websocket("/ws/emacs")
async def emacs_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Emacs clients.
    
    Uses simple JSON protocol for CRDT synchronization.
    All edits go through CRDT - no direct file saves from Emacs.
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
    
    # Send welcome message
    await websocket.send_json({
        "type": "welcome",
        "userId": user_id,
        "color": user_color
    })
    
    # Log helper
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
                # Join a file's CRDT session
                file_path = data.get("file", "")
                
                # Leave previous file if any
                if current_file and observer_callback:
                    crdt_manager.remove_observer(current_file, observer_callback)
                
                current_file = file_path
                emacs_clients[user_id]["file"] = file_path
                
                # Get or create document
                doc_state = crdt_manager.get_or_create(file_path)
                content = crdt_manager.get_content(file_path)
                version = crdt_manager.get_version(file_path)
                
                # Create observer for this client
                async def on_crdt_change(path: str, delta: list, ver: int):
                    """Handle CRDT changes and forward to this Emacs client."""
                    # Check for special "saved" notification
                    if delta and len(delta) == 1 and delta[0].get("saved"):
                        try:
                            await websocket.send_json({
                                "type": "saved",
                                "file": path,
                                "version": ver
                            })
                        except:
                            pass
                        return
                    
                    # Forward delta to client
                    try:
                        await websocket.send_json({
                            "type": "delta",
                            "file": path,
                            "ops": delta,
                            "version": ver,
                            "userId": "server"  # Could track source user
                        })
                    except:
                        pass
                
                # Wrap async callback for sync observer
                def observer_wrapper(path, delta, ver):
                    asyncio.create_task(on_crdt_change(path, delta, ver))
                
                observer_callback = observer_wrapper
                crdt_manager.add_observer(file_path, observer_callback)
                
                # Send current content
                await websocket.send_json({
                    "type": "sync",
                    "file": file_path,
                    "content": content,
                    "version": version
                })
                
                await send_log("info", f"Joined: {file_path}")
                
                # Notify other Emacs clients
                await broadcast_to_emacs_file(file_path, {
                    "type": "users",
                    "file": file_path,
                    "users": get_emacs_users_in_file(file_path)
                }, exclude=user_id)
            
            elif msg_type == "delta":
                # Apply client's delta to CRDT
                file_from_msg = data.get("file")
                ops = data.get("ops", [])
                target_file = file_from_msg or current_file
                
                print(f"[Emacs] RECV delta from {user_name}: file={target_file}, ops={ops}")
                
                if not target_file:
                    print(f"[Emacs] ERROR: No target file for delta! current_file={current_file}, msg_file={file_from_msg}")
                    await send_log("error", "No file specified for delta")
                    continue
                
                if ops:
                    success = crdt_manager.apply_delta(target_file, ops, source_user=user_id)
                    print(f"[Emacs] apply_delta result: {success}")
                    if success:
                        # Broadcast to other Emacs clients in same file
                        await broadcast_to_emacs_file(target_file, {
                            "type": "delta",
                            "file": target_file,
                            "ops": ops,
                            "userId": user_id,
                            "userName": user_name
                        }, exclude=user_id)
                        
                        # Also broadcast to web clients (they need full content refresh)
                        content = crdt_manager.get_content(target_file)
                        await broadcast_to_web_file(target_file, {
                            "type": "sync",
                            "file": target_file,
                            "content": content,
                            "source": "emacs",
                            "userId": user_id
                        })
                    else:
                        await send_log("error", f"Failed to apply delta to {target_file}")
            
            elif msg_type == "cursor":
                # Broadcast cursor position to other clients in same file
                if current_file:
                    await broadcast_to_emacs_file(current_file, {
                        "type": "cursor",
                        "file": current_file,
                        "userId": user_id,
                        "name": user_name,
                        "color": user_color,
                        "line": data.get("line", 1),
                        "col": data.get("col", 1)
                    }, exclude=user_id)
            
            elif msg_type == "leave":
                # Leave current file
                if current_file and observer_callback:
                    crdt_manager.remove_observer(current_file, observer_callback)
                    await send_log("info", f"Left: {current_file}")
                    
                    # Notify others
                    await broadcast_to_emacs_file(current_file, {
                        "type": "users",
                        "file": current_file,
                        "users": get_emacs_users_in_file(current_file)
                    }, exclude=user_id)
                    
                current_file = None
                emacs_clients[user_id]["file"] = None
                observer_callback = None
            
            elif msg_type == "identity":
                # Update user name
                new_name = data.get("name", user_name)
                user_name = new_name
                emacs_clients[user_id]["name"] = new_name
                await send_log("info", f"Identity updated: {new_name}")
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[Emacs] Error for {user_id}: {e}")
    finally:
        # Cleanup
        if current_file and observer_callback:
            crdt_manager.remove_observer(current_file, observer_callback)
        
        if user_id in emacs_clients:
            file_path = emacs_clients[user_id].get("file")
            del emacs_clients[user_id]
            
            # Notify others if was in a file
            if file_path:
                await broadcast_to_emacs_file(file_path, {
                    "type": "users",
                    "file": file_path,
                    "users": get_emacs_users_in_file(file_path)
                })
        
        print(f"[Emacs] Client disconnected: {user_name} ({user_id})")


async def broadcast_to_emacs_file(file_path: str, message: dict, exclude: str = None):
    """Broadcast message to all Emacs clients editing a specific file."""
    msg_json = json.dumps(message)
    for uid, client in list(emacs_clients.items()):
        if uid == exclude:
            continue
        if client.get("file") == file_path:
            try:
                await client["websocket"].send_text(msg_json)
            except:
                pass


async def broadcast_to_web_file(file_path: str, message: dict, exclude: str = None):
    """Broadcast message to all web clients editing a specific file."""
    msg_json = json.dumps(message)
    for user_id, user in collab_manager.users.items():
        if user_id == exclude:
            continue
        if user.active_file == file_path:
            try:
                await user.websocket.send_text(msg_json)
            except:
                pass


async def broadcast_to_all_file(file_path: str, message: dict, exclude: str = None, exclude_type: str = None):
    """Broadcast to both Emacs and web clients on a file."""
    if exclude_type != "emacs":
        await broadcast_to_emacs_file(file_path, message, exclude)
    if exclude_type != "web":
        await broadcast_to_web_file(file_path, message, exclude)


def get_emacs_users_in_file(file_path: str) -> list:
    """Get list of Emacs users currently in a file."""
    users = []
    for uid, client in emacs_clients.items():
        if client.get("file") == file_path:
            users.append({
                "id": uid,
                "name": client["name"],
                "color": client["color"]
            })
    return users


# Static files
STATIC_DIR = Path(__file__).parent / "static"

# ============================================================
# FILE API - Generic file read/write
# ============================================================

@app.get("/api/file")
def get_file(path: str):
    """Read a file relative to project root."""
    target = BASE_DIR / path
    if target.exists() and target.is_file():
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
    return {"success": True}

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

# ============================================================
# PREVIEW WebSocket
# ============================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    
    def on_update(updates):
        loop.call_soon_threadsafe(queue.put_nowait, updates)
    
    try:
        preview_manager.add_callback(on_update)
        
        # Send initial state
        status = preview_manager.get_status()
        if status['pages']:
            initial = []
            for p in status['pages']:
                content = preview_manager.get_image(p)
                if content:
                    initial.append({'page': p, 'svg': content.decode('utf-8')})
            if initial:
                await websocket.send_json({"type": "init", "updates": initial})
        
        while True:
            updates = await queue.get()
            await websocket.send_json({"type": "update", "updates": updates})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS Error: {e}")

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
        "tinymist": {
            "running": tinymist_process is not None and tinymist_process.poll() is None,
            "port": TINYMIST_PORT,
            "url": f"http://127.0.0.1:{TINYMIST_PORT}" if tinymist_process else None
        }
    }

# ============================================================
# Mount Static Files (must be last!)
# ============================================================

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
