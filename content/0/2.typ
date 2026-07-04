#import "../../templates/templater.typ": *

= File Structure

Understanding the project layout helps you navigate and extend Noteworthy.

== Project Root

#notation("Directory Legend")[
  - 📁 = Directory
  - 📄 = File
]

```
noteworthy/
├── 📁 config/          # Configuration files
│   ├── hierarchy.json  # Chapter/page structure
│   ├── metadata.json   # Title, authors, etc.
│   ├── constants.json  # Display settings
│   └── schemes/        # Color themes
├── 📁 content/         # Your document pages
│   ├── 0/, 1/, 2/...   # Chapter folders
│   └── images/         # Embedded images
├── 📁 templates/       # The template system
│   ├── templater.typ   # Main entry point
│   ├── core/           # Core utilities
│   └── module/         # Feature modules
└── output.pdf          # Compiled document
```

== Templates Directory

The `templates/` folder contains the template system:

#definition("templater.typ")[
  The single entry point that re-exports all modules. Content files only need to import this one file.
]

#definition("core/")[
  Core utilities shared across all modules:
  - `setup.typ` — Configuration loading and theme definition
  - `scheme.typ` — Color scheme management
  - `parser.typ` — Content parsing for builds
  - `scanner.typ` — Content discovery
]

#definition("module/")[
  Feature modules, each in its own folder with a `mod.typ` entry point:
  - `block/` — Content blocks
  - `geometry/` — 2D primitives
  - `canvas/` — Plotting canvases
  - `data/` — Tables and data
  - `cover/` — Document covers
  - `layout/` — Page layouts
]

== Module Pattern

Each module follows the same pattern:

#example("Module Structure")[
  ```
  module/block/
  ├── mod.typ      # Entry point (exports themed wrappers)
  └── block.typ    # Implementation
  ```

  The `mod.typ` file imports the implementation, applies theming, and exports ready-to-use functions.
]


#import "../../templates/templater.typ": *

= File Structure

Understanding the project layout helps you navigate and extend Noteworthy.

== Project Root

#notation("Directory Legend")[
  - 📁 = Directory
  - 📄 = File
]

```
noteworthy/
├── 📁 config/          # Configuration files
│   ├── hierarchy.json  # Chapter/page structure
│   ├── metadata.json   # Title, authors, etc.
│   ├── constants.json  # Display settings
│   └── schemes/        # Color themes
├── 📁 content/         # Your document pages
│   ├── 0/, 1/, 2/...   # Chapter folders
│   └── images/         # Embedded images
├── 📁 templates/       # The template system
│   ├── templater.typ   # Main entry point
│   ├── core/           # Core utilities
│   └── module/         # Feature modules
└── output.pdf          # Compiled document
```

== Templates Directory

The `templates/` folder contains the template system:

#definition("templater.typ")[
  The single entry point that re-exports all modules. Content files only need to import this one file.
]

#definition("core/")[
  Core utilities shared across all modules:
  - `setup.typ` — Configuration loading and theme definition
  - `scheme.typ` — Color scheme management
  - `parser.typ` — Content parsing for builds
  - `scanner.typ` — Content discovery
]

#definition("module/")[
  Feature modules, each in its own folder with a `mod.typ` entry point:
  - `block/` — Content blocks
  - `geometry/` — 2D primitives
  - `canvas/` — Plotting canvases
  - `data/` — Tables and data
  - `cover/` — Document covers
  - `layout/` — Page layouts
]

== Module Pattern

Each module follows the same pattern:

#example("Module Structure")[
  ```
  module/block/
  ├── mod.typ      # Entry point (exports themed wrappers)
  └── block.typ    # Implementation
  ```

  The `mod.typ` file imports the implementation, applies theming, and exports ready-to-use functions.
]


