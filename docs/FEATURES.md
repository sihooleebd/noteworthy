# Noteworthy Geometry & Plotting System - Feature Documentation

This document provides comprehensive documentation for all advanced features in the Noteworthy plotting and geometry system.

---

## Table of Contents

1. [Smart Labels](#smart-labels)
2. [Geometry Objects](#geometry-objects)
3. [Angle Rendering](#angle-rendering)
4. [Vector System](#vector-system)
5. [Function Plotting](#function-plotting)
6. [Calculus Visualization](#calculus-visualization)
7. [3D Space Plots](#3d-space-plots)
8. [Polar & Parametric Curves](#polar--parametric-curves)
9. [Label Offset System](#label-offset-system)
10. [Hierarchy Sync Wizard](#hierarchy-sync-wizard)

---

## Smart Labels

Labels support **intelligent substitution** using placeholder syntax. The system automatically calculates and inserts values.

### Available Placeholders

| Placeholder | Applies To          | Description                 |
| ----------- | ------------------- | --------------------------- |
| `{angle}`   | `angle`             | Calculated angle in degrees |
| `{length}`  | `segment`, `vector` | Euclidean length            |
| `{radius}`  | `circle`, `arc`     | Radius value                |
| `{area}`    | `circle`, `polygon` | Calculated area             |
| `{circum}`  | `circle`, `polygon` | Circumference/perimeter     |

### Example Usage

```typst
#let seg = segment(point(0, 0), point(3, 4), label: "Length: {length}")
// Renders as "Length: 5"

#let ang = angle(A, O, B, label: "{angle}")
// Renders as "45°" (or whatever the angle is)

#let circ = circle(point(0,0), 2, label: "Area = {area}")
// Renders as "Area = 12.57"
```

---

## Geometry Objects

All geometry primitives are defined as **object dictionaries** with a `type` field. Pass them to canvases for rendering.

### Point

```typst
#let P = point(x, y, label: none, style: auto)
#let P3D = point-3d(x, y, z, label: none, style: auto)
```

| Parameter     | Type         | Description                         |
| ------------- | ------------ | ----------------------------------- |
| `x`, `y`, `z` | `float`      | Coordinates                         |
| `label`       | `content`    | Optional label                      |
| `style`       | `dictionary` | Override `fill`, `stroke`, `radius` |

### Segment

```typst
#let seg = segment(p1, p2, label: none, style: auto)
```

Connects two points. Supports 3D points automatically.

### Line (Infinite)

```typst
#let L = line-through(p1, p2, style: auto)
```

Extends infinitely through two points, clipped to canvas bounds.

### Ray

```typst
#let R = ray(origin, through, style: auto)
```

Starts at `origin`, extends through `through` to infinity.

### Circle

```typst
#let C = circle(center, radius, label: none, fill: none, style: auto)
```

- **Label placement**: Labels appear at **45° on the circle edge**, not center
- **3D circles**: Discretized as 64-point polygons on XY plane

### Arc

```typst
#let A = arc(center, radius, start: 0deg, end: 90deg, style: auto)
```

### Polygon

```typst
#let poly = polygon(p1, p2, p3, ..., label: none, fill: none, style: auto)
```

Automatic closure. Supports 3D vertices.

---

## Angle Rendering

### Standard Angle

```typst
#let ang = angle(p1, vertex, p2, label: none, radius: 0.5, fill: auto, reflex: false, label-radius: auto)
```

| Parameter            | Type            | Description                                              |
| -------------------- | --------------- | -------------------------------------------------------- |
| `p1`, `vertex`, `p2` | `point`         | Three points defining the angle                          |
| `radius`             | `float`         | Arc radius for the marker                                |
| `fill`               | `color`         | Fill color (default: stroke color at 70% transparent)    |
| `reflex`             | `bool`/`"auto"` | `false`=CCW, `true`=CW, `"auto"`=smallest                |
| `label-radius`       | `float`         | Distance from vertex for label (default: `radius * 1.5`) |

### Right Angle Marker

```typst
#let ra = right-angle(p1, vertex, p2, radius: 0.3)
```

Draws a square corner marker.

### Reflex Mode

```typst
// Auto-select smallest angle
angle(A, O, B, reflex: "auto")

// Force reflex (>180°)
angle(A, O, B, reflex: true)
```

### Technical Notes

- Angles are calculated using `calc.atan2(dx, dy)` (Typst convention: x first)
- The arc is rendered as a **discretized 30-point polygon** for robustness
- CCW (counter-clockwise) order is enforced: angle sweeps from `p1` to `p2`

---

## Vector System

### Basic Vectors

```typst
#let v = vector(x, y, label: none, origin: (0, 0), style: auto)
#let v3 = vector-3d(x, y, z, label: none, origin: (0, 0, 0), style: auto)
```

| Parameter     | Type            | Description                                  |
| ------------- | --------------- | -------------------------------------------- |
| `x`, `y`, `z` | `float`         | Component magnitudes                         |
| `origin`      | `tuple`/`point` | **Starting point** of vector (bound vectors) |
| `label`       | `content`       | Label at vector midpoint                     |
| `style`       | `dictionary`    | `stroke`, `thickness`, `dash`                |

### Bound Vectors

The `origin` parameter allows **anchoring vectors** to specific points:

```typst
#let a = vector(3, 0, origin: (0, 0))       // Starts at origin
#let b-shifted = vector(1, 2, origin: (3, 0))  // Starts at (3, 0)
```

### Vector Operations

```typst
#let sum = vec-add(v1, v2)        // Returns new vector
#let proj = vec-project(v1, v2)   // Projection of v1 onto v2
#let scaled = vec-scale(v, 2.5)   // Scalar multiplication
#let mag = vec-magnitude(v)       // Length as float
#let unit = vec-normalize(v)      // Unit vector
```

### Dashed/Styled Vectors

```typst
#let dashed-vec = vector(2, 1,
  origin: (1, 1),
  style: (stroke: (dash: "dashed", paint: gray))
)
```

---

## Function Plotting

### Basic Function

```typst
#let f = graph(x => x*x - 2, domain: (-5, 5), label: $y = x^2 - 2$)
```

### Robust Function (Singularities)

For functions with singularities like `sin(π/x)`:

```typst
#let singular = robust-func(
  x => if x == 0 { 0 } else { calc.sin(calc.pi / x) },
  domain: (-0.5, 0.5),
  label: $sin(pi/x)$,
)
```

**Features:**
- Dense uniform sampling (2000 points)
- **Discontinuity detection**: Large jumps (Δy > 2.0) insert break markers
- **Segment rendering**: Line breaks at discontinuities (no false connections)

### Technical Implementation

The robust sampler returns points with `none` as break markers:
```
[(x1, y1), (x2, y2), none, (x3, y3), ...]
```

The renderer splits at `none` and draws separate segments.

---

## Calculus Visualization

The calculus module provides tools for visualizing derivatives, integrals, and discontinuities. All functions integrate seamlessly with the theme system and support automatic styling.

### Tangent Lines

Draw tangent lines to functions at specific points:

```typst
#let f(x) = x * x / 4 + 1
#let tangent-line = tangent(f, 2, length: 3, label: "Tangent")
```

| Parameter | Type     | Description                               |
| --------- | -------- | ----------------------------------------- |
| `f`       | function | The function to find tangent for          |
| `x`       | float    | x-coordinate where tangent is drawn       |
| `length`  | float    | Total length of tangent line (default: 2) |
| `label`   | content  | Optional label                            |
| `style`   | dict     | Style overrides (`stroke`, `dash`, etc.)  |

**Example:**

```typst
#cartesian-canvas(
  x-domain: (-1, 4),
  y-domain: (0, 6),
  graph(f, domain: (-1, 4), label: $f(x) = x^2/4 + 1$),
  tangent(f, 2, length: 3, style: (stroke: (paint: blue, dash: "dashed"))),
  point(2, f(2), label: $P(2, 2)$),
)
```

### Normal Lines

Draw normal (perpendicular) lines to function curves:

```typst
#let normal-line = normal(f, 2, length: 3, label: "Normal")
```

Parameters are identical to `tangent`. The normal is automatically perpendicular to the tangent at the given point.

**Special Cases:**
- **Horizontal tangents** (slope = 0): Normal is vertical
- **Vertical tangents** (slope → ∞): Handled via slope magnitude check

```typst
#cartesian-canvas(
  graph(f, domain: (-1, 4)),
  tangent(f, 2, length: 3, style: (stroke: blue)),
  normal(f, 2, length: 3, style: (stroke: red)),
)
```

### Discontinuit visualization (Holes)

Visualize removable discontinuities using **holes** - points where the function is undefined but has a limit.

#### Empty Holes (Removable Discontinuities)

```typst
#let f(x) = if x == 1 { 2 } else { (x*x - 1)/(x - 1) }

#cartesian-canvas(
  graph(f, domain: (-1, 3), hole: (1,), label: $f(x) = (x^2-1)/(x-1)$),
)
```

- **Appearance**: White-filled circle with function's stroke color
- **Size**: `radius: 0.08` (matches point size)
- **Placement**: At `(x, lim_{x→h} f(x))` - uses `f(x + 0.0001)` to approximate limit

#### Filled Holes (Point Discontinuities)

```typst
#cartesian-canvas(
  graph(f, domain: (-1, 3), filled-hole: (2,)),
)
```

- **Appearance**: Solid circle in function's color
- **Use case**: Show where function value differs from limit

**Multiple Holes:**

```typst
graph(f, 
  hole: (1, 3),           // Empty holes at x=1 and x=3
  filled-hole: (2,),      // Filled hole at x=2
)
```

### Riemann Sums (Integration Approximation)

Visualize area under curves using rectangular/trapezoidal approximations.

#### Basic Usage

```typst
#let f(x) = calc.sqrt(x) + 0.5
#let domain = (0.5, 3.5)

#cartesian-canvas(
  graph(f, domain: (0, 4)),
  riemann-sum(f, domain, 6, method: "left", label: "Left Sum"),
)
```

| Parameter | Type     | Description                                         |
| --------- | -------- | --------------------------------------------------- |
| `f`       | function | Function to integrate                               |
| `domain`  | tuple    | `(start, end)` integration bounds                   |
| `n`       | int      | Number of rectangles/trapezoids                     |
| `method`  | string   | `"left"`, `"right"`, `"midpoint"`, `"trapezoid"`    |
| `label`   | content  | Optional label (appears centered above sum)         |
| `style`   | dict     | Style overrides (ignored if using theme)            |
| `smooth`  | bool     | If `true`, hide interior strokes (default: `false`) |

#### Methods

1. **Left Riemann Sum** (`method: "left"`)
   - Rectangle height = `f(left edge)`
   - Typically **underestimates** for increasing functions

2. **Right Riemann Sum** (`method: "right"`)
   - Rectangle height = `f(right edge)`
   - Typically **overestimates** for increasing functions

3. **Midpoint Sum** (`method: "midpoint"`)
   - Rectangle height = `f(midpoint)`
   - Better approximation than left/right

4. **Trapezoid Sum** (`method: "trapezoid"`)
   - Uses trapezoids instead of rectangles
   - **Best approximation** among these methods
   - Area = average of left and right heights

#### Theme Integration

By default, Riemann sums use **theme highlight color at 30% opacity**:

```typst
// Automatic theme colors
riemann-sum(f, domain, 6, method: "left")
```

To override with custom colors:

```typst
riemann-sum(f, domain, 6, 
  method: "trapezoid",
  style: (
    fill: purple.transparentize(80%),
    stroke: purple,
  )
)
```

#### Smooth Integrals

For clean integral visualizations without interior lines, use `smooth: true`:

```typst
#cartesian-canvas(
  graph(f, domain: (0, 4)),
  riemann-sum(f, domain, 50, 
    method: "trapezoid", 
    label: "∫ f(x) dx",
    smooth: true,  // Hides interior vertical lines
  ),
)
```

**Effect**: Only the outline and filled area are visible, creating a smooth integral region.

#### Label Positioning

Labels automatically appear:
- **Horizontally**: Centered at `(start + end) / 2`
- **Vertically**: 5% above the tallest rectangle
- **Anchor**: `"center"` for proper alignment

**Example: Comparing Methods**

```typst
#let f(x) = calc.sqrt(x) + 0.5
#let domain = (0.5, 3.5)

// Left Sum
#cartesian-canvas(
  graph(f, domain: (0, 4)),
  riemann-sum(f, domain, 6, method: "left", label: "Left"),
)

// Right Sum
#cartesian-canvas(
  graph(f, domain: (0, 4)),
  riemann-sum(f, domain, 6, method: "right", label: "Right"),
)

// Midpoint Sum
#cartesian-canvas(
  graph(f, domain: (0, 4)),
  riemann-sum(f, domain, 6, method: "midpoint", label: "Midpoint"),
)

// Trapezoid Sum
#cartesian-canvas(
  graph(f, domain: (0, 4)),
  riemann-sum(f, domain, 6, method: "trapezoid", label: "Trapezoid"),
)

// Smooth Integral (many trapezoids)
#cartesian-canvas(
  graph(f, domain: (0, 4)),
  riemann-sum(f, domain, 50, method: "trapezoid", 
    label: "∫ f(x) dx", 
    smooth: true
  ),
)
```

### Implementation Details

#### Derivative Calculation

Tangent/normal slopes use **symmetric difference quotient**:

```typst
m = (f(x + h) - f(x - h)) / (2h)  // h = 1e-5
```

More accurate than forward/backward differences.

#### Hole Rendering

Holes are drawn using `plot.annotate`:

```typst
plot.annotate({
  circle((x, y), radius: 0.08, fill: white, stroke: func-stroke)
})
```

This ensures they appear **on top** of the function line.

#### Riemann Sum Rendering

Each rectangle/trapezoid is a `polygon` object:

```typst
// Rectangle
polygon(point(x0, 0), point(x0, h), point(x1, h), point(x1, 0))

// Trapezoid
polygon(point(x0, 0), point(x0, y0), point(x1, y1), point(x1, 0))
```

The `smooth` mode suppresses interior strokes by setting edge polygons to `stroke: none`.

---

## 3D Space Plots

### Space Canvas

```typst
#space-canvas(
  view: (x: -90deg, y: -70deg, z: 0deg),
  // ... 3D objects
)
```

### 3D Primitives

All 2D objects have 3D counterparts:

```typst
point-3d(x, y, z, label: "P")
vector-3d(2, 0, 0, origin: (0, 0, 0), label: $x$, style: (stroke: red))
segment-3d(p1, p2)  // If p1/p2 have z components
```

### Axis Vectors

```typst
#space-canvas(
  view: (x: -90deg, y: -70deg, z: 0deg),
  vector-3d(2, 0, 0, label: $x$, style: (stroke: red)),
  vector-3d(0, 2, 0, label: $y$, style: (stroke: green)),
  vector-3d(0, 0, 2, label: $z$, style: (stroke: blue)),
)
```

---

## Polar & Parametric Curves

### Polar Curves

```typst
#let cardioid = polar-func(
  t => 1 + calc.cos(t),  // r as function of θ
  domain: (0, 2 * calc.pi),
  label: "Cardioid",
)

#polar-canvas(cardioid)
```

### Parametric Curves

```typst
#let spiral = parametric(
  t => (t * calc.cos(t), t * calc.sin(t)),  // (x, y) as function of t
  domain: (0, 4 * calc.pi),
  samples: 500,
)
```

---

## Label Offset System

All labels are automatically positioned to **avoid overlapping lines**.

### Vector/Segment Labels

Labels are offset **perpendicular to the line** (0.25-0.3 units):

```
    label
      ↑ 0.3 units perpendicular
──────●──────→
   midpoint
```

### Function Labels

Labels are placed at **75% of the domain** with tangent-perpendicular offset:

```typst
// Label appears at x = 0.75 * (x_max - x_min) + x_min
// Offset perpendicular to curve tangent
```

### Circle Labels

Labels appear at **45° on the circle edge** (not center).

### White Background

All labels have `fill: white` to mask underlying lines:

```typst
content(pos, label, fill: white, stroke: none, padding: 0.1)
```

---

## Hierarchy Sync Wizard

The TUI sync wizard handles discrepancies between `hierarchy.json` and the filesystem.

### Context-Sensitive Options

| Condition               | Available Options                                           |
| ----------------------- | ----------------------------------------------------------- |
| Files missing from disk | **[A]** Create Missing Files, **[R]** Remove from Hierarchy |
| New files on disk       | **[B]** Add to Hierarchy, **[I]** Ignore New Files          |

### Option Details

| Key   | Action                | Description                                                      |
| ----- | --------------------- | ---------------------------------------------------------------- |
| **A** | Create Missing Files  | Creates scaffold `.typ` files for hierarchy entries              |
| **B** | Add to Hierarchy      | Adds new files, **preserving existing metadata** (title, number) |
| **R** | Remove from Hierarchy | Removes entries without corresponding files                      |
| **I** | Ignore New Files      | Adds files to `.indexignore`                                     |

### Numbering Preservation

When adding files to hierarchy, existing page metadata is preserved:

```python
if j < len(old_pages):
    pages.append(old_pages[j].copy())  # Preserves 'number', 'title', etc.
else:
    pages.append({'title': 'Untitled Section'})
```

---

## Canvas Types Reference

| Canvas             | Use Case                                | Axes                   |
| ------------------ | --------------------------------------- | ---------------------- |
| `blank-canvas`     | Raw geometry, no axes                   | None                   |
| `cartesian-canvas` | Functions, standard 2D plots            | X/Y Cartesian          |
| `polar-canvas`     | Polar functions                         | Radial + Angular       |
| `space-canvas`     | 3D objects                              | X/Y/Z with perspective |
| `combi-plot`       | Combinatorics (boxes, linear, circular) | Custom                 |

---

## Style Reference

### Stroke Styles

```typst
style: (stroke: red)
style: (stroke: (paint: blue, thickness: 2pt))
style: (stroke: (dash: "dashed", paint: gray))
style: (stroke: (dash: "dotted", thickness: 1pt))
```

### Fill Styles

```typst
fill: red.transparentize(50%)
fill: gradient.linear(red, blue)
```

---

## Troubleshooting

### Variable Shadowing in Labels

**Problem**: Label shows dictionary content instead of symbol

**Cause**: Variable name shadows math symbol

```typst
#let sum = vec-add(a, b)      // 'sum' shadows $sum$
#let obj = vector(..., label: $sum$)  // Prints dictionary!
```

**Fix**: Rename variable

```typst
#let vec-sum = vec-add(a, b)  // No shadow
```

### Angle Orientation Issues

**Problem**: Angle marker appears rotated 90°

**Cause**: Using `calc.atan2(dy, dx)` instead of Typst's `calc.atan2(dx, dy)`

**Fix**: Already corrected in codebase

---

*Documentation generated for Noteworthy v1.0*
*Last updated: December 24, 2024*
