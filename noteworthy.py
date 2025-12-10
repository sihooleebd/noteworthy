#!/usr/bin/env python3
import sys
from pathlib import Path
try:
    from noteworthy.__main__ import main
except ImportError:
    sys.path.append(str(Path(__file__).parent))
    from noteworthy.__main__ import main
if __name__ == "__main__":
    main()
