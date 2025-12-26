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

### Single File Compilation
To speed up development, compile just the file you're working on:
```bash
typst compile content/1/1.typ
```
Or for a specific section via the build system:
```bash
typst compile templates/parser.typ --input target=01.01 section.pdf
```

### Build Flags
Pass flags to `python3 noteworthy.py`:

| Flag             | Description                              |
| :--------------- | :--------------------------------------- |
| `--load`         | Force update from `master`.              |
| `--force-update` | Destructive reinstall (wipes templates). |
| `-d`             | Debug mode (verbose).                    |
| `-c`             | Config mode (custom Typst flags).        |

### Directory Structure

- `content/`: Your `.typ` source files.
- `config/`: JSON configuration.
- `templates/`: Core system templates (do not edit unless necessary).
- `docs/`: This documentation.
- `output.pdf`: Final merged document.
- `tutor.pdf`: Development preview.
