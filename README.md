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

## What is Noteworthy?

**Noteworthy** is not just a template—it's a comprehensive **framework** for building educational textbooks, lecture notes, and technical documentation with Typst. It provides a complete ecosystem of tools, themes, and components that work together seamlessly.

An example project is available at https://github.com/sihooleebd/math-noteworthy. 

### Framework Components

- **Theme System**: 13+ pre-built color schemes with easy customization
- **Content Block Library**: Pre-styled components for definitions, theorems, examples, proofs, and solutions
- **Plotting Engine**: Advanced 2D/3D plotting, vector diagrams, and geometric constructions
- **Document Structure**: Automated table of contents, chapter covers, and page headers
- **Configuration Layer**: Centralized `config.typ` for complete control
- **Build System**: Incremental compilation with automatic PDF merging

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
- **Python 3** with **tqdm**: `pip3 install tqdm` (for progress bars during build)
- **Poppler** (provides `pdfinfo` for page counting):
  - macOS: `brew install poppler`
  - Linux: `apt-get install poppler-utils`
- **PDF Tool** (for merging and metadata):
  - **Option 1** (recommended): `brew install pdftk-java` (macOS) or `apt-get install pdftk` (Linux)
  - **Option 2** (fallback): Ghostscript is usually pre-installed on macOS/Linux
  
> **Note**: `pdftk-java` is required for adding PDF metadata (title, author) and clickable bookmarks/outline that appear in the PDF viewer sidebar for easy navigation.

### Installation

```bash
git clone https://github.com/yourusername/noteworthy.git
cd noteworthy
```

### Build Your Document

```bash
# Standard build (generates output.pdf)
python3 build.py

# Keep individual chapter PDFs as archive
python3 build.py --leave-individual
```

### Single File Compilation

```bash
# Compile entire document
typst compile main.typ output.pdf

# Compile specific section
typst compile renderer.typ --input target=01.01 section.pdf
```

## Document Structure

This repository includes comprehensive examples of all framework features:

```
noteworthy/
├── config.typ              # Framework configuration
├── build.py                # Build system
├── content/                # Example content
│   ├── chapter 01/         # Core Components
│   │   ├── 01.01.typ       # Content Blocks (definition, theorem, proof, etc.)
│   │   └── 01.02.typ       # Layout Elements (equations, solutions)
│   ├── chapter 02/         # Plotting & Geometry
│   │   ├── 02.01.typ       # Basic Plots (rect-plot, polar-plot)
│   │   ├── 02.02.typ       # Geometry (points, polygons)
│   │   ├── 02.03.typ       # Vectors (components, addition, projection)
│   │   └── 02.04.typ       # 3D Space Plots
│   └── chapter 03/         # Data & Visualization
│       ├── 03.01.typ       # Function Graphs
│       ├── 03.02.typ       # Combinatorics Diagrams
│       └── 03.03.typ       # Tables
└── templates/              # Framework core
    ├── parser.typ          # Document orchestration
    ├── templater.typ       # Component exports
    ├── default-schemes.typ # Theme definitions
    ├── covers/             # Cover page generators
    ├── layouts/            # Content blocks & outline
    └── plots/              # Plotting modules
```

## Documentation

Complete documentation is available in the [Wiki](../../wiki):

- [Getting Started](../../wiki/Getting-Started) - Installation and quick start
- [Configuration](../../wiki/Configuration) - Configure your document
- [Content Blocks](../../wiki/Content-Blocks) - Available content blocks
- [Plotting Reference](../../wiki/Plotting-Reference) - Complete plotting API
- [Themes](../../wiki/Themes) - Theme customization
- [Build System](../../wiki/Build-System) - Build script usage
- [Advanced Usage](../../wiki/Advanced-Usage) - Extending the framework
- [Troubleshooting](../../wiki/Troubleshooting) - Common issues

The [content/](content/) directory contains working examples for every feature.

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
