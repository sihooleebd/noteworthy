> **CRITICAL SECURITY WARNING**
>
> **This is the ONLY official repository for Noteworthy.**
> We are aware of unauthorized clones being used to spread malware.
>
> - **We NEVER distribute executable files (.exe, .msi, .dmg).**
> - This project is **source code only**.
> - Always verify: `https://github.com/sihooleebd/noteworthy`

# Noteworthy

```
         ,--.
       ,--.'|
   ,--,:  : |
,`--.'`|  ' :
|   :  :  | |
:   |   \ | :
|   : '  '; |
'   ' ;.    ;
|   | | \   |
'   : |  ; .'
|   | '`--'
'   : |
;   |.'
'---'
```

**A powerful Typst framework for creating beautiful educational documents.**

[![Typst](https://img.shields.io/badge/Typst-0.12%2B-239DAD?logo=typst)](https://typst.app/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Community-5865F2?logo=discord&logoColor=white)](https://discord.gg/W3S2UQCJzM)
[![Website](https://img.shields.io/badge/Website-noteworthy.benjaminlee.kr-purple)](https://noteworthy.benjaminlee.kr/)

---

## Quick Start

```bash
# Create project and download launcher
mkdir myproject && cd myproject
mkdir content
curl -O https://raw.githubusercontent.com/sihooleebd/noteworthy/master/noteworthy.py

# Run TUI (downloads everything on first run)
python3 noteworthy.py

# For GUI mode, install web dependencies first
pip install fastapi uvicorn
python3 noteworthy.py -g
```

**[Full Installation Guide](docs/getting-started/installation.md)**

---

## Features

| Feature         | Description                                     |
| --------------- | ----------------------------------------------- |
| **15+ Themes**  | Pre-built color schemes, easy customization     |
| **Modules**     | Math, plotting, geometry, data structures       |
| **Web GUI**     | Real-time preview, collaboration, Monaco editor |
| **Fast Builds** | Parallel compilation, incremental updates       |
| **PDF Output**  | Merged PDFs with bookmarks and metadata         |

---

## Commands

| Command                            | Description                    |
| ---------------------------------- | ------------------------------ |
| `python3 noteworthy.py`            | Launch Terminal UI             |
| `python3 noteworthy.py -g`         | Launch Web GUI                 |
| `python3 noteworthy.py -g -p 3000` | GUI on custom port             |
| `python3 noteworthy.py -u`         | Update from GitHub             |
| `python3 noteworthy.py -u -n`      | Update to nightly branch       |
| `python3 noteworthy.py -u -f`      | Force update (clean reinstall) |
| `python3 noteworthy_cli.py`        | Non-interactive CLI build      |

---

## Documentation

**[Documentation](docs/index.md)**

| Section                                                 | Description                    |
| ------------------------------------------------------- | ------------------------------ |
| [Getting Started](docs/getting-started/installation.md) | Installation and first project |
| [Guides](docs/guides/theming.md)                        | Theming, modules, building     |
| [Reference](docs/reference/cli.md)                      | CLI, config files, API         |
| [Architecture](docs/architecture/overview.md)           | System internals               |
| [Contributing](docs/contributing/development-setup.md)  | Development setup              |

---

## Example Project

See a complete example at [math-noteworthy](https://github.com/sihooleebd/math-noteworthy).

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Dev setup
git clone https://github.com/sihooleebd/noteworthy
cd noteworthy
uv sync
source .venv/bin/activate
```

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built with:
- [Typst](https://typst.app/) — The typesetting system
- [CeTZ](https://github.com/cetz-package/cetz) — Drawing library
- [FastAPI](https://fastapi.tiangolo.com/) — Web framework
- [Monaco Editor](https://microsoft.github.io/monaco-editor/) — Code editor

---

Created by [Sihoo Lee](https://github.com/sihooleebd) & [Hojun Lee](https://github.com/R0K0R)

**Noteworthy** — *A framework for noteworthy educational documents.*
