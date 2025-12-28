# Workflow & Tools

Master the Noteworthy build system and TUI tools.

## TUI System

Run the system with:
```bash
python3 noteworthy.py
```

### Editors
Press `e` in the build menu to access editors:

| Editor               | Function                                          |
| :------------------- | :------------------------------------------------ |
| **Config Editor**    | Edit document metadata (title, author) and theme. |
| **Hierarchy Editor** | Manage chapter/page structure visually.           |
| **Scheme Editor**    | Create or modify color themes.                    |
| **Snippets Editor**  | Edit custom Typst macros.                         |
| **Index Ignore**     | Manage files excluded from the build.             |

---

## Hierarchy Sync Wizard

The system automatically detects discrepancies between `hierarchy.json` and your `content/` folder structure.

### Conflict Resolution
When mismatch is found:

| Option | Action               | Description                                     |
| :----- | :------------------- | :---------------------------------------------- |
| `[A]`  | **Create Missing**   | Generates missing `.typ` files on disk.         |
| `[B]`  | **Add to Hierarchy** | Adds new files to hierarchy, preserving titles. |
| `[R]`  | **Remove**           | Deletes hierarchy entries for missing files.    |
| `[I]`  | **Ignore**           | Adds new files to `.indexignore`.               |

**Note**: When adding (`[B]`), existing metadata like page numbers is preserved.

---

## Build System

### Standalone Compilation
Compile the full document without the Python TUI:
```bash
# With exact folder/page info (recommended)
eval "typst compile templates/parser.typ output.pdf --root . $(python3 noteworthy.py --print-inputs)"

# Quick compile (uses 1-indexed fallback)
typst compile templates/parser.typ output.pdf --root .
```

The `--print-inputs` flag outputs Typst `--input` flags with your content folder structure.

### Single Section Compilation
Compile a specific section for faster iteration:
```bash
typst compile templates/parser.typ section.pdf --root . --input target=0/0
```

### CLI Flags
Pass flags to `python3 noteworthy.py`:

| Flag             | Description                                       |
| :--------------- | :------------------------------------------------ |
| `--load`         | Force update from `master`.                       |
| `--force-update` | Destructive reinstall (wipes templates).          |
| `--print-inputs` | Output Typst `--input` flags for content folders. |
| `-d`             | Debug mode (verbose).                             |
| `-c`             | Config mode (custom Typst flags).                 |

### Directory Structure

- `content/`: Your `.typ` source files.
- `config/`: JSON configuration.
- `templates/`: Core system templates (do not edit unless necessary).
- `docs/`: This documentation.
- `output.pdf`: Final merged document.
- `tutor.pdf`: Development preview.
