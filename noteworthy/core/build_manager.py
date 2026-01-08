# Build Manager - Parallel build orchestration

import os
import json
import threading
import concurrent.futures
from pathlib import Path

from ..config import PREFACE_FILE
from ..utils import scan_content


class BuildManager:
    """Manages parallel PDF compilation with page offset tracking."""
    
    def __init__(self, build_dir):
        self.build_dir = build_dir
        self.cache_file = build_dir / 'page_cache.json'
        self.page_counts = self._load_cache()
        self.page_map = {}
        self.current_offset = 1
        self.lock = threading.Lock()
        
    def _load_cache(self):
        """Load page count cache from previous builds."""
        if self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text())
            except:
                pass
        return {}
        
    def save_cache(self):
        """Persist page count cache for future builds."""
        try:
            self.cache_file.write_text(json.dumps(self.page_counts))
        except:
            pass
            
    def get_predicted_count(self, key):
        """Get predicted page count for a target (from cache or default 1)."""
        return self.page_counts.get(key, 1)
        
    def update_count(self, key, count):
        """Thread-safe update of page count."""
        with self.lock:
            self.page_counts[key] = count
            
    def build_parallel(self, chapters, config, opts, callbacks):
        """
        Build all targets in parallel with automatic page offset recalculation.
        
        Args:
            chapters: List of (index, chapter_dict) tuples
            config: Document configuration
            opts: Build options (frontmatter, typst_flags, threads, etc.)
            callbacks: Dict with 'on_log' and 'on_progress' callbacks
            
        Returns:
            List of paths to generated PDFs in order
        """
        max_workers = opts.get('threads', os.cpu_count() or 1)
        flags = opts.get('typst_flags', [])
        
        # Use provided folders if available, otherwise scan
        ch_folders = opts.get('ch_folders')
        pg_folders = opts.get('pg_folders')
        
        if not ch_folders or not pg_folders:
            ch_folders, pg_folders = scan_content()
        
        # Add folder info to flags (passed to all compile calls)
        folder_flags = flags.copy()
        folder_flags.extend(['--input', f'chapter-folders={json.dumps(ch_folders)}'])
        folder_flags.extend(['--input', f'page-folders={json.dumps(pg_folders)}'])
        
        # Build task list
        callbacks.get('on_log', lambda m, o: None)(f"Building {len(chapters)} chapters (parallel)", True)
        tasks = self._create_task_list(chapters, config, opts, ch_folders, pg_folders)
        callbacks.get('on_log', lambda m, o: None)(f"Generated {len(tasks)} tasks", True)
        
        task_map = {t[0]: t for t in tasks}
        ordered_keys = [t[0] for t in tasks]
        
        # Calculate initial page offsets
        projected_offsets = {}
        current = 1
        for key in ordered_keys:
            projected_offsets[key] = current
            current += self.get_predicted_count(key)
            
        # Iterative build with pagination correction
        iteration = 0
        while True:
            iteration += 1
            callbacks.get('on_log', lambda m, o: None)(f"Build Pass {iteration}...", True)
            
            to_run = list(ordered_keys) if iteration == 1 else self._get_dirty_tasks(ordered_keys, projected_offsets, callbacks)
            
            if not to_run and iteration > 1:
                break
                
            self._execute_parallel(to_run, task_map, projected_offsets, folder_flags, max_workers, callbacks)
            
            if iteration > 3:
                callbacks.get('on_log', lambda m, o: None)("Max retries reached. Pagination might be unstable.", False)
                break
                
            # Recalculate offsets for next iteration
            if iteration == 1:
                projected_offsets = self._recalc_offsets(ordered_keys)
                
        self.save_cache()
        self.page_map = projected_offsets
        return [task_map[k][3] for k in ordered_keys]
    
    def _create_task_list(self, chapters, config, opts, ch_folders, pg_folders):
        """Create list of compilation tasks."""
        tasks = []
        
        if opts['frontmatter']:
            if config.get('display-cover', True):
                tasks.append(('cover', 'front', 'cover', self.build_dir / '00_cover.pdf', 'Cover'))
            try:
                if PREFACE_FILE.exists() and PREFACE_FILE.read_text().strip():
                    tasks.append(('preface', 'front', 'preface', self.build_dir / '01_preface.pdf', 'Preface'))
            except:
                pass
            if config.get('display-outline', True):
                tasks.append(('outline', 'front', 'outline', self.build_dir / '02_outline.pdf', 'TOC'))
        
        selected_set = set(opts.get('selected_pages', []))
        use_selection = 'selected_pages' in opts

        for ci, ch in chapters:
            ch_folder = ch_folders[ci] if ci < len(ch_folders) else str(ci)
            ch_key = f'chapter-{ci}'
            
            # Filter pages based on selection
            pages_to_build = []
            pg_files = pg_folders.get(str(ci), [])
            
            for ai, p in enumerate(ch['pages']):
                if use_selection and (ci, ai) not in selected_set:
                    continue
                pages_to_build.append((ai, p))

            if pages_to_build:
                if config.get('display-chap-cover', True):
                    tasks.append((ch_key, 'chapter', f'chapter-{ci}', 
                                 self.build_dir / f'10_chapter_{ci}_cover.pdf', f"Chapter {ch_folder}"))
                
                for ai, p in pages_to_build:
                    pg_file = pg_files[ai] if ai < len(pg_files) else str(ai)
                    key = f'{ci}/{ai}'
                    tasks.append((key, 'section', key, 
                                 self.build_dir / f'20_page_{ci}_{ai}.pdf', f"Section {pg_file}: {p['title']}"))
                
        return tasks
    
    def _recalc_offsets(self, ordered_keys):
        """Recalculate page offsets based on actual page counts."""
        new_offsets = {}
        curr = 1
        for key in ordered_keys:
            new_offsets[key] = curr
            curr += self.get_predicted_count(key)
        return new_offsets
    
    def _get_dirty_tasks(self, ordered_keys, projected_offsets, callbacks):
        """Find tasks that need recompilation due to offset changes."""
        new_offsets = {}
        curr = 1
        dirty_index = -1
        
        for idx, key in enumerate(ordered_keys):
            new_offsets[key] = curr
            curr += self.get_predicted_count(key)
            
            if dirty_index == -1 and new_offsets[key] != projected_offsets[key]:
                dirty_index = idx
                
        if dirty_index == -1:
            return []
            
        # Update projected offsets
        projected_offsets.clear()
        projected_offsets.update(new_offsets)
        
        to_run = ordered_keys[dirty_index:]
        callbacks.get('on_log', lambda m, o: None)(
            f"Detected layout shift at {ordered_keys[dirty_index]}. Recompiling {len(to_run)} tasks.", True
        )
        return to_run
    
    def _execute_parallel(self, to_run, task_map, projected_offsets, folder_flags, max_workers, callbacks):
        """Execute compilation tasks in parallel."""
        from .build import compile_target, get_pdf_page_count
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_key = {}
            for key in to_run:
                t_data = task_map[key]
                offset = projected_offsets[key]
                
                f = executor.submit(
                    compile_target, 
                    t_data[2],
                    t_data[3],
                    page_offset=offset,
                    extra_flags=folder_flags,
                    log_callback=lambda m: None 
                )
                future_to_key[f] = key
                
            for future in concurrent.futures.as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    future.result()
                    path = task_map[key][3]
                    count = get_pdf_page_count(path)
                    self.update_count(key, count)
                    
                    if callbacks.get('on_progress'):
                        if callbacks['on_progress']() is False:
                            executor.shutdown(wait=False, cancel_futures=True)
                            raise KeyboardInterrupt("Build cancelled by user")
                            
                except Exception as e:
                    callbacks.get('on_log', lambda m, o: None)(f"Task {key} failed: {e}", False)
                    raise
