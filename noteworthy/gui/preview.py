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
        self.process = None
        self.running = False
        self.monitor_thread = None
        self.page_mapping = []
        self.preview_cache = {}
        self.callbacks = []
        
        # Cache directory in project build folder
        self.cache_dir = BASE_DIR / "build" / ".preview_cache"
    
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
        if self.process:
            self.stop_watch()
        
        # Clear cache
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        typst_bin = self._find_typst()
        print(f"[Preview] Using typst: {typst_bin}")
        
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
        
        print(f"[Preview] Found chapters: {chapter_folders}")
        print(f"[Preview] Found pages: {page_folders}")
        
        # Parse content file path to find the target
        # Expected format: content/{chapter_id}/{page_id}.typ
        target = None
        if file_path.startswith("content/"):
            parts = file_path.replace("content/", "").replace(".typ", "").split("/")
            if len(parts) == 2:
                ch_name = parts[0]  # Actual folder name like "0", "1", etc.
                pg_name = parts[1]  # Actual file name without .typ
                
                # Find the index of this chapter
                if ch_name in chapter_folders:
                    ch_idx = chapter_folders.index(ch_name)
                    pg_files = page_folders.get(str(ch_idx), [])
                    if pg_name in pg_files:
                        pg_idx = pg_files.index(pg_name)
                        target = f"{ch_idx}/{pg_idx}"
                        print(f"[Preview] Target: {target} (chapter {ch_name}, page {pg_name})")
        
        # Use parser.typ with target input for content files
        if target and RENDERER_FILE.exists():
            watch_file = RENDERER_FILE
        else:
            watch_file = BASE_DIR / file_path
            if not watch_file.exists():
                print(f"[Preview] File not found: {watch_file}")
                return
        
        cache_pattern = self.cache_dir / "page-{n}.svg"
        
        import json
        cmd = [
            typst_bin,
            "watch",
            str(watch_file),
            str(cache_pattern),
            "--root", str(BASE_DIR),
            "--input", f"chapter-folders={json.dumps(chapter_folders)}",
            "--input", f"page-folders={json.dumps(page_folders)}"
        ]
        
        if target:
            cmd.extend(["--input", f"target={target}"])
        
        print(f"[Preview] Running: {' '.join(cmd)}")
        
        try:
            # Use stderr=STDOUT to combine output, don't block on PIPE
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # Line buffered
            )
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            # Also start a thread to read typst output
            self.output_thread = threading.Thread(target=self._read_output, daemon=True)
            self.output_thread.start()
            
            print(f"[Preview] Started watching {file_path}")
        except Exception as e:
            print(f"[Preview] Failed to start typst: {e}")
    
    def _read_output(self):
        """Read and log typst output."""
        try:
            for line in iter(self.process.stdout.readline, ''):
                if not self.running:
                    break
                if line:
                    print(f"[Typst] {line.rstrip()}")
        except:
            pass
    
    def stop_watch(self):
        """Stop current watch process."""
        self.running = False
        if self.process:
            self.process.terminate()
            self.process = None
    
    def add_callback(self, cb):
        """Register callback for updates."""
        self.callbacks.append(cb)
    
    def _monitor_loop(self):
        """Monitor cache directory for SVG updates."""
        last_mtimes = {}
        
        while self.running:
            if not self.process:
                time.sleep(0.1)
                continue
            
            # Check if process died
            if self.process.poll() is not None:
                print(f"[Preview] Typst process exited with code: {self.process.returncode}")
                self.running = False
                self.process = None
                break
            
            # Scan for new/updated SVGs
            try:
                svgs = list(self.cache_dir.glob("page-*.svg"))
                current_pages = []
                updates = []
                
                for svg in svgs:
                    try:
                        num = int(svg.stem.split('-')[-1])
                        current_pages.append(num)
                        
                        mtime = svg.stat().st_mtime
                        if mtime != last_mtimes.get(svg.name):
                            # Read with retry for incomplete writes
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
                                self.preview_cache[num] = content.encode('utf-8')
                                last_mtimes[svg.name] = mtime
                                updates.append({'page': num, 'svg': content})
                    except:
                        pass
                
                self.page_mapping = sorted(current_pages)
                
                if updates:
                    for cb in self.callbacks:
                        try:
                            cb(updates)
                        except:
                            pass
            except:
                pass
            
            time.sleep(0.02)  # 50Hz
    
    def get_status(self):
        """Get current preview status."""
        return {
            "running": self.running and self.process is not None,
            "pages": self.page_mapping
        }
    
    def get_image(self, page_num):
        """Get cached image for a page."""
        return self.preview_cache.get(int(page_num))
