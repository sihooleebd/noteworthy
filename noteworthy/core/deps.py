# Dependency checking utilities

import shutil
import sys


def check_dependencies():
    """Check that required external tools are installed."""
    missing = []
    
    if not shutil.which('typst'):
        missing.append(("typst", "Install from https://typst.app"))
    
    if not shutil.which('pdfinfo'):
        missing.append(("pdfinfo", "Install with: brew install poppler (macOS) or apt-get install poppler-utils (Linux)"))
    
    has_pdf_tool = shutil.which('pdfunite') or shutil.which('gs')
    if not has_pdf_tool:
        missing.append(("pdfunite/gs", "Install poppler-utils or ghostscript for PDF merging"))
    
    if missing:
        print("Missing dependencies:")
        for tool, hint in missing:
            print(f"  - {tool}: {hint}")
        sys.exit(1)


def get_available_pdf_merger():
    """Return the name of the available PDF merger tool."""
    if shutil.which('pdfunite'):
        return 'pdfunite'
    elif shutil.which('gs'):
        return 'ghostscript'
    elif shutil.which('pdftk'):
        return 'pdftk'
    return None
