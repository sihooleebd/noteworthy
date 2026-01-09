# Configuration Files

Reference for all JSON configuration files in the `config/` directory.

## Overview

| File             | Purpose                              |
| ---------------- | ------------------------------------ |
| `metadata.json`  | Document title, authors, affiliation |
| `constants.json` | Theme, display options               |
| `hierarchy.json` | Chapter/page structure               |
| `snippets.typ`   | Custom Typst macros                  |
| `preface.typ`    | Preface content                      |
| `modules/*.json` | Per-module settings                  |

---

## metadata.json

Document metadata displayed on cover and in PDF properties.

### Schema

```json
{
  "title": "string",
  "subtitle": "string",
  "authors": ["string"],
  "affiliation": "string",
  "logo": "string (path)"
}
```

### Example

```json
{
  "title": "Linear Algebra",
  "subtitle": "Lecture Notes - Spring 2024",
  "authors": ["Dr. Jane Smith", "Prof. John Doe"],
  "affiliation": "MIT Mathematics",
  "logo": "assets/logo.png"
}
```

### Fields

| Field         | Type   | Description              |
| ------------- | ------ | ------------------------ |
| `title`       | string | Document title           |
| `subtitle`    | string | Subtitle or edition      |
| `authors`     | array  | List of author names     |
| `affiliation` | string | Organization/institution |
| `logo`        | string | Path to logo image       |

---

## constants.json

Global display and build settings.

### Schema

```json
{
  "display-mode": "string",
  "display-cover": "boolean",
  "display-chap-cover": "boolean",
  "display-outline": "boolean"
}
```

### Example

```json
{
  "display-mode": "catppuccin-mocha",
  "display-cover": true,
  "display-chap-cover": true,
  "display-outline": true
}
```

### Fields

| Field                | Type    | Default     | Description                |
| -------------------- | ------- | ----------- | -------------------------- |
| `display-mode`       | string  | `"default"` | Active theme name          |
| `display-cover`      | boolean | `true`      | Show document cover        |
| `display-chap-cover` | boolean | `true`      | Show chapter covers        |
| `display-outline`    | boolean | `true`      | Generate table of contents |

---

## hierarchy.json

Defines the document structure with chapter and page titles.

### Schema

```json
[
  {
    "title": "string",
    "pages": [
      {
        "title": "string"
      }
    ]
  }
]
```

### Example

```json
[
  {
    "title": "Introduction",
    "pages": [
      { "title": "What is Linear Algebra?" },
      { "title": "Prerequisites" }
    ]
  },
  {
    "title": "Vectors",
    "pages": [
      { "title": "Vector Spaces" },
      { "title": "Linear Independence" },
      { "title": "Basis and Dimension" }
    ]
  }
]
```

### Structure

- Array of chapter objects
- Each chapter has `title` and `pages` array
- Each page has `title`
- Order matches `content/` folder structure

> [!NOTE]
> The hierarchy must match the files in `content/`. Use the TUI sync wizard to detect mismatches.

---

## snippets.typ

Custom Typst macros available throughout your document.

### Format

```typst
#let myabbr = [Abbreviation]
#let myfunc(x) = { x * 2 }
#let myblock(body) = block(fill: blue.lighten(80%), body)
```

### Usage

After definition, use anywhere:

```typst
This uses #myabbr in text.
The result is #myfunc(5).
#myblock[Custom content]
```

---

## preface.typ

The preface content shown after the cover page.

### Format

Standard Typst content:

```typst
= Preface

This document covers the fundamental concepts of linear algebra...

== Acknowledgments

Thanks to...
```

---

## modules/*.json

Per-module configuration files created when you customize module settings.

### Location

```
config/modules/
├── canvas.json
├── graph.json
└── blocks.json
```

### Schema

Defined by each module's `blueprint.json`:

```json
{
  "setting-key": "value",
  "another-setting": true
}
```

### Example: canvas.json

```json
{
  "default-grid": true,
  "grid-color": "#cccccc",
  "point-size": 0.08
}
```

### Example: blocks.json

```json
{
  "block-design": "modern",
  "show-numbers": true
}
```

---

## Validation

Noteworthy Studio validates settings against module blueprints. Invalid values are rejected with error messages.

---

## File Locations

| File           | Path                         |
| -------------- | ---------------------------- |
| metadata.json  | `config/metadata.json`       |
| constants.json | `config/constants.json`      |
| hierarchy.json | `config/hierarchy.json`      |
| snippets.typ   | `config/snippets.typ`        |
| preface.typ    | `config/preface.typ`         |
| Module configs | `config/modules/<name>.json` |

---

## See Also

- [Project Structure](../getting-started/project-structure.md)
- [Theming Guide](../guides/theming.md)
