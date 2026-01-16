# Templates Reference

Understanding the Typst template system in `templates/`.

## Overview

The `templates/` directory contains the core Typst rendering engine. It provides:

- Document structure (parser, setup)
- Module system (canvas, graph, geometry)
- Theme integration
- Cover and layout components

---

## Directory Structure

```
templates/
├── core/                    # Core rendering
│   ├── parser.typ           # Main compilation entry
│   ├── setup.typ            # Document setup
│   ├── render.typ           # Content rendering
│   └── cover/               # Cover templates
│       ├── cover.typ        # Document cover
│       ├── chapter-cover.typ
│       ├── page-title.typ
│       └── preface.typ
│
├── module/                  # Extension modules
│   ├── core/                # Built-in modules
│   │   ├── blocks/          # Educational blocks
│   │   ├── outline/         # Table of contents
│   │   └── cover/           # Cover utilities
│   │
│   ├── canvas/              # Drawing primitives
│   ├── graph/               # Function plotting
│   ├── geometry/            # Geometric constructions
│   ├── dsa/                 # Data structures
│   ├── trees/               # Tree visualizations
│   ├── layout/              # Layout utilities
│   └── ...
│
├── schemes/                 # Theme definitions
│   └── data/                # Theme JSON files
│
├── systemconfig/            # Internal configuration
│
└── templater.typ            # Main import file
```

---

## Core Components

### parser.typ

The main entry point for Typst compilation.

```typst
// Simplified structure
#import "setup.typ": *
#import "render.typ": render-content

#show: setup.with(theme: active-theme)
#render-content(chapters, pages)
```

### setup.typ

Document setup and global configuration:

- Page size and margins
- Font configuration
- Theme application
- Header/footer setup

### render.typ

Content rendering logic:

- Chapter/page iteration
- Cover insertion
- Outline generation

### templater.typ

The user-facing import file:

```typst
#import "module/core/blocks/mod.typ": *
#import "module/canvas/mod.typ": *
#import "module/graph/mod.typ": *
// ... all public modules
```

Usage in content files:

```typst
#import "../../templates/templater.typ": *
```

---

## Module Structure

Each module follows a standard structure:

```
module/<name>/
├── mod.typ              # Public API
├── metadata.json        # Module info (required)
├── src/
│   ├── impl.typ         # Implementation
│   └── helpers.typ      # Internal helpers
├── blueprint.json       # Configuration schema (optional)
└── examples.typ         # Usage examples
```

### metadata.json (Required)

Defines module identity and dependencies:

```json
{
  "name": "mymodule",
  "description": "Short description of the module",
  "dependencies": ["shape"],
  "exports": ["myfunction", "myother"]
}
```

| Field          | Required | Description                             |
| -------------- | -------- | --------------------------------------- |
| `name`         | ✅        | Module identifier (matches folder name) |
| `description`  | ✅        | Human-readable description              |
| `dependencies` | ❌        | Required modules (auto-installed)       |
| `exports`      | ❌        | List of exported symbols                |

### mod.typ (Public API)

Exports public functions with theme injection:

```typst
#import "src/impl.typ": _point, _vector

#let active-theme = /* loaded from config */

#let point(..args) = _point(..args, theme: active-theme)
#let vector(..args) = _vector(..args, theme: active-theme)
```

### impl.typ (Implementation)

Pure implementation with theme parameter:

```typst
#let _point(pos, label: none, style: (:), theme: (:)) = {
  let color = theme.at("point-fill", default: blue)
  // ... implementation
}
```

> [!IMPORTANT]
> Implementation files never hardcode colors. Always use `theme.at("key", default: fallback)`.

### blueprint.json (Configuration)

Defines configurable options:

```json
{
  "settings": [
    {
      "key": "default-grid",
      "label": "Show Grid by Default",
      "type": "boolean",
      "default": true
    }
  ]
}
```

---

## Theme Integration

### Theme Structure

Themes are JSON files in `templates/schemes/data/`:

```json
{
  "page-fill": "#1e1e2e",
  "text-main": "#cdd6f4",
  "text-accent": "#89b4fa"
}
```

### Using Theme Colors

In implementations:

```typst
#let my-func(content, theme: (:)) = {
  let bg = theme.at("page-fill", default: white)
  let fg = theme.at("text-main", default: black)
  
  block(fill: bg, text(fill: fg, content))
}
```

---

## Creating a Module

### 1. Create Structure

```bash
mkdir -p templates/module/mymodule/src
```

### 2. Write Implementation

`templates/module/mymodule/src/impl.typ`:

```typst
#let _my-function(content, theme: (:)) = {
  let color = theme.at("text-accent", default: blue)
  text(fill: color, weight: "bold", content)
}
```

### 3. Create Public API

`templates/module/mymodule/mod.typ`:

```typst
#import "src/impl.typ": _my-function
#import "../core/setup.typ": active-theme

#let my-function(content) = _my-function(content, theme: active-theme)
```

### 4. Export from templater

Add to `templates/templater.typ`:

```typst
#import "module/mymodule/mod.typ": *
```

### 5. (Optional) Add Configuration

`templates/module/mymodule/blueprint.json`:

```json
{
  "settings": [
    {
      "key": "my-option",
      "label": "My Option",
      "type": "boolean",
      "default": true
    }
  ]
}
```

---

## Best Practices

1. **Separation of concerns** — Keep impl.typ pure (no side effects)
2. **Theme-aware** — Never hardcode colors
3. **Defaults** — Always provide sensible defaults
4. **Documentation** — Include examples.typ
5. **Minimal exports** — Only export what users need

---

## See Also

- [Modules Guide](../guides/modules.md)
- [Theming Guide](../guides/theming.md)
- [Architecture Overview](../architecture/overview.md)
