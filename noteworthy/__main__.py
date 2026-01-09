#!/usr/bin/env python3
"""
Noteworthy - Main entry point
Handles TUI, GUI, and update operations
"""
import curses
import argparse
import sys
import os
import json
import logging
import shutil
from pathlib import Path

from .config import BUILD_DIR
from .tui.app import run_app
from .utils import generate_updater


def main():
    parser = argparse.ArgumentParser(description='Noteworthy Launcher')
    parser.add_argument('--print-inputs', action='store_true', help='Print Typst input flags')
    parser.add_argument('-g', '--gui', action='store_true', help='Launch web GUI instead of TUI')
    parser.add_argument('-p', '--port', type=int, default=8000, help='Port for GUI server (default: 8000)')
    
    # Update flags
    parser.add_argument('-u', '--update', action='store_true', help='Update noteworthy')
    parser.add_argument('-n', '--nightly', action='store_true', help='Use nightly branch')
    parser.add_argument('-f', '--force', action='store_true', help='Force update (clean install)')

    # Legacy (Backward Compatibility)
    parser.add_argument('--update-nightly', action='store_true', help='Legacy: Update to nightly')
    parser.add_argument('--load', action='store_true', help='Legacy: Alias for --update')
    parser.add_argument('--load-nightly', action='store_true', help='Legacy: Alias for --update-nightly')
    parser.add_argument('--force-update', action='store_true', help='Legacy: Alias for --update --force')
    parser.add_argument('--force-update-nightly', action='store_true', help='Legacy: Alias for --update-nightly --force')
    
    args = parser.parse_args()

    # Handle --print-inputs
    if args.print_inputs:
        content_dir = Path('content')
        ch_folders = []
        pg_folders = {}
        
        if content_dir.exists():
            ch_dirs = sorted(
                [d for d in content_dir.iterdir() if d.is_dir() and d.name.isdigit()],
                key=lambda d: int(d.name)
            )
            for idx, ch_dir in enumerate(ch_dirs):
                pg_files = sorted(
                    [f.stem for f in ch_dir.glob('*.typ') if f.stem.isdigit()],
                    key=lambda s: int(s)
                )
                if pg_files:
                    ch_folders.append(ch_dir.name)
                    pg_folders[str(idx)] = pg_files
        
        print(f"--input chapter-folders='{json.dumps(ch_folders)}' --input page-folders='{json.dumps(pg_folders)}'")
        sys.exit(0)
    
    # Check for update request
    do_update = False
    branch = 'master'
    force = args.force
    
    # Triggers
    if args.update or args.load or args.force_update:
        do_update = True
        
    if args.update_nightly or args.load_nightly or args.force_update_nightly:
        do_update = True
        branch = 'nightly'
        
    # Modifiers
    if args.nightly:
        branch = 'nightly'
        
    if args.force_update or args.force_update_nightly:
        force = True
        
    # Auto-install if missing
    if not Path('noteworthy').exists():
        do_update = True
        print("Noteworthy folder not found. Initiating download...")
        
    if do_update:
        print(f"Initiating update (branch: {branch}, force: {force})...")
        script_content = generate_updater(branch, force, 'noteworthy.py')
        updater_path = Path('_update_runner.py')
        updater_path.write_text(script_content)
        
        os.chmod(updater_path, 0o755)
        os.execv(sys.executable, [sys.executable, str(updater_path)])
        sys.exit(0)

    # Ensure preface.typ exists to prevent build errors
    preface_path = Path('config/preface.typ')
    if Path('config').exists() and not preface_path.exists():
        try:
            preface_path.write_text('')
        except Exception as e:
            print(f"Warning: Could not create default preface: {e}")

    # Launch GUI if requested
    if args.gui:
        try:
            from .gui.app import run_gui
            run_gui(port=args.port)
        except ImportError as e:
            print("Error: GUI requires additional dependencies.")
            print("Install with: pip install fastapi uvicorn")
            print(f"Details: {e}")
            sys.exit(1)
    else:
        # Launch TUI
        logging.basicConfig(level=logging.CRITICAL)
        os.environ.setdefault('ESCDELAY', '25')
        try:
            curses.wrapper(lambda scr: run_app(scr, args))
        except KeyboardInterrupt:
            print('\nBuild cancelled.')
            if BUILD_DIR.exists():
                shutil.rmtree(BUILD_DIR)
            sys.exit(1)
        except Exception as e:
            print(f'\nBuild failed: {e}')
            import traceback
            traceback.print_exc()
            if BUILD_DIR.exists():
                shutil.rmtree(BUILD_DIR)
            sys.exit(1)


if __name__ == '__main__':
    main()