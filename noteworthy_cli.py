#!/usr/bin/env python3
import argparse
import sys
import json
import logging
import shutil
import time
import os
from pathlib import Path

# Fix import path to allow importing from noteworthy package
sys.path.append(str(Path(__file__).parent))

from noteworthy.config import BASE_DIR, BUILD_DIR, OUTPUT_FILE, METADATA_FILE, HIERARCHY_FILE, PREFACE_FILE
from noteworthy.utils import load_settings, save_settings, load_config_safe, check_dependencies, scan_content
from noteworthy.core.build import (
    BuildManager, compile_target, merge_pdfs, create_pdf_metadata, 
    apply_pdf_metadata, zip_build_directory, get_pdf_page_count
)

def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')

class CliTarget:
    def __init__(self, chapters=None, pages=None):
        self.chapters = chapters or []  # List of chapter indices
        self.pages = pages or []        # List of (ch_idx, pg_idx) tuples


def run_build(args):
    # Load settings and config
    settings = load_settings()
    config = load_config_safe()
    
    # Override settings with CLI args
    debug = args.debug or settings.get('debug', False)
    setup_logging(debug)
    
    try:
        hierarchy = json.loads(HIERARCHY_FILE.read_text())
    except Exception as e:
        print(f"Error loading hierarchy: {e}")
        return

    # Determine what to build
    selected_pages = []
    
    # Process chapter filters
    target_chapters = set()
    if args.chapters:
        for c in args.chapters:
            if 0 <= c < len(hierarchy):
                target_chapters.add(c)
            else:
                print(f"Warning: Chapter {c} not found in hierarchy")
    
    # Default to all if no specific selection
    if not target_chapters:
        target_chapters = set(range(len(hierarchy)))

    for ci in target_chapters:
        ch = hierarchy[ci]
        for ai in range(len(ch['pages'])):
            selected_pages.append((ci, ai))

    if not selected_pages:
        print("No pages selected for build.")
        return

    print("Checking dependencies...")
    try:
        check_dependencies()
    except SystemExit:
        print("Missing dependencies! Please ensure typst, pdfinfo, and pdfunite/ghostscript/pdftk are installed.")
        return

    # Prepare build dir
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir()

    print(f"Building {len(selected_pages)} pages from {len(target_chapters)} chapters...")
    
    # Construct opts dictionary relative to TUI expectations
    opts = {
        'debug': debug,
        'frontmatter': not args.no_frontmatter, # Default to true
        'leave_individual': args.leave_pdfs,
        'typst_flags': args.flags if args.flags else settings.get('typst_flags', []),
        'threads': args.threads or settings.get('threads', max(1, (os.cpu_count() or 1) // 2)),
        'selected_pages': selected_pages
    }
    
    ch_folders, pg_folders = scan_content()
    opts['ch_folders'] = ch_folders
    opts['pg_folders'] = pg_folders

    # Main Build Process
    try:
        # Calculate tasks to enable progress tracking (simple version)
        by_ch = {}
        for ci, ai in selected_pages:
            by_ch.setdefault(ci, []).append(ai)
        chapters = [(i, hierarchy[i]) for i in sorted(by_ch.keys())]
        
        bm = BuildManager(BUILD_DIR)
        
        # We need a simple progress callback
        total_tasks = 0 # Will be updated
        completed_tasks = 0
        
        def on_log(msg, ok=True):
            if debug or not ok:
                pass # Already handled by logging/print
            
        def on_progress():
            nonlocal completed_tasks
            completed_tasks += 1
            # print(f"\rProgress: {completed_tasks} tasks completed", end="", flush=True)
            return True

        callbacks = {'on_log': on_log, 'on_progress': on_progress}
        
        print("Compiling pages...")
        start_time = time.time()
        
        pdfs = bm.build_parallel(chapters, config, opts, callbacks)
        
        compile_time = time.time() - start_time
        print(f"\nCompilation finished in {compile_time:.1f}s")
        
        current_page_count = sum([get_pdf_page_count(p) for p in pdfs]) + 1
        page_map = bm.page_map
        
        # Outline / TOC
        if opts['frontmatter'] and config.get('display-outline', True):
            print("Regenerating TOC...")
            out = BUILD_DIR / '02_outline.pdf'
            
            folder_flags = list(opts['typst_flags'])
            folder_flags.extend(['--input', f'chapter-folders={json.dumps(ch_folders)}'])
            folder_flags.extend(['--input', f'page-folders={json.dumps(pg_folders)}'])
            
            compile_target(
                'outline', 
                out, 
                page_offset=page_map.get('outline', 0), 
                page_map=page_map, 
                extra_flags=folder_flags, 
                log_callback=lambda m: None 
            )
        
        print(f"Total pages: {current_page_count - 1}")
        print("Merging PDFs...")
        
        method = merge_pdfs(pdfs, OUTPUT_FILE)
        
        if not method or not OUTPUT_FILE.exists():
            print("Merge failed!")
            return
            
        print("Applying Metadata...")
        bm_file = BUILD_DIR / 'bookmarks.txt'
        bookmarks_list = create_pdf_metadata(chapters, page_map, bm_file)
        apply_pdf_metadata(OUTPUT_FILE, bm_file, 'Noteworthy Framework', 'Sihoo Lee, Lee Hojun', bookmarks_list)
        
        if opts['leave_individual']:
            zip_build_directory(BUILD_DIR)
            print(f"Individual PDFs archived in {BUILD_DIR}")
            
        if OUTPUT_FILE.exists() and BUILD_DIR.exists() and not opts['leave_individual']:
            shutil.rmtree(BUILD_DIR)
            
        print(f"\nBuild Complete! Output: {OUTPUT_FILE}")
        
    except KeyboardInterrupt:
        print("\nBuild cancelled.")
        if BUILD_DIR.exists():
             shutil.rmtree(BUILD_DIR)
    except Exception as e:
        print(f"\nBuild failed: {e}")
        if debug:
            import traceback
            traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description='Noteworthy CLI Builder')
    
    parser.add_argument('-c', '--chapters', type=int, nargs='+', help='Specific chapter indices to build (space separated)')
    
    parser.add_argument('--no-frontmatter', action='store_true', help='Skip frontmatter (cover, preface, TOC)')
    parser.add_argument('--leave-pdfs', action='store_true', help='Keep individual PDFs in build folder')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    parser.add_argument('-t', '--threads', type=int, help='Number of threads to use')
    parser.add_argument('--flags', nargs='+', help='Additional Typst CLI flags')
    
    # Update flags
    parser.add_argument('-u', '--update', action='store_true', help='Update noteworthy')
    parser.add_argument('-n', '--nightly', action='store_true', help='Use nightly branch')
    parser.add_argument('-f', '--force', action='store_true', help='Force update (clean install)')
    
    # Legacy
    parser.add_argument('--update-nightly', action='store_true', help='Legacy: Update to nightly')

    args = parser.parse_args()
    
    # Check for update request
    do_update = False
    branch = 'master'
    
    if args.update:
        do_update = True
        
    if args.update_nightly:
        do_update = True
        branch = 'nightly'
        
    if args.nightly:
        branch = 'nightly'
    
    if do_update:
        try:
            from noteworthy.utils import generate_updater
            
            print(f"Initiating update (branch: {branch}, force: {args.force})...")
            
            script_content = generate_updater(branch, args.force, 'noteworthy_cli.py')
            updater_path = Path('_update_runner.py')
            updater_path.write_text(script_content)
            
            os.chmod(updater_path, 0o755)
            # Use sys.executable to ensure we run with the same python interpreter
            os.execv(sys.executable, [sys.executable, str(updater_path)])
            
        except ImportError:
            print("Error: 'noteworthy' package not found. Cannot generate updater.")
            sys.exit(1)
        except Exception as e:
            print(f"Update initiation failed: {e}")
            sys.exit(1)
    
    run_build(args)

if __name__ == '__main__':
    main()
