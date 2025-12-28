# Templates System

The `templates/` directory contains the core Typst source code for Noteworthy.

## Overview

The system is organized into modular components. Most of the user-facing functionality resides in `templates/module/`.

## Directory Structure

### `module/`
The standard library of Noteworthy. Contains functional modules for drawing, layout, and data.

-   **[Canvas](modules/canvas.md)**: `canvas/*` - The core drawing engine.
-   **[Graph](modules/graph.md)**: `graph/*` - Function plotting and calculus.
-   **[Geometry](modules/geometry.md)**: `shape/*` - Points, lines, circles, and constructions.
-   **[DSA](modules/dsa.md)**: `dsa/*` - Data Structures and Algorithms.
-   **[Trees](modules/trees.md)**: `trees/*` - Tree visualizations.
-   **[Layout & Covers](modules/layout.md)**: `layout/*`, `cover/*` - Outlines, title pages.
-   **[Others](modules/others.md)**: `block/*`, `data/*`, `combi/*` - Blocks, tables, combinatorics.

### `layouts/`
Contains raw layout implementations (like the outline function) which are often wrapped by modules.

### `systemconfig/`
Internal system configuration files. These handle the low-level mapping of theme tokens to Typst dictionaries. Users generally shouldn't need to modify this.

### `parser.typ`
The main entry point for the Typst compiler. When `noteworthy.py` runs `typst compile`, it targets this file or files derived from it. It sets up the document context (preface, pages, bibliography).
