"""Noteworthy's previewer for Syncworthy: ``typst watch`` SVG pages, and tinymist.

PreviewManager (preview.py) does the work on its own threads; this adapter
connects it to the hub: opening or leaving a ``.typ`` file starts or stops a
watch, and what the watch produces is pushed to the clients that have the file
open as ``{"type": "preview", "updates": [...]}`` -- the message the plugin's
preview.js draws.
"""
import asyncio
import logging

from .preview import PreviewManager

log = logging.getLogger("noteworthy.syncworthy_plugin")


class NoteworthyPreviewer:
    extensions = (".typ",)
    placeholder = "Select a .typ file"
    placeholder_selected = "Select a .typ file to view preview"

    def __init__(self):
        self.manager: PreviewManager | None = None
        self.ctx = None

    # ---- Previewer protocol ------------------------------------------------
    def attach(self, ctx) -> None:
        self.ctx = ctx
        self.manager = PreviewManager()
        self.manager.stop_full_preview()
        self.manager.add_callback(self._on_update)
        self.manager.add_log_callback(self._on_log)

    def handles(self, path: str) -> bool:
        return bool(path) and path.endswith(".typ")

    def start(self, path: str) -> None:
        self.manager.start_watch(path)

    def stop(self, path: str) -> None:
        self.manager.stop_watch(path)

    async def initial_messages(self, path: str) -> list[dict]:
        """The cached pages, for the one user who just opened PATH.

        A fresh watch has no pages for a moment, so poll briefly (20 x 150ms)
        for the first compile.
        """
        for _ in range(20):
            await asyncio.sleep(0.15)
            status = self.manager.get_status(path)
            if status["pages"]:
                updates = []
                for page in status["pages"]:
                    svg_bytes = self.manager.get_image(path, page)
                    if svg_bytes:
                        updates.append({"page": page, "svg": svg_bytes.decode("utf-8")})
                if updates:
                    return [{"type": "preview", "updates": updates}]
        return []

    def status(self) -> dict:
        """Merged into /api/status; clients probe status.tinymist.{running,url}."""
        return {"preview": self.manager.get_status(), "tinymist": self.tinymist_status()}

    def shutdown(self) -> None:
        if self.manager:
            self.manager.stop_full_preview()

    # ---- tinymist ------------------------------------------------------------
    def tinymist_status(self) -> dict:
        """The tinymist status block shared by /api/status and /api/tinymist/status."""
        pm = self.manager
        running = pm.full_preview_running
        return {
            "running": running,
            "url": pm.get_full_preview_url() if running else None,
            "control_url": pm.get_full_preview_control_url() if running else None,
            "target": pm.full_preview_target,
        }

    # ---- from the manager's threads to the clients ----------------------------
    def _on_update(self, updates, source_path):
        self.ctx.broadcast_to_file(source_path, {"type": "preview", "updates": updates})

    def _on_log(self, level, message, source_path=None):
        payload = {"type": "preview_log", "level": level, "message": message, "file": source_path}
        if source_path:
            self.ctx.broadcast_to_file(source_path, payload)
        else:
            self.ctx.broadcast(payload)
