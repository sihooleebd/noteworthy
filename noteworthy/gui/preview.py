"""
Live Preview Manager for Noteworthy GUI
Watches files and generates SVG previews via typst
"""
import subprocess
import threading
import time
import shutil
import os
from pathlib import Path

from ..config import BASE_DIR, RENDERER_FILE


class PreviewManager:
    """Manages live preview compilation and WebSocket updates."""
    
    def __init__(self):
        # Maps path -> {process, thread, ref_count, cache_dir}
        self.watchers = {}
        self.callbacks = []
        
        # Base cache directory
        self.base_cache_dir = BASE_DIR / "build" / ".preview_cache"
        if self.base_cache_dir.exists():
            try:
                shutil.rmtree(self.base_cache_dir)
            except:
                pass
        self.base_cache_dir.mkdir(parents=True, exist_ok=True)
    
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
            print(f"[Preview] Incremented ref count for {file_path} to {self.watchers[file_path]['ref_count']}")
            return

        # Create unique cache dir for this file
        import hashlib
        path_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        cache_dir = self.base_cache_dir / path_hash
        
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        typst_bin = self._find_typst()
        print(f"[Preview] Starting watch for {file_path} using {typst_bin}")
        
        # Scan content directory
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
                print(f"[Preview] File not found: {watch_file}")
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
        
        print(f"[Preview] Running: {' '.join(cmd)}")
        
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
            print(f"[Preview] Started watching {file_path}")
            
        except Exception as e:
            print(f"[Preview] Failed to start typst: {e}")
    
    def _read_output(self, process, watcher):
        """Read and log typst output."""
        try:
            for line in iter(process.stdout.readline, ''):
                if not watcher['running']:
                    break
                if line:
                    print(f"[Typst] {line.rstrip()}")
        except:
            pass
    
    def stop_watch(self, file_path: str):
        """Stop watching a file."""
        file_path = str(Path(file_path))
        if file_path not in self.watchers:
            return
            
        watcher = self.watchers[file_path]
        watcher['ref_count'] -= 1
        print(f"[Preview] Decremented ref count for {file_path} to {watcher['ref_count']}")
        
        if watcher['ref_count'] <= 0:
            print(f"[Preview] Stopping watch for {file_path}")
            watcher['running'] = False
            if watcher['process']:
                try:
                    watcher['process'].terminate()
                except:
                    pass
            try:
                shutil.rmtree(watcher['cache_dir'])
            except:
                pass
            del self.watchers[file_path]
    
    def add_callback(self, cb):
        """Register callback for updates."""
        self.callbacks.append(cb)
    
    def _monitor_loop(self, file_path, watcher):
        """Monitor cache directory for SVG updates."""
        last_mtimes = {}
        
        while watcher['running']:
            if not watcher['process']:
                time.sleep(0.1)
                continue
            
            # Check if process died
            if watcher['process'].poll() is not None:
                print(f"[Preview] Typst process exited with code: {watcher['process'].returncode}")
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
                                    except:
                                        pass
                                time.sleep(0.005)
                            
                            if content:
                                watcher['preview_cache'][num] = content.encode('utf-8')
                                last_mtimes[svg.name] = mtime
                                updates.append({'page': num, 'svg': content})
                    except:
                        pass
                
                watcher['page_mapping'] = sorted(current_pages)
                
                if updates:
                    for cb in self.callbacks:
                        try:
                            # Pass file_path so hub knows who to send it to
                            cb(updates, file_path)
                        except Exception as e:
                            print(f"[Preview] Callback error: {e}")
            except:
                pass
            
            time.sleep(0.02)
    
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
