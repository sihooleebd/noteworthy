
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
# Create project and get launcher
mkdir myproject && cd myproject
curl -O https://raw.githubusercontent.com/sihooleebd/noteworthy/master/noteworthy.py

# Launch
python3 noteworthy.py
```

**[Full Installation Guide](https://noteworthy.benjaminlee.kr/docs.html#getting-started/installation)**

---

## Features

| Feature         | Description                                                       |
| :-------------- | :---------------------------------------------------------------- |
| **15+ Themes**  | Pre-built color schemes, easy customization                       |
| **Modules**     | Math, plotting, geometry, data structures                         |
| **Web Studio**  | Google Docs-style editing, Monaco editor, real-time collaboration |
| **Solo Mode**   | Single-user mode with tinymist-powered fast live preview          |
| **Fast Builds** | Parallel compilation, incremental updates                         |
| **PDF Output**  | Merged PDFs with bookmarks and metadata                           |

---

## Commands

| Command                               | Description                                                          |
| :------------------------------------ | :------------------------------------------------------------------- |
| `python3 noteworthy.py`               | Launch Terminal UI                                                   |
| `python3 noteworthy.py -g (-p) (-nc)` | Launch Web GUI<br>`-p xxxx` for specific port<br>`-nc` for solo mode |
| `python3 noteworthy.py -u (-n) (-f)`  | Update from GitHub<br>`-n` for nightly<br>`-f` for force             |
| `python3 noteworthy_cli.py`           | Non-interactive CLI build                                            |

**[Full CLI Reference](https://noteworthy.benjaminlee.kr/docs.html#reference/cli)**

---

## Documentation

**[Read the Docs](https://noteworthy.benjaminlee.kr/docs.html)**

| Section                                                                                     | Description                    |
| :------------------------------------------------------------------------------------------ | :----------------------------- |
| [Getting Started](https://noteworthy.benjaminlee.kr/docs.html#getting-started/installation) | Installation and first project |
| [Guides](https://noteworthy.benjaminlee.kr/docs.html#guides/theming)                        | Theming, modules, building     |
| [Reference](https://noteworthy.benjaminlee.kr/docs.html#reference/cli)                      | CLI, config files, API         |
| [Architecture](https://noteworthy.benjaminlee.kr/docs.html#architecture/overview)           | System internals               |

---

## Example Project

- For the `legacy` branch(formerly `master`), see a complete example at [math-noteworthy](https://github.com/sihooleebd/math-noteworthy).
- For the `master` branch(formerly `nightly-v1`), see a complete example at [calculus-1](https://github.com/sihooleebd/calculus-1).
- Both projects are handmade by the project authors. 

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
- [Tinymist](https://github.com/Myriad-Dreamin/tinymist) — Fast live preview
- [CeTZ](https://github.com/cetz-package/cetz) — Drawing library
- [FastAPI](https://fastapi.tiangolo.com/) — Web framework
- [Monaco Editor](https://microsoft.github.io/monaco-editor/) — Code editor

---

Created by [Sihoo Lee](https://github.com/sihooleebd) & [Hojun Lee](https://github.com/R0K0R)

**Noteworthy** — *A framework for noteworthy educational documents.*
