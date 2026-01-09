#!/usr/bin/env python3
"""
Legacy launcher - forwards to noteworthy package.
For modern usage, run: noteworthy (after uv sync)
"""
import sys
from pathlib import Path

# Ensure package is importable when running from project root
sys.path.insert(0, str(Path(__file__).parent))

from noteworthy.__main__ import main

if __name__ == "__main__":
    main()
