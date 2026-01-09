# Typst Layer

Deep dive into the `templates/` Typst architecture.

## Overview

The Typst layer handles:

- Document rendering
- Theme application
- Module functionality
- Content transformation

---

## Directory Structure

```
templates/
├── core/
│   ├── parser.typ        # Main entry point
│   ├── setup.typ         # Document setup
│   ├── render.typ        # Content rendering
│   └── cover/
│       ├── cover.typ
│       ├── chapter-cover.typ
│       ├── page-title.typ
│       └── preface.typ
│
├── module/
│   ├── core/             # Built-in modules
│   ├── canvas/           # Drawing
│   ├── graph/            # Plotting
│   ├── geometry/         # Constructions
│   ├── dsa/              # Data structures
│   ├── trees/            # Trees
│   ├── layout/           # Layouts
│   └── ...
│
├── schemes/
│   └── data/             # Theme JSON files
│
├── systemconfig/         # Internal config
│
└── templater.typ         # User import
```

---

## Core Components

### parser.typ

The main compilation entry point.

**Responsibilities:**
- Set up document context
- Load configuration
- Import modules
- Render chapters and pages

**Simplified structure:**

```typst
#import "setup.typ": document-setup, active-theme
#import "render.typ": render-pages

// Apply document setup
#show: document-setup.with(
  title: metadata.title,
  theme: active-theme
)

// Render content
#render-pages(hierarchy, content-map)
```

### setup.typ

Document configuration and styling.

**Responsibilities:**
- Page size and margins
- Font configuration
- Header/footer templates
- Theme loading

```typst
#let document-setup(title: "", theme: (:), body) = {
  set page(
    paper: "a4",
    margin: (top: 2.5cm, bottom: 2.5cm, left: 2cm, right: 2cm),
    header: make-header(title, theme),
    footer: make-footer(theme)
  )
  
  set text(font: "Linux Libertine", size: 11pt)
  set heading(numbering: "1.1")
  
  body
}
```

### render.typ

Content rendering logic.

**Responsibilities:**
- Chapter iteration
- Page rendering
- Cover insertion
- TOC generation

### templater.typ

The user-facing import file.

```typst
// Re-export all public modules
#import "module/core/blocks/mod.typ": *
#import "module/canvas/mod.typ": *
#import "module/graph/mod.typ": *
#import "module/geometry/mod.typ": *
#import "module/dsa/mod.typ": *
#import "module/trees/mod.typ": *
// ...
```

---

## Module System

### Module Structure

Each module follows this pattern:

```
module/<name>/
├── mod.typ           # Public API
├── src/
│   ├── impl.typ      # Implementation  
│   └── helpers.typ   # Internal utilities
├── blueprint.json    # Config schema (optional)
└── examples.typ      # Usage examples
```

### Separation of Concerns

**mod.typ (Public API):**
- Exports public functions
- Injects active theme
- Handles configuration

**impl.typ (Implementation):**
- Pure functions
- Theme parameter (no globals)
- No side effects

### Example: Canvas Module

**mod.typ:**
```typst
#import "src/impl.typ": _point, _vector, _segment
#import "../core/setup.typ": active-theme

#let point(..args) = _point(..args, theme: active-theme)
#let vector(..args) = _vector(..args, theme: active-theme)
#let segment(..args) = _segment(..args, theme: active-theme)
```

**src/impl.typ:**
```typst
#let _point(pos, label: none, style: (:), theme: (:)) = {
  let fill = theme.at("point-fill", default: blue)
  let radius = 0.08
  
  circle(pos, radius: radius, fill: fill)
  if label != none {
    content(pos, anchor: "south", label)
  }
}
```

---

## Theme System

### Theme Files

Located in `templates/schemes/data/`:

```json
{
  "page-fill": "#1e1e2e",
  "text-main": "#cdd6f4",
  "text-accent": "#89b4fa",
  "heading-fill": "#313244",
  "block-stroke": "#45475a"
}
```

### Theme Loading

Themes are loaded by setup.typ:

```typst
#let load-theme(name) = {
  let path = "../schemes/data/" + name + ".json"
  json(path)
}

#let active-theme = load-theme(constants.display-mode)
```

### Using Themes

Always use `.at()` with defaults:

```typst
// Good
let color = theme.at("text-accent", default: blue)

// Bad (will break on missing key)
let color = theme.text-accent
```

---

## Configuration Integration

### Reading Config Files

```typst
#let metadata = json("../../config/metadata.json")
#let constants = json("../../config/constants.json")
#let hierarchy = json("../../config/hierarchy.json")
```

### Input Flags

Python passes data via CLI:

```bash
typst compile parser.typ --input chapter-folders='["1","2"]'
```

Access in Typst:

```typst
#let chapter-folders = json.decode(sys.inputs.at("chapter-folders", default: "[]"))
```

---

## Import Paths

Content files import from relative paths:

```typst
// From content/1/1.typ
#import "../../templates/templater.typ": *
```

Depth matters:
- `content/1/1.typ` → `../../templates/`
- `content/1/sub/1.typ` → `../../../templates/`

---

## Best Practices

1. **Theme-aware** — Never hardcode colors
2. **Pure implementations** — Keep impl.typ side-effect free
3. **Defaults everywhere** — Use `.at(key, default: value)`
4. **Consistent structure** — Follow module pattern
5. **Document exports** — Only public functions in mod.typ

---

## See Also

- [Architecture Overview](overview.md)
- [Templates Reference](../reference/templates.md)
- [Modules Guide](../guides/modules.md)
