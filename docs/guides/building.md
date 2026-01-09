# Building

Learn how to compile your Noteworthy documents using the TUI, CLI, or Noteworthy Studio.

## Build Methods

Noteworthy offers three ways to build:

| Method     | Command                    | Best For                      |
| ---------- | -------------------------- | ----------------------------- |
| **Studio** | `noteworthy -g`            | Visual editing, collaboration |
| **TUI**    | `noteworthy`               | Interactive terminal use      |
| **CLI**    | `python noteworthy_cli.py` | Scripts, CI/CD                |

---

## Studio Build

The web interface provides visual build control.

### Launch

```bash
noteworthy -g
# or with custom port:
noteworthy -g -p 3000
```

### Build Steps

1. Click the **Build** tab in the sidebar
2. Use the grid to select chapters/pages:
   - Click cells to toggle selection
   - Click row/column headers to select entire rows/columns
3. Configure options (frontmatter, covers)
4. Click **Build**
5. Download `output.pdf`

---

## TUI Build

The terminal interface provides keyboard-driven builds.

### Launch

```bash
noteworthy
```

### Navigation

| Key        | Action                      |
| ---------- | --------------------------- |
| `b`        | Open build menu             |
| Arrow keys | Navigate grid               |
| `h/j/k/l`  | Vim-style navigation        |
| `Space`    | Toggle current page         |
| `r`        | Toggle entire row (chapter) |
| `c`        | Toggle entire column        |
| `a`        | Select all                  |
| `n`        | Select none                 |
| `Enter`    | Start build                 |
| `q`        | Quit                        |

### Build Options

| Key | Option                                   |
| --- | ---------------------------------------- |
| `f` | Toggle frontmatter (cover, preface, TOC) |
| `p` | Keep individual PDFs                     |
| `d` | Debug mode                               |
| `e` | Open configuration editors               |

---

## CLI Build

For scripted and CI/CD builds.

### Basic Usage

```bash
# Build entire document
python noteworthy_cli.py

# Build specific chapters (0-indexed)
python noteworthy_cli.py -c 0 1 2

# Skip frontmatter
python noteworthy_cli.py --no-frontmatter

# Debug mode
python noteworthy_cli.py --debug
```

### CLI Flags

| Flag               | Description                     |
| ------------------ | ------------------------------- |
| `-c`, `--chapters` | Space-separated chapter indices |
| `--no-frontmatter` | Skip cover, preface, TOC        |
| `--leave-pdfs`     | Keep individual chapter PDFs    |
| `--debug`          | Verbose output                  |
| `-t`, `--threads`  | Parallel compilation threads    |
| `--flags`          | Pass additional flags to Typst  |

### Example: CI/CD Pipeline

```yaml
# .github/workflows/build.yml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run python noteworthy_cli.py
      - uses: actions/upload-artifact@v4
        with:
          name: document
          path: output.pdf
```

---

## Standalone Compilation

Compile directly with Typst (bypassing Python):

### Full Document

```bash
# Get input flags
eval "typst compile templates/core/parser.typ output.pdf --root . $(noteworthy --print-inputs)"
```

### Single Section

```bash
# Compile chapter 0, page 0 only
typst compile templates/core/parser.typ section.pdf --root . --input target=0/0
```

---

## Build Output

| File          | Description                               |
| ------------- | ----------------------------------------- |
| `output.pdf`  | Final merged document                     |
| `preview.pdf` | Quick preview (if using Studio)           |
| `build/`      | Temporary artifacts (deleted after merge) |

---

## Troubleshooting

### "Typst not found"

Ensure Typst is installed and in PATH:

```bash
typst --version
```

### "pdftk not found"

PDF merging requires pdftk or Ghostscript:

```bash
# macOS
brew install pdftk-java

# Linux  
apt install pdftk
```

### Build Errors

Check the Typst compilation output for errors. Common issues:

| Error              | Solution                    |
| ------------------ | --------------------------- |
| "Unknown variable" | Check templater import path |
| "File not found"   | Verify relative paths       |
| "Syntax error"     | Check Typst syntax          |

---

## Next Steps

- [Collaboration Guide →](collaboration.md)
- [CLI Reference →](../reference/cli.md)
