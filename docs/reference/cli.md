# CLI Reference

Complete command-line reference for Noteworthy.

## Entry Points

Noteworthy provides three executables:

> [!NOTE]
> **Noteworthy Studio** is our web-based GUI for visual editing and real-time collaboration.

| Command             | Purpose                     |
| ------------------- | --------------------------- |
| `noteworthy`        | Main launcher (TUI/Studio)  |
| `noteworthy_cli.py` | Non-interactive CLI builder |
| `noteworthy.py`     | Bootstrap launcher          |

---

## noteworthy

The primary command after `uv sync` and activating the venv.

### Usage

```bash
noteworthy [OPTIONS]
```

### Options

| Flag      | Long             | Description                         |
| --------- | ---------------- | ----------------------------------- |
|           | `--print-inputs` | Print Typst input flags             |
| `-g`      | `--gui`          | Launch Noteworthy Studio            |
| `-p PORT` | `--port PORT`    | `[-g]` Specify port (default: 8000) |
| `-nc`     | `--no-coop`      | `[-g]` Solo mode (no collaboration) |
|           | `--bind ADDR`    | `[-g]` Listening address (default: `127.0.0.1`) |
|           | `--headless`     | `[-g]` Do not open a browser on startup |
|           | `--packet-log`   | `[-g]` Log low-level Yjs packets (debugging) |
| `-u`      | `--update`       | Update from GitHub                  |
| `-n`      | `--nightly`      | `[-u]` Use nightly branch           |
| `-f`      | `--force`        | `[-u]` Force clean install          |

### Examples

```bash
# Launch TUI
noteworthy

# Launch Noteworthy Studio
noteworthy -g

# Launch Studio in Solo Mode (No collaboration)
noteworthy -g -nc

# Studio on custom port
noteworthy -g -p 3000

# Studio reachable from other machines (LAN, Tailscale, tunnels)
noteworthy -g --bind 0.0.0.0

# Update to latest
noteworthy -u

# Update to nightly (force)
noteworthy -u -n -f

# Print Typst input flags
noteworthy --print-inputs
```

> [!IMPORTANT]
> Studio binds to `127.0.0.1` by default, which accepts connections only from
> the same machine. Serving collaborators on a LAN or through a tunnel requires
> `--bind 0.0.0.0` (see the [Collaboration Guide](../guides/collaboration.md)).

---

## noteworthy_cli.py

Non-interactive CLI for scripted builds.

### Usage

```bash
python noteworthy_cli.py [OPTIONS]
```

### Options

| Flag | Long               | Description                                |
| ---- | ------------------ | ------------------------------------------ |
| `-c` | `--chapters`       | Chapter indices to build (space-separated) |
|      | `--no-frontmatter` | Skip cover, preface, TOC                   |
|      | `--leave-pdfs`     | Keep individual chapter PDFs               |
|      | `--debug`          | Enable verbose logging                     |
| `-t` | `--threads`        | Parallel compilation threads               |
|      | `--flags`          | Additional Typst CLI flags                 |
| `-u` | `--update`         | Update from GitHub                         |
| `-n` | `--nightly`        | `[-u]` Use nightly branch                  |
| `-f` | `--force`          | `[-u]` Force clean install                 |

### Examples

```bash
# Build entire document
python noteworthy_cli.py

# Build chapters 0, 1, 2
python noteworthy_cli.py -c 0 1 2

# Skip frontmatter
python noteworthy_cli.py --no-frontmatter

# Debug mode with 4 threads
python noteworthy_cli.py --debug -t 4

# Pass extra Typst flags
python noteworthy_cli.py --flags "--font-path /fonts"
```

---

## Typst Compilation

Direct Typst compilation without Python:

### Full Document

```bash
# With content folder info (recommended)
eval "typst compile templates/core/parser.typ output.pdf --root . $(noteworthy --print-inputs)"

# Basic (fallback ordering)
typst compile templates/core/parser.typ output.pdf --root .
```

### Single Section

```bash
# Chapter 0, Page 0
typst compile templates/core/parser.typ section.pdf --root . --input target=0/0

# Chapter 2, Page 3
typst compile templates/core/parser.typ section.pdf --root . --input target=2/3
```

### Typst Input Flags

The `--print-inputs` flag outputs:

```bash
--input chapter-folders='["1","2","3"]' --input page-folders='{"0":["1","2"],"1":["1","2","3"]}'
```

This tells Typst the exact content structure.

---

## Environment Variables

| Variable   | Default | Description                 |
| ---------- | ------- | --------------------------- |
| `ESCDELAY` | `25`    | Terminal escape delay (TUI) |

---

## Exit Codes

| Code  | Meaning              |
| ----- | -------------------- |
| `0`   | Success              |
| `1`   | Error (see output)   |
| `130` | Interrupted (Ctrl+C) |

---

## Legacy Flags

These flags are kept for backward compatibility:

| Flag                     | Equivalent |
| ------------------------ | ---------- |
| `--load`                 | `-u`       |
| `--load-nightly`         | `-u -n`    |
| `--force-update`         | `-u -f`    |
| `--update-nightly`       | `-u -n`    |
| `--force-update-nightly` | `-u -n -f` |

---

## See Also

- [Building Guide](../guides/building.md)
- [Config Files Reference](config-files.md)
