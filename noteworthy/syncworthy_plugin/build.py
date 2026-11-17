"""The PDF build, as a Syncworthy action.

The body is the old gui/server.py run_build; progress still goes out as
``build_progress`` messages on the doc socket, which the plugin's build.js shows.
"""
import json
import logging
import os
import re
import shutil

from ..config import BUILD_DIR, HIERARCHY_FILE, OUTPUT_FILE

log = logging.getLogger("noteworthy.syncworthy_plugin")


def run_build(ctx, data: dict) -> dict:
    """Execute build process.

    Runs in a worker thread (FastAPI's sync threadpool), not the asyncio loop
    that owns the websockets, so progress is handed to the loop with
    ctx.broadcast, which is thread-safe.
    """
    def _broadcast_build_event(payload: dict):
        try:
            ctx.broadcast(payload)
        except Exception as e:
            log.error(f"[Build] Failed to broadcast progress: {e}")

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
            # Now, and only now, is "which page did that land on" answerable:
            # turn the reference markers into real internal links.
            try:
                from ..core.xref import rewrite_links
                rewrite_links(OUTPUT_FILE)
            except Exception as e:
                log.error(f"Could not link cross-references: {e}")
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
