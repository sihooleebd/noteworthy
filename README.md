# Noteworthy

**A powerful Typst framework for creating beautiful, themed educational documents.**

[![Typst](https://img.shields.io/badge/Typst-0.12%2B-239DAD?logo=typst)](https://typst.app/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## What is Noteworthy?

**Noteworthy** is not just a template—it's a comprehensive **framework** for building educational textbooks, lecture notes, and technical documentation with Typst. It provides a complete ecosystem of tools, themes, and components that work together seamlessly.

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
- **PDF Merge Tool** (optional, for multi-chapter documents):
  - macOS: `brew install poppler` (provides `pdfunite`)
  - Linux: `apt-get install poppler-utils`

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
├── renderer.typ            # Document processor
├── main.typ                # Full document entry
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

## Build System

The `build.py` script provides powerful incremental compilation:

### Features

- **Incremental Compilation**: Compiles cover, preface, TOC, and each chapter/section separately
- **Automatic Merging**: Uses `pdfunite` or `ghostscript` to merge individual PDFs
- **Auto Cleanup**: Removes temporary build files after successful compilation
- **Archive Option**: Optionally preserve individual PDFs as a zip file

### Usage

```bash
# Standard build
python3 build.py
# Output: output.pdf (merged document)
# Build directory automatically cleaned up

# Preserve individual PDFs
python3 build.py --leave-individual
# Output: output.pdf + build_pdfs.zip (15 individual PDFs)
```

### Build Process

1. Extracts document structure from `config.typ`
2. Compiles components in order:
   - Cover page
   - Preface
   - Table of contents
   - For each chapter:
     - Chapter cover
     - Chapter sections (01.01, 01.02, etc.)
3. Merges all PDFs using `pdfunite` (or `ghostscript` as fallback)
4. Cleans up build directory (unless `--leave-individual` specified)

## Usage Example

```typst
#import "templates/templater.typ": *

= Vectors

#definition("Vector")[
  A *vector* is a quantity with both magnitude and direction.
]

#example("Calculate Magnitude")[
  Find $|vec(v)|$ where $vec(v) = angle.l 3, 4 angle.r$.
]

#solution[
  Using the Pythagorean theorem:
  $ |vec(v)| = sqrt(3^2 + 4^2) = sqrt(25) = 5 $
]

// Visualize the vector
#combi-plot({
  draw-vec((0, 0), (3, 4), label: $vec(v)$)
  draw-vec-comps((3, 4), label-x: "3", label-y: "4")
})
```

## Available Themes

- `rose-pine` (default) - Warm, cozy aesthetic
- `nord` - Cool Nordic palette
- `dracula` - Vivid purple theme
- `gruvbox` - Retro warm palette
- `tokyo-night` - Neon night theme
- `catppuccin-mocha` / `catppuccin-latte`
- `solarized-dark` / `solarized-light`
- `everforest` - Natural green theme
- `moonlight` - Deep blue theme
- `dark` / `light` / `print`

Change theme in `config.typ`:
```typst
#let display-mode = "nord"  // Switch theme here
```

## Example Content

The included examples demonstrate every framework feature:

### Content Blocks
- `definition`, `theorem`, `proof`, `example`, `solution`, `note`, `notation`, `analysis`, `equation`

### Plotting Functions
- **Basic**: `rect-plot`, `polar-plot`, `combi-plot`, `space-plot`
- **Geometry**: `point`, `add-polygon`, `add-angle`, `add-right-angle`, `add-xy-axes`
- **Vectors**: `draw-vec`, `draw-vec-comps`, `draw-vec-sum`, `draw-vec-proj`
- **Graphs**: `plot-function` (Cartesian, parametric, polar)
- **Combinatorics**: `draw-boxes`, `draw-linear`, `draw-circular`
- **Tables**: `table-plot`, `compact-table`, `value-table`, `grid-table`

## Customization

### Configure Your Document

Edit `config.typ`:

```typst
#let title = "My Textbook"
#let authors = ("Your Name",)
#let affiliation = "Your Institution"
#let display-mode = "nord"

// Customize labels
#let chapter-name = "Chapter"
#let solutions-text = "Solutions"

// Define document structure
#let hierarchy = (
  (
    title: "Introduction",
    summary: "Getting started...",
    pages: (
      (id: "01.01", title: "Section 1"),
      (id: "01.02", title: "Section 2"),
    ),
  ),
  // Add more chapters...
)
```

### Add Custom Themes

```typst
#let scheme-custom = (
  page-fill: rgb("#1a1b26"),
  text-main: rgb("#c0caf5"),
  text-heading: rgb("#7aa2f7"),
  text-accent: rgb("#bb9af7"),
  text-muted: rgb("#565f89"),
  plot: (
    stroke: rgb("#7dcfff"),
    highlight: rgb("#bb9af7"),
    grid: rgb("#414868"),
  ),
  blocks: (
    definition: (fill: rgb("#283457"), stroke: rgb("#7aa2f7")),
    // ... more blocks
  ),
)
```

## Documentation

For complete reference and advanced usage:
- [DOCUMENTATION.md](DOCUMENTATION.md) - Complete framework reference
- [content/](content/) - Working examples for every feature

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

Created by [Sihoo Lee](https://github.com/sihooleebd)

---

**Noteworthy** - *A framework for noteworthy educational documents.*
