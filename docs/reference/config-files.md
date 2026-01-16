# Configuration Files

Reference for all JSON configuration files in the `config/` directory.

## Overview

| File             | Purpose                              |
| ---------------- | ------------------------------------ |
| `metadata.json`  | Document title, authors, affiliation |
| `constants.json` | Theme, display options               |
| `hierarchy.json` | Chapter/page structure               |
| `modules.json`   | Module installation state            |
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

## modules.json

Tracks installed modules, their status, and synchronization metadata.

### Schema

```json
{
  "meta": {
    "commit": "string",
    "last_sync": "ISO timestamp",
    "repo_commit": "string"
  },
  "modules": {
    "<name>": {
      "status": "disabled | qualified | global",
      "source": "remote | local | orphaned",
      "sha": "string | null"
    }
  },
  "core_modules": {
    "<name>": {
      "status": "global",
      "source": "core",
      "sha": "string"
    }
  },
  "local_modules": {
    "<name>": {
      "status": "disabled | qualified | global"
    }
  }
}
```

### Example

```json
{
  "meta": {
    "last_sync": "2026-01-17T01:54:43.221056",
    "repo_commit": "ddac077e8f47492c988fc606d9fa69d13c1f9022"
  },
  "modules": {
    "canvas": { "status": "qualified", "source": "remote", "sha": "46070a7..." },
    "shape": { "status": "qualified", "source": "remote", "sha": "fbc023a..." },
    "graph": { "status": "disabled", "source": "remote", "sha": null }
  },
  "core_modules": {
    "block": { "status": "global", "source": "core", "sha": "ecbac60..." },
    "cover": { "status": "global", "source": "core", "sha": "218ba52..." }
  },
  "local_modules": {}
}
```

### Sections

| Section         | Description                          |
| --------------- | ------------------------------------ |
| `meta`          | Sync timestamps and repository state |
| `modules`       | Remote extension modules             |
| `core_modules`  | Required system modules              |
| `local_modules` | User-created custom modules          |

### Module Fields

| Field    | Required        | Values                                | Description               |
| -------- | --------------- | ------------------------------------- | ------------------------- |
| `status` | ✅               | `disabled`, `qualified`, `global`     | Import style              |
| `source` | ✅               | `remote`, `local`, `core`, `orphaned` | Origin of module          |
| `sha`    | For remote/core | Git tree SHA                          | Used for update detection |

### Status Values

| Status      | Import           | Description                      |
| ----------- | ---------------- | -------------------------------- |
| `disabled`  | None             | Not loaded at all                |
| `qualified` | `#import mod`    | Namespaced access (`mod.func()`) |
| `global`    | `#import mod: *` | Global access (`func()`)         |

> [!NOTE]
> The `sha` field tracks the git tree hash for update detection. If `sha` differs from the remote repository, an update is available.

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
