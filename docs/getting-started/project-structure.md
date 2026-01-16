# Project Structure

Understanding how Noteworthy projects are organized.

## Directory Overview

```
myproject/
├── noteworthy.py          # Bootstrap entry point
├── noteworthy_cli.py      # CLI build tool
├── pyproject.toml         # Project configuration
├── uv.lock                # Dependency lockfile
│
├── noteworthy/            # Python package
│   ├── __main__.py        # Main entry point
│   ├── config.py          # Path configuration
│   ├── utils.py           # Utility functions
│   ├── core/              # Build engine
│   ├── tui/               # Terminal UI
│   └── gui/               # Web GUI
│
├── templates/             # Typst templates
│   ├── core/              # Core rendering (parser, setup)
│   ├── module/            # Extension modules
│   └── templater.typ      # Template engine
│
├── content/               # Your document content
│   ├── 1/                 # Chapter 1
│   │   ├── 1.typ          # Page 1
│   │   ├── 2.typ          # Page 2
│   │   └── ...
│   ├── 2/                 # Chapter 2
│   └── ...
│
├── config/                # Configuration files
│   ├── metadata.json      # Document metadata
│   ├── constants.json     # Build constants
│   ├── hierarchy.json     # Chapter/page titles
│   ├── preface.typ        # Preface content
│   ├── snippets.typ       # Custom snippets
│   └── modules/           # Per-module configs
│
├── build/                 # Temporary build artifacts
├── docs/                  # Documentation
└── output.pdf             # Final compiled PDF
```

---

## Content Directory

The `content/` directory holds your document source files.

### Organization

```
content/
├── 1/           # Chapter folder (numeric name)
│   ├── 1.typ    # Page 1.1
│   ├── 2.typ    # Page 1.2
│   └── 3.typ    # Page 1.3
├── 2/           # Chapter 2
│   └── 1.typ    # Page 2.1
└── 3/           # Chapter 3
    ├── 1.typ
    └── 2.typ
```

### Naming Rules

| Element         | Format         | Example            |
| --------------- | -------------- | ------------------ |
| Chapter folders | Numeric        | `1/`, `2/`, `10/`  |
| Page files      | Numeric `.typ` | `1.typ`, `2.5.typ` |

> [!TIP]
> Use decimal names like `1.5.typ` to insert pages between existing ones.

---

## Config Directory

The `config/` directory contains JSON and Typst configuration files.

| File             | Purpose                     |
| ---------------- | --------------------------- |
| `metadata.json`  | Title, authors, affiliation |
| `constants.json` | Theme, display options      |
| `hierarchy.json` | Chapter/page titles for TOC |
| `modules.json`   | Module installation state   |
| `preface.typ`    | Preface Typst content       |
| `snippets.typ`   | Custom Typst definitions    |
| `modules/*.json` | Per-module configuration    |

### Example: metadata.json

```json
{
  "title": "Linear Algebra Notes",
  "subtitle": "Spring 2024",
  "authors": ["Dr. Jane Smith"],
  "affiliation": "MIT",
  "logo": "assets/logo.png"
}
```

### Example: constants.json

```json
{
  "display-mode": "ocean",
  "display-cover": true,
  "display-outline": true
}
```

---

## Templates Directory

The `templates/` directory contains the Typst rendering engine.

```
templates/
├── core/
│   ├── parser.typ      # Main entry point for compilation
│   ├── setup.typ       # Document setup and imports
│   ├── render.typ      # Content rendering
│   └── cover/          # Cover page templates
│
├── module/
│   ├── core/           # Built-in modules (blocks, outline)
│   ├── canvas/         # Drawing module
│   ├── graph/          # Plotting module
│   ├── geometry/       # Geometry constructions
│   └── ...
│
└── templater.typ       # Template engine utilities
```

> [!NOTE]
> Generally, you don't need to modify files in `templates/`. Use `config/` for customization.

---

## Python Package

The `noteworthy/` package contains the build system.

```
noteworthy/
├── __main__.py       # CLI entry point
├── config.py         # Path constants
├── utils.py          # Shared utilities
│
├── core/
│   ├── build.py          # Compilation logic
│   ├── build_manager.py  # Parallel build orchestration
│   ├── deps.py           # Dependency checking
│   ├── pm.py             # Package manager for modules
│   └── modules.py        # Module imports generation
│
├── tui/
│   ├── app.py        # TUI application
│   ├── base.py       # Base UI components
│   ├── menus.py      # Menu screens
│   └── wizards/      # Setup wizards
│
└── gui/
    ├── app.py        # GUI launcher
    ├── server.py     # FastAPI backend
    ├── document_hub.py  # Real-time sync
    └── static/       # Web frontend
```

---

## Next Steps

- [Content Authoring →](../guides/content-authoring.md)
- [Configuration Reference →](../reference/config-files.md)
