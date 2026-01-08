# System Architecture

Noteworthy is a hybrid system combining a Python-based build orchestration layer with a Typst-based rendering engine.

## Overview

The system consists of three main components:
1.  **Python Orchestrator (`noteworthy.py`)**: Handles CLI arguments, TUI, configuration management, and build coordination.
2.  **Core Parser (`noteworthy/core`)**: Logic for scanning the project structure, generating build plans, and executing Typst compilations.
3.  **GUI Server (`noteworthy/gui`)**: A FastAPI-based backend and web frontend for visual editing and collaboration.
4.  **Typst Templates (`templates/`)**: A modular library of Typst components, layouts, and drawing tools.

## The Build Process

The build workflow when running `python3 noteworthy.py` is as follows:

1.  **Bootstrap**: `noteworthy.py` runs first. It checks if the `noteworthy` package is installed and updates it if necessary (via GitHub API).
2.  **Configuration Loading**: The system reads JSON configs from `config/` (hierarchy, metadata, styling).
3.  **TUI / CLI**: The user interacts with the Terminal UI to select chapters or configure settings.
4.  **Content Scanning**: `core/build.py` scans the `content/` directory. It maps `content/X/Y.typ` structure to a sequential chapter/page order.
5.  **Compilation**:
    - The system invokes `typst compile` on target files.
    - It passes layout information (like chapter folders) to Typst via CLI `--input` flags or generated JSON files.
    - The main entry point for compilation is usually `templates/parser.typ` (or similar wrapper), which dynamically imports the content files.
6.  **PDF Manipulation**: After Typst generates PDF chunks (one per chapter or section), the Python script uses `pdftk` or `cpdf` to merge them into a single `output.pdf`, applying metadata and bookmarks.

## Directory Structure

-   `noteworthy.py`: The entry point script.
-   `noteworthy/`: Python source code.
    -   `core/`: Build logic, file system syncing.
    -   `tui/`: Text User Interface components.
    -   `gui/`: Web-based GUI server and static assets.
-   `templates/`: Typst source code.
    -   `module/`: Functional modules (canvas, graph, etc.).
    -   `layouts/`: Page layouts (outline, etc.).
    -   `systemconfig/`: Internal configuration templates.
-   `content/`: User content, organized by `ChapterID/PageID.typ` folders.
-   `config/`: User configuration files (JSON).
-   `docs/`: Documentation.

## Integration Points

### Python -> Typst
Data is passed from Python to Typst primarily through:
-   **CLI `--input` flags**: For passing simple strings or JSON blobs (e.g., folder maps).
-   **Generated Files**: Sometimes temporary files (like `toc_labels.json`) are generated for Typst to read.

### Typst -> PDF
Typst renders the `.typ` files into standard PDF. The Python script then treats these PDFs as artifacts to be assembled.
