> **CRITICAL SECURITY WARNING**
>
> **This is the ONLY official repository for Noteworthy.**
> Noteworthy does not relate to repos other than sihooleebd/noteworthy, sihooleebd/noteworthy-website, sihooleebd/noteworthy-modules (this list is live updated). 
> 
> We are aware of unauthorized clones of this repository being used to spread malware.
>
> - **We NEVER distribute executable files (e.g., .exe, .msi, .dmg).**
> - This project is released as **source code only**. If you downloaded a playable or runnable application claiming to be this project, **IT IS MALWARE**.
> - Please uninstall any such files immediately and scan your system.
> - Always verify that you are downloading from: `https://github.com/sihooleebd/noteworthy`.

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

**A powerful Typst framework for creating beautiful, themed educational documents.**

[![Typst](https://img.shields.io/badge/Typst-0.12%2B-239DAD?logo=typst)](https://typst.app/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Community-5865F2?logo=discord&logoColor=white)](https://discord.gg/W3S2UQCJzM)
[![Website](https://img.shields.io/badge/Website-noteworthy.benjaminlee.kr-purple)](https://noteworthy.benjaminlee.kr/)

Say hi to **Noteworthy**, an academic parser and framework for creating massive and complex documents in one go. It can be used for building educational textbooks, lecture notes, and technical documentation with Typst. It provides a complete ecosystem of tools, themes, and components that work together seamlessly.

An example project is available at https://github.com/sihooleebd/math-noteworthy. 

## Gallery

<p align="center">
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/example-01.png" width="45%" alt="Cover Page"/>
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/example-02.png" width="45%" alt="Table of Contents"/>
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/example-03.png" width="45%" alt="Content Page"/>
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/example-04.png" width="45%" alt="Another Content Page"/>
</p>

### Themes

[View the Theme Catalogue (PDF)](https://raw.githubusercontent.com/sihooleebd/noteworthy/media/theme-library.pdf)

### Framework Components

- **Theme System**: 13+ pre-built color schemes with easy customization
- **Content Block Library**: Pre-styled components for definitions, theorems, examples, proofs, and solutions
- **Plotting Engine**: Advanced 2D/3D plotting, vector diagrams, and geometric constructions
- **Document Structure**: Automated table of contents, chapter covers, and page headers
- **Configuration Layer**: JSON-based settings in `config/`
- **Build System**: Incremental compilation with automatic PDF merging
- **Interactive Editors**: TUI-based editors for config, hierarchy, schemes, and snippets

## Key Features

- **Theme-Driven Design**: Switch between 13+ themes instantly  
- **Modular Architecture**: Import only what you need
- **Rich Typography**: Beautiful math typesetting with custom snippets
- **Extensible**: Add custom blocks, themes, and plotting functions
- **Production-Ready**: Used for real educational materials
- **Incremental Build**: Compile sections individually, merge automatically

## Documentation

**[Go to Documentation Hub](./docs/HOME.md)**

## Quick Start

### Prerequisites

- **Typst** (v0.12.0+): [Install Typst](https://github.com/typst/typst#installation)
- **Python 3**: Required for the build system
- **Poppler** (provides `pdfinfo` for page counting):
  - macOS: `brew install poppler`
  - Linux: `apt-get install poppler-utils`
  - Windows: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases) and add to PATH
- **PDF Tool** (for merging and metadata):
  - macOS: `brew install pdftk-java`
  - Linux: `apt-get install pdftk`
  - Windows: Download from [pdftk releases](https://www.pdflabs.com/tools/pdftk-the-pdf-toolkit/)
  - *Fallback*: Ghostscript (usually pre-installed on macOS/Linux, [download for Windows](https://ghostscript.com/releases/gsdnld.html))
  
> **Note |** `pdftk` is required for adding PDF metadata (title, author) and clickable bookmarks/outline that appear in the PDF viewer sidebar for easy navigation.

### Installation

```bash
mkdir project
cd project
mkdir content
curl -O https://raw.githubusercontent.com/sihooleebd/noteworthy/master/noteworthy.py
python3 noteworthy.py
```

### Quickstart

Add the neccesary content for your project and run the build script. The setup wizard will guide you through configuration:

```bash
python3 noteworthy.py
```

### Advanced Usage

You can force an update or switch branches using CLI flags:

| Flag                     | Description                                                                                           |
| ------------------------ | ----------------------------------------------------------------------------------------------------- |
| `--load`                 | Force update/install from `master` branch.                                                            |
| `--load-nightly`         | Force update/install from `nightly` branch.                                                           |
| `--force-update`         | **Destructive**. Removes existing `noteworthy` and `templates` folders and reinstalls from `master`.  |
| `--force-update-nightly` | **Destructive**. Removes existing `noteworthy` and `templates` folders and reinstalls from `nightly`. |
| `--print-inputs`         | Output Typst `--input` flags for content folder info. Use with `typst compile`.                       |

The noteworthy system guides you through the initialization, the configuration, and the build. Upon first run, the template will load the necessary template files.

### CLI Builder (Lightweight)

For users who prefer a simpler, non-interactive build experience, use `noteworthy_cli.py`:

```bash
# Build the entire document
python3 noteworthy_cli.py

# Build specific chapters (0-indexed)
python3 noteworthy_cli.py -c 0 1 2

# Skip frontmatter (cover, preface, TOC)
python3 noteworthy_cli.py --no-frontmatter

# Debug mode with verbose output
python3 noteworthy_cli.py --debug
```

| Flag               | Description                                |
| ------------------ | ------------------------------------------ |
| `-c`, `--chapters` | Space-separated list of chapter indices    |
| `--no-frontmatter` | Skip cover, preface, and table of contents |
| `--leave-pdfs`     | Keep individual PDFs in build folder       |
| `--debug`          | Enable verbose debug logging               |
| `-t`, `--threads`  | Number of parallel compilation threads     |
| `--flags`          | Additional Typst CLI flags                 |

The CLI builder uses the same build engine as the TUI but runs non-interactively, making it ideal for CI/CD pipelines and scripted builds. 

<p align="center">
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/wizard_demo.gif" width="70%" alt="Setup Wizard Demo"/>
</p>

**TUI Features:**
- **Chapter Selection**: Toggle individual chapters/sections to compile
- **Options**:
  - `d` - Debug mode (verbose output)
  - `f` - Include/exclude frontmatter (cover, preface, outline)
  - `l` - Keep individual PDFs after merge
  - `c` - Configure custom Typst flags (e.g., `--font-path`)
  - `e` - Open configuration editors
- **Editor Menu** (`e` key):
  - Config Editor - Document settings (title, authors, theme, preface content, etc.)
  - Hierarchy Editor - Chapter/page structure with add/delete
  - Scheme Editor - Color themes with create/delete
  - Snippets Editor - Custom macros
  - Ignored Files - Manage files excluded from indexing
- **Controls**: Arrow keys to navigate, Space to toggle, Enter to build, `q` to quit
- **Build Progress**: Real-time compilation status with Typst log toggle (`v`)
- **Template Integrity Check**: Verify that the template files are not corrupted and auto fix
- **Backup & Restore**: Export and Import configuration files individually

#### Interface Preview

<p align="center">
  <strong>Main Menu & Editor Selection</strong><br>
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/main.png" width="45%" />
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/editor-select.png" width="45%" />
</p>

<p align="center">
  <strong>Editors</strong><br>
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/hierarchy.png" width="45%" />
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/scheme.png" width="45%" />
</p>

<p align="center">
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/config.png" width="45%" />
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/snippets.png" width="45%" />
</p>

<p align="center">
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/indexignore.png" width="45%" />
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/preface.png" width="45%" />
</p>

<p align="center">
  <strong>Build Process</strong><br>
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/build.png" width="45%" />
  <img src="https://github.com/sihooleebd/noteworthy/blob/media/building.png" width="45%" />
</p>

### Standalone/Single File Compilation

```bash
# Compile full document with folder info
eval "typst compile templates/core/parser.typ output.pdf --root . $(python3 noteworthy.py --print-inputs)"

# Compile specific section
typst compile templates/core/parser.typ section.pdf --root . --input target=0/0
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:
- [Typst](https://typst.app/) - The typesetting system
- [CeTZ](https://github.com/cetz-package/cetz) - Drawing library
- [CeTZ-Plot](https://github.com/cetz-package/cetz-plot) - Plotting extension

## Contact

Created by [Sihoo Lee](https://github.com/sihooleebd) & [Hojun Lee](https://github.com/R0K0R)

---

**Noteworthy** - *A framework for noteworthy educational documents.*
