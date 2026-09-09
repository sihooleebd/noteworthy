"""
Live Preview Manager for Noteworthy GUI
Watches files and generates SVG previews via typst
"""
import subprocess
import logging
import threading
import time
import shutil
import os
from pathlib import Path

from ..config import BASE_DIR, RENDERER_FILE
log = logging.getLogger("noteworthy.gui")


class PreviewManager:
    """Manages live preview compilation and WebSocket updates."""
    
    def __init__(self):
        # Maps path -> {process, thread, ref_count, cache_dir}
        self.watchers = {}
        self.callbacks = []
        self.log_callbacks = []  # For error log broadcasting
        
        # Full preview state
        self.full_preview_process = None
        self.full_preview_thread = None
        self.full_preview_running = False
        self.full_preview_port = None  # Dynamic port for tinymist
        self.full_preview_control_port = None
        self.full_preview_target = None
        
        # Base cache directory
        self.base_cache_dir = BASE_DIR / "build" / ".preview_cache"
        if self.base_cache_dir.exists():
            try:
                shutil.rmtree(self.base_cache_dir)
            except Exception:
                pass
        self.base_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _find_available_port(self, start_port: int = 23625, max_attempts: int = 100):
        """Find an available port starting from start_port."""
        import socket
        for offset in range(max_attempts):
            port = start_port + offset
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                continue
        return None
    
    def _find_tinymist(self):
        """Find tinymist binary."""
        possible_paths = [
            os.path.expanduser("~/.cargo/bin/tinymist"),
            "/usr/local/bin/tinymist",
            "tinymist"
        ]
        for p in possible_paths:
            if shutil.which(p) or Path(p).exists():
                return p
        return "tinymist"
    
    def _find_typst(self):
        """Find typst binary."""
        possible_paths = [
            "/opt/homebrew/bin/typst",
            "/usr/local/bin/typst",
            os.path.expanduser("~/.cargo/bin/typst"),
            "typst"
        ]
        for p in possible_paths:
            if shutil.which(p) or Path(p).exists():
                return p
        return "typst"
    
    def start_watch(self, file_path: str):
        """Start watching a file for changes."""
        # Normalize path
        file_path = str(Path(file_path))
        
        if file_path in self.watchers:
            self.watchers[file_path]['ref_count'] += 1
            log.debug(f"[Preview] Incremented ref count for {file_path} to {self.watchers[file_path]['ref_count']}")
            return

        # Create unique cache dir for this file
        import hashlib
        path_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        cache_dir = self.base_cache_dir / path_hash
        
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        typst_bin = self._find_typst()
        log.info(f"[Preview] Starting watch for {file_path} using {typst_bin}")
        
        # Scan content directory
        content_dir = BASE_DIR / "content"
        chapter_folders = []
        page_folders = {}
        
        if content_dir.exists():
            ch_dirs = sorted(
                [d for d in content_dir.iterdir() if d.is_dir() and d.name.replace('.', '', 1).lstrip('-').isdigit()],
                key=lambda d: float(d.name) if d.name.replace('.', '', 1).lstrip('-').isdigit() else 999
            )
            for ch_dir in ch_dirs:
                chapter_folders.append(ch_dir.name)
                pg_files = sorted(
                    [f.stem for f in ch_dir.glob("*.typ") if f.stem.replace('.', '', 1).lstrip('-').isdigit()],
                    key=lambda s: float(s) if s.replace('.', '', 1).lstrip('-').isdigit() else 999
                )
                # Keyed by folder NAME, matching utils.scan_content and the
                # lookup in parser.typ.  Keying by index only agreed with the
                # folder name while chapters were 0,1,2,... -- with a gap
                # (content/0 and content/4) the lookup missed and every page
                # fell back to a 0-based range, renumbering the whole chapter.
                page_folders[ch_dir.name] = pg_files
        
        # Parse target
        target = None
        if file_path.startswith("content/"):
            parts = file_path.replace("content/", "").replace(".typ", "").split("/")
            if len(parts) == 2:
                ch_name = parts[0]
                pg_name = parts[1]
                if ch_name in chapter_folders:
                    ch_idx = chapter_folders.index(ch_name)
                    pg_files = page_folders.get(str(ch_idx), [])
                    if pg_name in pg_files:
                        pg_idx = pg_files.index(pg_name)
                        target = f"{ch_idx}/{pg_idx}"
        
        if target and RENDERER_FILE.exists():
            watch_file = RENDERER_FILE
        else:
            watch_file = BASE_DIR / file_path
            if not watch_file.exists():
                log.warning(f"[Preview] File not found: {watch_file}")
                return
        
        cache_pattern = cache_dir / "page-{n}.svg"
        
        import json
        cmd = [
            typst_bin, "watch", str(watch_file), str(cache_pattern),
            "--root", str(BASE_DIR),
            "--input", f"chapter-folders={json.dumps(chapter_folders)}",
            "--input", f"page-folders={json.dumps(page_folders)}"
        ]
        
        if target:
            cmd.extend(["--input", f"target={target}"])
        
        log.info(f"[Preview] Running: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            watcher = {
                'process': process,
                'ref_count': 1,
                'cache_dir': cache_dir,
                'running': True,
                'preview_cache': {},
                'page_mapping': []
            }
            
            # Start monitoring threads
            watcher['monitor_thread'] = threading.Thread(
                target=self._monitor_loop, 
                args=(file_path, watcher),
                daemon=True
            )
            watcher['output_thread'] = threading.Thread(
                target=self._read_output, 
                args=(process, watcher),
                daemon=True
            )
            
            watcher['monitor_thread'].start()
            watcher['output_thread'].start()
            
            self.watchers[file_path] = watcher
            log.info(f"[Preview] Started watching {file_path}")
            
        except Exception as e:
            log.error(f"[Preview] Failed to start typst: {e}")
    
    def _read_output(self, process, watcher):
        """Read and log typst output."""
        try:
            for line in iter(process.stdout.readline, ''):
                if not watcher['running']:
                    break
                if line:
                    log.debug(f"[Typst] {line.rstrip()}")
        except Exception:
            pass
    
    def stop_watch(self, file_path: str):
        """Stop watching a file."""
        file_path = str(Path(file_path))
        if file_path not in self.watchers:
            return
            
        watcher = self.watchers[file_path]
        watcher['ref_count'] -= 1
        log.debug(f"[Preview] Decremented ref count for {file_path} to {watcher['ref_count']}")
        
        if watcher['ref_count'] <= 0:
            log.info(f"[Preview] Stopping watch for {file_path}")
            watcher['running'] = False
            if watcher['process']:
                try:
                    watcher['process'].terminate()
                except Exception:
                    pass
            try:
                shutil.rmtree(watcher['cache_dir'])
            except Exception:
                pass
            del self.watchers[file_path]
    
    def add_callback(self, cb):
        """Register callback for updates."""
        self.callbacks.append(cb)
    
    def cleanup_old_watchers(self, keep_paths: list = None, max_watchers: int = 3):
        """
        Cleanup old watchers, keeping only the most recent ones.
        This implements LRU-style caching to avoid cold starts on file switch.
        """
        keep_paths = keep_paths or []
        current_count = len(self.watchers)
        
        if current_count <= max_watchers:
            return
        
        # Find watchers to remove (those not in keep_paths)
        to_remove = []
        for path in self.watchers:
            if path not in keep_paths:
                to_remove.append(path)
        
        # Remove oldest watchers until we're at max_watchers
        while len(self.watchers) > max_watchers and to_remove:
            oldest_path = to_remove.pop(0)
            log.info(f"[Preview] Evicting old watcher: {oldest_path}")
            self._force_stop_watch(oldest_path)
    
    def _force_stop_watch(self, file_path: str):
        """Force stop a watcher without ref count check."""
        if file_path not in self.watchers:
            return
        
        watcher = self.watchers[file_path]
        watcher['running'] = False
        if watcher.get('process'):
            try:
                watcher['process'].terminate()
            except Exception:
                pass
        try:
            shutil.rmtree(watcher['cache_dir'])
        except Exception:
            pass
        del self.watchers[file_path]
    
    def _monitor_loop(self, file_path, watcher):
        """Monitor cache directory for SVG updates."""
        last_mtimes = {}
        
        while watcher['running']:
            if not watcher['process']:
                time.sleep(0.1)
                continue
            
            # Check if process died
            if watcher['process'].poll() is not None:
                log.info(f"[Preview] Typst process exited with code: {watcher['process'].returncode}")
                watcher['running'] = False
                # Don't delete from watchers yet, let stop_watch handle cleanup
                break
            
            # Scan for new/updated SVGs
            try:
                svgs = list(watcher['cache_dir'].glob("page-*.svg"))
                current_pages = []
                updates = []
                
                for svg in svgs:
                    try:
                        num = int(svg.stem.split('-')[-1])
                        current_pages.append(num)
                        
                        mtime = svg.stat().st_mtime
                        if mtime != last_mtimes.get(svg.name):
                            # Read with retry
                            content = None
                            for _ in range(5):
                                if svg.stat().st_size > 0:
                                    try:
                                        content = svg.read_text(encoding='utf-8')
                                        break
                                    except Exception:
                                        pass
                                time.sleep(0.005)
                            
                            if content:
                                watcher['preview_cache'][num] = content.encode('utf-8')
                                last_mtimes[svg.name] = mtime
                                updates.append({'page': num, 'svg': content})
                    except Exception:
                        pass
                
                watcher['page_mapping'] = sorted(current_pages)
                
                if updates:
                    log.debug(f"[Debug] Found {len(updates)} updates for {file_path}")
                    for cb in self.callbacks:
                        try:
                            # Pass file_path so hub knows who to send it to
                            cb(updates, file_path)
                        except Exception as e:
                            log.error(f"[Preview] Callback error: {e}")
            except Exception as e:
                log.error(f"[Debug] Monitor loop error: {e}")

            # 150ms keeps updates feeling live while avoiding a hot
            # glob/stat loop per watched file (was 20ms).
            time.sleep(0.15)
    
    def get_status(self, file_path: str = None):
        """Get status for a specific file."""
        file_path = str(Path(file_path)) if file_path else None
        if file_path and file_path in self.watchers:
            watcher = self.watchers[file_path]
            return {
                "running": watcher['running'],
                "pages": watcher['page_mapping']
            }
        return {"running": False, "pages": []}
    
    def get_image(self, file_path: str, page_num: int):
        """Get cached image for a page."""
        file_path = str(Path(file_path))
        if file_path in self.watchers:
            return self.watchers[file_path]['preview_cache'].get(int(page_num))
        return None
    
    # ============================================================
    # Full Document Preview (tinymist)
    # ============================================================
    
    def add_log_callback(self, cb):
        """Register callback for log messages (for broadcasting to clients)."""
        self.log_callbacks.append(cb)
    
    def _broadcast_log(self, level: str, message: str, source_path: str = None):
        """Broadcast a log message to all registered callbacks."""
        for cb in self.log_callbacks:
            try:
                cb(level, message, source_path)
            except Exception as e:
                log.error(f"[Preview] Log callback error: {e}")
    
    def start_full_preview(self, file_path: str = None):
        """Start the document preview using tinymist with optional target."""
        file_path = str(Path(file_path)) if file_path else None

        if self.full_preview_running:
            log.info("[Preview] Full preview already running")
            return self.get_full_preview_url()
        
        tinymist_bin = self._find_tinymist()
        parser_file = BASE_DIR / "templates" / "core" / "parser.typ"
        
        if not parser_file.exists():
            log.warning(f"[Preview] Parser file not found: {parser_file}")
            self._broadcast_log("error", f"Parser file not found: {parser_file}", file_path)
            return None
        
        # Build content info for inputs
        import json
        content_dir = BASE_DIR / "content"
        chapter_folders = []
        page_folders = {}
        
        if content_dir.exists():
            ch_dirs = sorted(
                [d for d in content_dir.iterdir() if d.is_dir() and d.name.replace('.', '', 1).lstrip('-').isdigit()],
                key=lambda d: float(d.name) if d.name.replace('.', '', 1).lstrip('-').isdigit() else 999
            )
            for ch_dir in ch_dirs:
                chapter_folders.append(ch_dir.name)
                pg_files = sorted(
                    [f.stem for f in ch_dir.glob("*.typ") if f.stem.replace('.', '', 1).lstrip('-').isdigit()],
                    key=lambda s: float(s) if s.replace('.', '', 1).lstrip('-').isdigit() else 999
                )
                # Keyed by folder NAME, matching utils.scan_content and the
                # lookup in parser.typ.  Keying by index only agreed with the
                # folder name while chapters were 0,1,2,... -- with a gap
                # (content/0 and content/4) the lookup missed and every page
                # fell back to a 0-based range, renumbering the whole chapter.
                page_folders[ch_dir.name] = pg_files
        
        # Parse target from file_path (e.g., "content/2/5.typ" -> "2/4")
        target = None
        if file_path and file_path.startswith("content/"):
            parts = file_path.replace("content/", "").replace(".typ", "").split("/")
            if len(parts) == 2:
                ch_name = parts[0]
                pg_name = parts[1]
                if ch_name in chapter_folders:
                    ch_idx = chapter_folders.index(ch_name)
                    pg_files = page_folders.get(str(ch_idx), [])
                    if pg_name in pg_files:
                        pg_idx = pg_files.index(pg_name)
                        target = f"{ch_idx}/{pg_idx}"
        
        cmd = [
            tinymist_bin, "preview", str(parser_file),
            "--root", str(BASE_DIR),
            "--input", f"chapter-folders={json.dumps(chapter_folders)}",
            "--input", f"page-folders={json.dumps(page_folders)}",
            "--no-open",
        ]
        
        # Find an available port for this instance (data plane and control plane)
        data_port = self._find_available_port(start_port=23625)
        if data_port:
            self.full_preview_port = data_port
            control_port = self._find_available_port(start_port=data_port + 1)
            self.full_preview_control_port = control_port
            cmd.extend(["--data-plane-host", f"127.0.0.1:{data_port}"])
            if control_port:
                cmd.extend(["--control-plane-host", f"127.0.0.1:{control_port}"])
            log.info(f"[Preview] Using ports {data_port} (data) / {control_port} (control) for tinymist")
        else:
            log.warning("[Preview] Warning: Could not find available port, using default")
            self.full_preview_port = 23625  # Default tinymist port
            self.full_preview_control_port = None
        
        # Add target if we have one
        if target:
            cmd.extend(["--input", f"target={target}"])
        
        log.info(f"[Preview] Starting full preview: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr into stdout for logging
                text=True,
                bufsize=1,
                cwd=str(BASE_DIR)
            )
            
            self.full_preview_process = process
            self.full_preview_running = True
            self.full_preview_target = file_path
            self._broadcast_log(
                "info",
                f"Starting Tinymist preview for {file_path or 'parser.typ'}",
                file_path
            )
            
            # Start thread to read output and broadcast logs
            self.full_preview_thread = threading.Thread(
                target=self._read_full_preview_output,
                args=(process,),
                daemon=True
            )
            self.full_preview_thread.start()
            
            log.info(f"[Preview] Full preview started, PID: {process.pid}")
            self._broadcast_log("info", f"Tinymist preview started on {self.get_full_preview_url()}", file_path)
            return self.get_full_preview_url()
            
        except Exception as e:
            log.error(f"[Preview] Failed to start tinymist: {e}")
            self._broadcast_log("error", f"Failed to start tinymist: {e}", file_path)
            self.full_preview_running = False
            self.full_preview_process = None
            self.full_preview_thread = None
            self.full_preview_port = None
            self.full_preview_control_port = None
            self.full_preview_target = None
            return None
    
    def _read_full_preview_output(self, process):
        """Read and broadcast tinymist output."""
        target_path = self.full_preview_target
        try:
            for line in iter(process.stdout.readline, ''):
                if not self.full_preview_running:
                    break
                if line:
                    line = line.rstrip()
                    log.debug(f"[Tinymist] {line}")
                    lower = line.lower()
                    if "error" in lower:
                        self._broadcast_log("error", line, target_path)
                    elif "warning" in lower:
                        self._broadcast_log("warning", line, target_path)
                    else:
                        self._broadcast_log("info", line, target_path)
        except Exception as e:
            log.error(f"[Preview] Error reading tinymist output: {e}")
            self._broadcast_log("error", f"Tinymist output reader failed: {e}", target_path)
        finally:
            return_code = process.poll()
            if self.full_preview_process is process and self.full_preview_running:
                message = f"Tinymist preview exited with code {return_code}"
                level = "info" if return_code in (0, None) else "error"
                log.warning(f"[Preview] {message}")
                self._broadcast_log(level, message, target_path)
                self.full_preview_running = False
                self.full_preview_process = None
                self.full_preview_thread = None
                self.full_preview_port = None
                self.full_preview_control_port = None
                self.full_preview_target = None
    
    def stop_full_preview(self):
        """Stop the full document preview."""
        if not self.full_preview_running and not self.full_preview_process:
            return
        
        log.info("[Preview] Stopping full preview")
        target_path = self.full_preview_target
        self._broadcast_log("info", "Stopping Tinymist preview", target_path)
        self.full_preview_running = False
        
        if self.full_preview_process:
            try:
                self.full_preview_process.terminate()
                self.full_preview_process.wait(timeout=3)
            except Exception:
                try:
                    self.full_preview_process.kill()
                except Exception:
                    pass
            self.full_preview_process = None
        
        self.full_preview_thread = None
        self.full_preview_port = None
        self.full_preview_control_port = None
        self.full_preview_target = None
        self._broadcast_log("info", "Tinymist preview stopped", target_path)
    
    def get_full_preview_url(self):
        """Get the URL for the full preview using the dynamically assigned port."""
        port = self.full_preview_port or 23625  # Fall back to default if not set
        return f"http://127.0.0.1:{port}"

    def get_full_preview_control_url(self):
        """Get the control-plane websocket URL for the full preview."""
        if not self.full_preview_control_port:
            return None
        return f"ws://127.0.0.1:{self.full_preview_control_port}"
