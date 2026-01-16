# Modules

Noteworthy's functionality is extended through **modules** — reusable Typst libraries for drawing, plotting, data structures, and more.

## Module Types

| Type       | Location                 | Description                                                                           |
| ---------- | ------------------------ | ------------------------------------------------------------------------------------- |
| **Core**   | `templates/module/core/` | Required system modules (block, cover)                                                |
| **Remote** | `templates/module/`      | Installed from [noteworthy-modules](https://github.com/sihooleebd/noteworthy-modules) |
| **Local**  | `templates/module/`      | User-created custom modules                                                           |

---

## Available Modules

### Core Modules (Always Installed)

| Module    | Description                                                      |
| --------- | ---------------------------------------------------------------- |
| **block** | Semantic content blocks: definitions, theorems, proofs, examples |
| **cover** | Document covers and title pages                                  |

### Extension Modules

| Module       | Description                                           | Dependencies |
| ------------ | ----------------------------------------------------- | ------------ |
| **canvas**   | Drawing primitives and coordinate systems             | shape        |
| **graph**    | Function plotting and calculus                        | —            |
| **shape**    | 2D geometric primitives                               | —            |
| **dsa**      | Data structures: linked lists, stacks, queues, graphs | —            |
| **trees**    | Tree visualizations for hierarchical data             | —            |
| **combi**    | Combinatorics: permutations, combinations             | —            |
| **timeline** | Vertical and horizontal timelines                     | —            |
| **data**     | Data visualization: tables, series, curves            | —            |
| **layout**   | Page layouts and document configuration               | —            |

---

## Installing Modules

### Via Noteworthy Studio (GUI)

1. Open Noteworthy Studio: `noteworthy -g`
2. Navigate to **Settings → Modules**
3. Scroll to **Available from Remote**
4. Click **Install** on desired module
5. Dependencies are installed automatically

### Via API

```bash
curl -X POST http://localhost:9001/api/modules/install \
  -H "Content-Type: application/json" \
  -d '{"modules": ["canvas"]}'
```

> [!NOTE]
> Dependencies are **automatically resolved and installed**. Installing `canvas` will also install `shape`.

### Syncing with Remote

Click **Sync** in the Modules tab to refresh the list of available modules from the repository.

---

## Module Status

Modules have three possible status values:

| Status      | Import Style     | Description                                           |
| ----------- | ---------------- | ----------------------------------------------------- |
| `disabled`  | Not imported     | Module installed but not loaded                       |
| `qualified` | `#import mod`    | Functions accessed via namespace (e.g., `mod.func()`) |
| `global`    | `#import mod: *` | Functions available globally (e.g., `func()`)         |

Core modules are always `global`. Remote modules default to `qualified` when installed.

---

## Dependency Resolution

When installing modules, dependencies are **automatically resolved**:

1. Dependencies are identified from `metadata.json`
2. Topological sort ensures correct install order
3. Dependencies are installed first
4. **Cycles are detected and logged** (but don't prevent installation)

```
Installing canvas...
→ Resolved dependency: shape
→ Installing shape (1/2)...
→ Installing canvas (2/2)...
```

> [!IMPORTANT]
> Dependencies are **force-installed** regardless of manual selection. You cannot install a module without its dependencies.

---

## Using Modules

After installation, modules are imported via the templater:

```typst
#import "../../templates/templater.typ": *

// Canvas module (qualified import)
#canvas.point((0, 0), label: "Origin")
#canvas.vector((0, 0), (3, 2))

// Block module (global import - core)
#definition("Vector Space")[
  A set V with operations...
]

#theorem("Basis Theorem")[
  Every vector space has a basis.
]
```

---

## Configuration

### Module Settings

Many modules have configurable options stored in `config/modules/<module>.json`:

```json
{
  "default-grid": true,
  "point-size": 0.08
}
```

Configure via:
- **GUI**: Settings → Modules → click settings icon
- **Direct edit**: Modify `config/modules/<name>.json`

### Blueprint Schema

Each module defines its settings in `blueprint.json`:

```json
{
  "settings": [
    {
      "key": "default-grid",
      "label": "Show Grid",
      "type": "boolean",
      "default": true
    }
  ]
}
```

---

## Creating Custom Modules

### Structure

```
templates/module/mymodule/
├── mod.typ           # Public API (required)
├── metadata.json     # Module info (required)
├── blueprint.json    # Settings schema (optional)
└── src/
    └── impl.typ      # Implementation
```

### metadata.json

```json
{
  "name": "mymodule",
  "description": "My custom module",
  "dependencies": ["shape"],
  "exports": ["myfunction"]
}
```

### Fields

| Field          | Required | Description                             |
| -------------- | -------- | --------------------------------------- |
| `name`         | ✅        | Module identifier (matches folder name) |
| `description`  | ✅        | Human-readable description              |
| `dependencies` | ❌        | List of required modules                |
| `exports`      | ❌        | List of exported symbols                |

---

## modules.json

Module state is tracked in `config/modules.json`. See [Config Files Reference](../reference/config-files.md#modulesjson) for schema.

---

## Next Steps

- [Canvas Module →](../modules/canvas.md)
- [Graph Module →](../modules/graph.md)
- [Config Files Reference →](../reference/config-files.md)
