# Noteworthy Plotting System

A unified object-oriented engine for 2D geometry, vectors, calculus, and 3D space.

## Canvas Types

Select the appropriate canvas for your needs:

| Canvas             | Use Case                     | Axes                   |
| :----------------- | :--------------------------- | :--------------------- |
| `cartesian-canvas` | Functions, standard 2D plots | X/Y Cartesian          |
| `polar-canvas`     | Polar functions              | Radial + Angular       |
| `space-canvas`     | 3D objects                   | X/Y/Z with perspective |
| `blank-canvas`     | Raw geometry, no axes        | None                   |
| `combi-plot`       | Combinatorics diagrams       | Custom                 |

---

## 2D Geometry

Primitives are defined as objects and passed to the canvas.

### Objects

```typst
// Point
point(x, y, label: "P", label-anchor: "south", label-distance: 0.3)

// Segment & Line
segment(p1, p2, label: "Segment", label-anchor: "north")
line-through(p1, p2, style: (stroke: dashed))
ray(origin, through)

// Shapes
circle(center, radius, label: "C", label-anchor: "south-west")
polygon(p1, p2, p3, label: "△", label-anchor: "center")
arc(center, p1, p2)  // Arc from p1 to p2
semicircle(center, start-point)
regular-polygon(center, first-vertex, n)
point-at-angle(center, angle, radius, from: p, label-anchor: "east")

// Curves
curve-through((0,0), (1,1), (2,0), label: "Linear")
smooth-curve((0,0), (1,1), (2,0), label: "Spline")
```

### Curve Types

*   **`curve-through`**: Connects points with **straight line segments** (Polyline). Best for technical diagrams or raw data paths.
*   **`smooth-curve`**: Connects points with a **smooth Catmull-Rom spline**. Best for natural paths and flow diagrams. `smooth-curve` accepts an optional `tension` parameter (default: 0.0) to control the spline curvature.

### Angles

```typst
// Standard Angle (automatically chooses < 180°)
angle(A, O, B, label: "{angle}") 

// Reflex Angle (> 180°)
angle(A, O, B, label: "{angle}", reflex: true)

// Right Angle Marker
right-angle(A, O, B)
```

**Note**: Angles use `calc.atan2` and default to the smallest angle (reflex: "auto").

### Smart Labels

Labels support intelligent substitution. Values are automatically calculated based on the geometry.

| Placeholder | Applies To          | Description              |
| :---------- | :------------------ | :----------------------- |
| `{angle}`   | `angle`             | Angle value (e.g. "45°") |
| `{length}`  | `segment`, `vector` | Length of line           |
| `{radius}`  | `circle`, `arc`     | Radius value             |
| `{area}`    | `circle`, `polygon` | Area                     |
| `{circum}`  | `circle`, `polygon` | Circumference            |

### Label Positioning

All geometry objects support precise label positioning:

| Parameter        | Type   | Default    | Description                             |
| ---------------- | ------ | ---------- | --------------------------------------- |
| `label-anchor`   | string | `"north"`  | Which edge of label box is at the point |
| `label-distance` | float  | `0.15-0.2` | Offset distance in coordinate units     |

**Anchor values**: `"north"`, `"south"`, `"east"`, `"west"`, `"north-east"`, `"north-west"`, `"south-east"`, `"south-west"`, `"center"`

```typst
// Label below the point, 0.4 units away
point(0, 0, label: "O", label-anchor: "south", label-distance: 0.4)

// Label to the right of the circle
circle(O, radius: 2, label: $C$, label-anchor: "west")
```

---

## Vector System

Vectors support automatic labeling and operations with **global smart label positioning**.

### Constructors

```typst
// Free Vector
vector(3, 2, label: $v$)

// Bound Vector (starts at specific point)
vector(1, 1, origin: (2, 0), label: $u$)

// 3D Vector
vector-3d(1, 2, 3, label: $w$)
```

### Operations

`vec-add` and `vec-project` return **arrays** containing the result vector and helplines objects. Pass them alongside the original vectors for smart labeling:

```typst
#let a = vector(3, 0, label: $arrow(a)$)
#let b = vector(1, 2, label: $arrow(b)$)

#blank-canvas(
  a,
  b,
  vec-add(a, b, label: $arrow(a)+arrow(b)$),
)
```

Other operations:
```typst
#let v-unit = vec-normalize(u)
#let mag = vec-magnitude(u)
#let dot = vec-dot(u, v)
```

### Smart Label Positioning

The canvas automatically applies **angular span labeling** to all vectors:

- **Span < 180°**: Leftmost vector gets CCW perpendicular label, rightmost gets CW perpendicular (both on "outside")
- **Span ≥ 180°**: Labels placed directly on the vector with a background hole

This prevents label overlap and keeps diagrams clear.

### Visual Helpers

`vec-add` and `vec-project` include auxiliary lines by default (dotted gray parallelogram sides or projection lines). Pass `helplines: false` to disable them.

---

## Function Plotting

### Basic & Robust

```typst
// Standard Function
graph(x => x*x, domain: (-2, 2))

// Robust (handles singularities automatically)
robust-func(x => 1/x, domain: (-5, 5))
```

### Calculus Visualization

Visualize derivatives and integrals seamlessly.

```typst
// Tangent Line
tangent(f, x0, length: 3)

// Normal Line
normal(f, x0, length: 3)

// Riemann Sums (Area approximation)
riemann-sum(f, domain, 6, method: "left", label: "Left Sum")
// Methods: "left", "right", "midpoint", "trapezoid"
```

---

## Data Visualization

### CSV Data Series

Import data from CSV files. Supports relative paths from your content file.

```typst
// In your content file:
#let my-data = csv-series(
  read("../data/results.csv"),  // Read file content
  x-col: 0,                     // Column index for X
  y-col: 1,                     // Column index for Y
  label: "Experiment 1"
)

#cartesian-canvas(
  x-domain: (0, 10),
  y-domain: (0, 100),
  my-data
)
```

---

## 3D Space

Render 3D points, vectors, and lines with automatic perspective.

```typst
#space-canvas(
  view: (x: -90deg, y: -70deg, z: 0deg), // Camera angle
  point-3d(1, 2, 3, label: "P"),
  vector-3d(0, 0, 5, label: $z$),
  segment-3d(p1, p2)
)
```

**Note**: 3D points are rendered as spherical billboards (always circular facing camera) for better aesthetics.
