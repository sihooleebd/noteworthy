# Modules

Noteworthy's functionality is extended through **modules** — reusable Typst libraries for drawing, plotting, data structures, and more.

## Built-in Modules

These modules are included with every Noteworthy installation:

| Module      | Description                                                  | Documentation                  |
| ----------- | ------------------------------------------------------------ | ------------------------------ |
| **blocks**  | Educational content blocks (definitions, theorems, examples) | [Others](../modules/others.md) |
| **outline** | Table of contents and navigation                             | [Layout](../modules/layout.md) |
| **cover**   | Cover pages and chapter headers                              | [Layout](../modules/layout.md) |

## Extension Modules

Additional modules can be installed from [noteworthy-modules](https://github.com/sihooleebd/noteworthy-modules):

| Module            | Description                                | Documentation                      |
| ----------------- | ------------------------------------------ | ---------------------------------- |
| **canvas**        | Drawing primitives (points, lines, shapes) | [Canvas](../modules/canvas.md)     |
| **graph**         | Function plotting and calculus             | [Graph](../modules/graph.md)       |
| **geometry**      | Geometric constructions                    | [Geometry](../modules/geometry.md) |
| **dsa**           | Data structures and algorithms             | [DSA](../modules/dsa.md)           |
| **trees**         | Tree visualizations                        | [Trees](../modules/trees.md)       |
| **combinatorics** | Permutations and combinations              | [Others](../modules/others.md)     |

---

## Installing Modules

### From noteworthy-modules

```bash
# Clone the modules repository
git clone https://github.com/sihooleebd/noteworthy-modules

# Copy desired modules to your project
cp -r noteworthy-modules/canvas templates/module/
```

### Via GUI

1. Open the GUI: `noteworthy -g`
2. Navigate to **Settings → Modules**
3. Click **Install** next to the desired module

---

## Using Modules

Modules are automatically available after the templater import:

```typst
#import "../../templates/templater.typ": *

// Canvas module
#canvas({
  point((0, 0), label: "Origin")
  vector((0, 0), (3, 2), label: "v")
})

// Graph module  
#plot-graph({
  plot-func(x => calc.sin(x), domain: (-pi, pi))
})

// Blocks module
#definition("Vector Space")[
  A set V with operations...
]
```

---

## Module Configuration

Many modules have configurable options. Configuration is stored in `config/modules/<module>.json`.

### Via GUI

1. Open **Settings → Module Settings**
2. Select a module
3. Adjust settings
4. Changes are saved automatically

### Via JSON

Edit `config/modules/<module>.json`:

```json
{
  "default-grid": true,
  "axis-color": "#888888",
  "point-size": 0.08
}
```

### Blueprint Schema

Each module defines its configuration schema in `blueprint.json`:

```json
{
  "settings": [
    {
      "key": "default-grid",
      "label": "Show Grid by Default",
      "type": "boolean",
      "default": true
    },
    {
      "key": "point-size",
      "label": "Point Radius",
      "type": "number",
      "default": 0.08,
      "min": 0.01,
      "max": 0.5
    }
  ]
}
```

---

## Creating Custom Modules

See the [Templates Reference](../reference/templates.md) for details on module structure.

Basic structure:

```
templates/module/mymodule/
├── mod.typ           # Public API
├── src/
│   └── impl.typ      # Implementation
├── blueprint.json    # Configuration schema (optional)
└── examples.typ      # Usage examples
```

---

## Next Steps

- [Canvas Module →](../modules/canvas.md)
- [Graph Module →](../modules/graph.md)
- [Templates Reference →](../reference/templates.md)
