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

Say hi to **Noteworthy**, an academic parser and framework for creating massive and complex documents in one go. It can be used for building educational textbooks, lecture notes, and technical documentation with Typst. It provides a complete ecosystem of tools, themes, and components that work together seamlessly.

An example project is available at https://github.com/sihooleebd/math-noteworthy. 

## Gallery

<p align="center">
  <img src="images/example-01.png" width="45%" alt="Cover Page"/>
  <img src="images/example-02.png" width="45%" alt="Table of Contents"/>
  <img src="images/example-03.png" width="45%" alt="Content Page"/>
  <img src="images/example-04.png" width="45%" alt="Another Content Page"/>
</p>

### Themes

<p align="center">
  <img src="images/themes/catppuccin-latte.png" width="30%" alt="Catppuccin Latte"/>
  <img src="images/themes/catppuccin-mocha.png" width="30%" alt="Catppuccin Mocha"/>
  <img src="images/themes/dracula.png" width="30%" alt="Dracula"/>
  <img src="images/themes/everforest.png" width="30%" alt="Everforest"/>
  <img src="images/themes/gruvbox.png" width="30%" alt="Gruvbox"/>
  <img src="images/themes/moonlight.png" width="30%" alt="Moonlight"/>
  <img src="images/themes/nord.png" width="30%" alt="Nord"/>
  <img src="images/themes/noteworthy-dark.png" width="30%" alt="Noteworthy Dark"/>
  <img src="images/themes/noteworthy-light.png" width="30%" alt="Noteworthy Light"/>
  <img src="images/themes/rose-pine.png" width="30%" alt="Rose Pine"/>
  <img src="images/themes/solarized-dark.png" width="30%" alt="Solarized Dark"/>
  <img src="images/themes/solarized-light.png" width="30%" alt="Solarized Light"/>
  <img src="images/themes/tokyo-night.png" width="30%" alt="Tokyo Night"/>
</p>

### Framework Components

- **Theme System**: 13+ pre-built color schemes with easy customization
- **Content Block Library**: Pre-styled components for definitions, theorems, examples, proofs, and solutions
- **Plotting Engine**: Advanced 2D/3D plotting, vector diagrams, and geometric constructions
- **Document Structure**: Automated table of contents, chapter covers, and page headers
- **Configuration Layer**: JSON-based settings in `templates/config/`
- **Build System**: Incremental compilation with automatic PDF merging
- **Interactive Editors**: TUI-based editors for config, hierarchy, schemes, and snippets

## Key Features

- **Theme-Driven Design**: Switch between 13+ themes instantly  
- **Modular Architecture**: Import only what you need
- **Rich Typography**: Beautiful math typesetting with custom snippets
- **Extensible**: Add custom blocks, themes, and plotting functions
- **Production-Ready**: Used for real educational materials
- **Incremental Build**: Compile sections individually, merge automatically

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
```

### Quickstart

Add the neccesary content for your project and run the build script. The setup wizard will guide you through configuration:

```bash
python3 noteworthy.py
```

The noteworthy system guides you through the initialization, the configuration, and the build. Upon first run, the template will load the necessary template files. 

<p align="center">
  <img src="images/wizard_demo.gif?v=2" width="70%" alt="Setup Wizard Demo"/>
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
  - Config Editor - Document settings (title, authors, theme, etc.)
  - Hierarchy Editor - Chapter/page structure with add/delete
  - Scheme Editor - Color themes with create/delete
  - Snippets Editor - Custom macros
  - Preface Editor - Preface content
- **Controls**: Arrow keys to navigate, Space to toggle, Enter to build, `q` to quit
- **Build Progress**: Real-time compilation status with Typst log toggle (`v`)
- **Template Integrity Check**: Verify that the template files are not corrupted and auto fix

#### Interface Preview

<p align="center">
  <strong>Main Menu & Editor Selection</strong><br>
  <img src="images/main.png" width="45%" />
  <img src="images/editor-select.png" width="45%" />
</p>

<p align="center">
  <strong>Editors</strong><br>
  <img src="images/hierarchy.png" width="45%" />
  <img src="images/scheme.png" width="45%" />
</p>

<p align="center">
  <img src="images/config.png" width="45%" />
  <img src="images/snippets.png" width="45%" />
</p>

<p align="center">
  <strong>Build Process</strong><br>
  <img src="images/build.png" width="45%" />
  <img src="images/building.png" width="45%" />
</p>

### Single File Compilation

```bash
# Compile specific section
typst compile templates/parser.typ --input target=01.01 section.pdf
```

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

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
