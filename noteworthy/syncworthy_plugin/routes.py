"""Noteworthy's own HTTP routes: build, download, preview control, settings.

Same paths and payloads as the old GUI server, so the frontend and any scripts
keep working.  ``/api/check`` is the diagnostics seam in Syncworthy itself.
"""
import logging

from fastapi import APIRouter, Body
from fastapi.responses import FileResponse

from ..config import OUTPUT_FILE
from . import build, settings_routes

log = logging.getLogger("noteworthy.syncworthy_plugin")


def build_router(plugin) -> APIRouter:
    router = APIRouter()
    router.include_router(settings_routes.router)

    # ---- build ---------------------------------------------------------------
    @router.post("/api/build")
    def run_build(data: dict = Body(...)):
        """Execute build process."""
        return build.run_build(plugin.ctx, data)

    @router.get("/api/download/output.pdf")
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

    # ---- preview control ----------------------------------------------------------
    @router.post("/api/watch")
    def start_watch(data: dict = Body(...)):
        """Start watching a file for preview."""
        plugin.previewer.manager.start_watch(data.get("path"))
        return {"success": True}

    @router.post("/api/tinymist/start")
    def start_tinymist_preview(data: dict = Body(default={})):
        """Start tinymist preview server for source/preview synchronization.

        Idempotent by default — a preview session is shared by every connected
        client, so if one is already running we just hand back its details
        instead of killing and retargeting it out from under whoever is using
        it. Pass `restart: true` to explicitly retarget/restart it.
        """
        pv = plugin.previewer
        pm = pv.manager
        file_path = data.get("path")
        restart = bool(data.get("restart"))

        if pm.full_preview_running and not restart:
            status = pv.tinymist_status()
            status["success"] = True
            return status

        if restart:
            pm.stop_full_preview()

        url = pm.start_full_preview(file_path)
        if url:
            return {
                "success": True,
                "url": url,
                "control_url": pm.get_full_preview_control_url(),
                "target": pm.full_preview_target,
            }
        return {"success": False, "error": "Failed to start tinymist preview"}

    @router.post("/api/tinymist/stop")
    def stop_tinymist_preview():
        """Stop tinymist preview server."""
        plugin.previewer.manager.stop_full_preview()
        return {"success": True}

    @router.get("/api/tinymist/status")
    def get_tinymist_status():
        """Get tinymist preview status."""
        return plugin.previewer.tinymist_status()

    return router
