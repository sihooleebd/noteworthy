import curses
import argparse
import sys
import logging
import shutil
import os
from pathlib import Path
from .config import BUILD_DIR
from .tui.app import run_app

def main():
    parser = argparse.ArgumentParser(description='Build Noteworthy documentation', add_help=False)
    args = parser.parse_args()
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