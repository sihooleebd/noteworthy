# Noteworthy Framework Documentation

Complete guide to using the Noteworthy framework for educational document creation.

## Table of Contents

1. [Framework Overview](#framework-overview)
2. [Configuration](#configuration)
3. [Content Block System](#content-block-system)
4. [Plotting Engine](#plotting-engine)
5. [Helper Functions Reference](#helper-functions-reference)
6. [Theme System](#theme-system)
7. [Advanced Framework Usage](#advanced-framework-usage)

---

## Framework Overview

Noteworthy is a **modular framework** for creating educational documents in Typst. Unlike traditional templates, Noteworthy provides:

- **Component Library**: Reusable blocks, plots, and layouts
- **Theme Engine**: Centralized theming with 13+ presets
- **Document Parser**: Automated structure generation
- **Plotting Framework**: Integrated 2D/3D visualization
- **Configuration Layer**: Single source of truth for settings

---

## Helper Functions Reference

### 📐 Geometry Module (`geoplot`)

#### `point`
Draws a labeled point in 2D or 3D.

```typst
#rect-plot({
  point((1, 2), "A", pos: "north")
  point((3, 1), "B", color: red)
})
```

#### `add-polygon`
Draws a polygon with optional fill and label.

```typst
#rect-plot({
  add-polygon(((0,0), (2,0), (1,2)), fill: blue.transparentize(80%), label: "Tri")
})
```

#### `add-angle`
Draws an angle arc between two rays.

```typst
#rect-plot({
  add-angle((0,0), 0deg, 45deg, $alpha$, radius: 1)
})
```

#### `add-right-angle`
Draws a right angle marker.

```typst
#rect-plot({
  add-right-angle((0,0), 0deg, radius: 0.3)
})
```

#### `add-xy-axes`
Draws a rotated local coordinate system.

```typst
#rect-plot({
  add-xy-axes(30deg, scale: 2)
})
```

### ↗️ Vector Module (`vectorplot`)

#### `draw-vec`
Draws a vector arrow from start to end.

```typst
#combi-plot({
  draw-vec((0,0), (2,3), label: $vec(v)$)
})
```

#### `draw-vec-comps`
Visualizes vector components (dashed lines).

```typst
#combi-plot({
  draw-vec-comps((2,3), label-x: "2", label-y: "3")
})
```

#### `draw-vec-sum`
Visualizes vector addition (parallelogram or tip-to-tail).

```typst
#combi-plot({
  draw-vec-sum((2,0), (1,2), mode: "parallelogram")
})
```

#### `draw-vec-proj`
Visualizes vector projection of `vec-a` onto `vec-b`.

```typst
#combi-plot({
  draw-vec-proj(vec-a: (2,3), vec-b: (4,0))
})
```

### 🧊 Space Module (`spaceplot`)

#### `space-plot`
Creates a 3D coordinate system.

```typst
#space-plot(
  view: (x: -70deg, z: 30deg),
  {
    draw-vec((0,0,0), (1,2,3), label: $vec(v)$)
  }
)
```

### 📈 Grapher Module (`grapher`)

#### `plot-function`
Plots mathematical functions.

```typst
#rect-plot({
  // Standard y = f(x)
  plot-function(x => x*x, type: "y=x")
  
  // Parametric (x(t), y(t))
  plot-function(t => (calc.cos(t), calc.sin(t)), type: "parametric")
  
  // Polar r(theta)
  plot-function(t => 1 + calc.cos(t), type: "polar")
})
```

### 📊 Plots Module (`plots`)

#### `rect-plot`
Standard 2D Cartesian plot with axes.

```typst
#rect-plot(
  x-domain: (-5, 5),
  y-domain: (-5, 5),
  {
    point((0,0), "O")
  }
)
```

#### `polar-plot`
Polar coordinate plot.

```typst
#polar-plot(
  radius: 5,
  {
    add-polar(t => 2 * calc.sin(3*t))
  }
)
```

#### `combi-plot`
Blank canvas for custom diagrams (no axes).

```typst
#combi-plot({
  draw-boxes(3, (1, 2, 1))
})
```

### 🎲 Combinatorics Module (`combiplot`)

#### `draw-boxes`
Draws boxes with balls (stars and bars).

```typst
#combi-plot({
  draw-boxes(3, (2, 1, 3)) // 3 boxes with 2, 1, 3 items
})
```

#### `draw-linear`
Draws items arranged linearly.

```typst
#combi-plot({
  draw-linear(("A", "B", "C"))
})
```

#### `draw-circular`
Draws items arranged in a circle.

```typst
#combi-plot({
  draw-circular(("A", "B", "C", "D"), radius: 2)
})
```

### 📅 Table Module (`tableplot`)

#### `table-plot`
Creates a themed table.

```typst
#table-plot(
  headers: ("Name", "Value"),
  data: (
    ("A", "10"),
    ("B", "20"),
  )
)
```

---

## Theme System

### Theme Structure

Each theme defines:

```typst
#let scheme-custom = (
  page-fill: color,      // Background
  text-main: color,      // Body text
  text-heading: color,   // Headings
  text-muted: color,     // Secondary text
  text-accent: color,    // Highlights
  blocks: (
    definition: (fill: color, stroke: color, title: "Definition"),
    theorem: (fill: color, stroke: color, title: "Theorem"),
    // ... more block types
  ),
  plot: (
    stroke: color,       // Plot lines
    highlight: color,    // Accent color
    grid: color,         // Grid lines
    bg: color/none,      // Background
  ),
)
```

### Creating Custom Themes

1. Define theme in `config.typ`
2. Add to `colorschemes` dictionary
3. Use with `#let display-mode = "your-theme"`

---

## Advanced Framework Usage

### Extending Block Types

Create custom blocks in `templates/layouts/blocks.typ`:

```typst
#let create-lemma = create-block.with((
  fill: rgb("#2a2a3e"),
  stroke: rgb("#ff79c6"),
  title: "Lemma",
))
```

Export in `templater.typ`:

```typst
#let lemma = blocks.create-lemma.with(active-theme.blocks.lemma)
```

### Custom Plotting Functions

Add to `templates/plots/`:

```typst
#let my-custom-plot(...) = {
  cetz.canvas({
    // Your drawing logic
  })
}
```

### Conditional Content

```typst
#if show-solution [
  This appears only when solutions are enabled.
]
```

### Custom Math Snippets

Define in `config.typ`:

```typst
#let ve c(x) = $arrow(#x)$
#let R = $bb(R)$
```

---

## Framework Philosophy

Noteworthy follows these principles:

1. **Modularity**: Use only what you need
2. **Consistency**: Unified theming across all components
3. **Extensibility**: Easy to add custom components
4. **Simplicity**: Configuration over code
5. **Beauty**: Professional aesthetics by default

---

## Tips & Best Practices

1. **Start Simple**: Use default theme and blocks first
2. **Organize Content**: Follow the chapter/section structure
3. **Use Named Parameters**: Makes code clearer
4. **Preview Often**: Use `typst watch` for live updates
5. **Extend Gradually**: Add custom features as needed

---

## Troubleshooting

**Issue:** Compilation errors after theme change  
**Solution:** Clear cache: `typst compile --clear-cache`

**Issue:** Plot doesn't render  
**Solution:** Ensure plot function is in correct environment (`rect-plot`, `combi-plot`, etc.)

**Issue:** Custom block doesn't appear  
**Solution:** Check it's exported in `templater.typ` and defined in theme

---

## Framework Updates

To update Noteworthy:

```bash
cd noteworthy
git pull origin main
```

Check the changelog for breaking changes.

---

**Noteworthy Framework** - Version 1.0  
Built for educational excellence with Typst.
