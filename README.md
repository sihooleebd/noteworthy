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



### Themes

You can generate a visual catalogue of all available themes (including block styles, typography, and plotting colors) by running:

```bash
cd images
typst compile theme_catalogue.typ --root ..
```

### Framework Components

- **Theme System**: 13+ pre-built color schemes with easy customization
- **Standard Library**: Extensive collection of modules (Math, Plotting, DSA) provided by [noteworthy-modules](https://github.com/sihooleebd/noteworthy-modules)
- **Document Structure**: Automated table of contents, chapter covers, and page headers
- **Configuration Layer**: JSON-based settings in `config/`
- **Build System**: Incremental compilation with automatic PDF merging
- **Interactive Editors**: TUI-based editors or **Web-based GUI** for real-time preview

## Key Features

- **Theme-Driven Design**: Switch between 13+ themes instantly  
- **Modular Architecture**: Import only what you need
- **Rich Typography**: Beautiful math typesetting with custom snippets
- **Extensible**: Add custom blocks, themes, and plotting functions
- **Production-Ready**: Used for real educational materials
- **Incremental Build**: Compile sections individually, merge automatically

## Interactive GUI & Collaboration

Noteworthy includes a powerful web-based interface for visual editing, configuration, and real-time collaboration.

### Features
- **Live Preview**: See your changes instantly as you type.
- **Visual Configuration**: Configure themes, layouts, and modules without editing JSON.
- **Real-time Collaboration**: Work with others on the same document simultaneously.
  - **Shared Cursors**: See where others are editing.
  - **Global Chat**: Communicate via the built-in encrypted chat.
  - **Conflict-Free**: File-scoped edits ensure data integrity.

### Running the GUI
```bash
python3 noteworthy.py --gui
```
The interface will be available at `http://localhost:8000`.

### Remote Collaboration via Ngrok
To collaborate with users over the internet (outside your LAN), we recommend using **ngrok**. This provides a secure, encrypted tunnel to your local instance.

1.  Start the Noteworthy GUI:
    ```bash
    python3 noteworthy.py --gui
    ```
2.  In a separate terminal, expose port 8000:
    ```bash
    ngrok http 8000
    ```
3.  Share the provided **HTTPS** URL (e.g., `https://xxxx-xx.ngrok-free.app`) with your collaborators.


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

You can force an update or switch branches using CLI flags. These flags work for both `noteworthy.py` and `noteworthy_cli.py`:

| Flag | Long Flag   | Description                                                                 |
| ---- | ----------- | --------------------------------------------------------------------------- |
| `-u` | `--update`  | Update noteworthy to the selected branch (default: master).                 |
| `-n` | `--nightly` | Select the `nightly` branch instead of `master`.                            |
| `-f` | `--force`   | **Destructive**. Force clean reinstall (removes existing `noteworthy` dir). |

**Examples:**
- `python3 noteworthy.py -u` (Update Master)
- `python3 noteworthy.py -u -n` (Update Nightly)
- `python3 noteworthy.py -u -f` (Force Clean Install Master)

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



#### TUI Build Menu Features
The build menu (`b` key from main menu or after setup) has been updated with a powerful grid interface:

- **Grid Layout**: Chapters are **Rows**, Pages are **Columns**.
- **Visuals**:
    - **Yellow Cursor**: Your current position.
    - **Cyan Crosshair**: Highlights the active row and column.
- **Navigation**:
    - **Arrow Keys**: Smart navigation that skips empty spaces and follows the PDF flow (Z-Pattern).
    - **vim-keys**: `h`, `j`, `k`, `l` also supported.
- **Selection**:
    - `Space`: Toggle current page.
    - `r`: Toggle entire Chapter (Row).
    - `c`: Toggle specific Page Index across all chapters (Column).
    - `a` / `n`: Select All / None.
- **Options**:
  - `d` - Debug mode
  - `f` - Toggle frontmatter
  - `p` - **Keep PDFs**: Don't delete individual chapter PDFs after merging.
  - `e` - Open configuration editors

#### Interface Preview



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
