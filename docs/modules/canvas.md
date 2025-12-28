# Canvas Module

The `canvas` module is the core drawing engine of Noteworthy. It provides a set of themed canvas environments and drawing primitives that integrate seamlessly with the project's styling system.

## Import

```typst
#import "../../templates/templater.typ": *
```


## Canvas Types

The module provides several specialized canvas wrappers around `cetz.canvas`. All canvases automatically apply the active theme's colors and settings.

### `cartesian-canvas`
Standard Cartesian coordinate system with grid lines.
```typst
#cartesian-canvas(
  x: (-5, 5), // X-axis domain
  y: (-5, 5), // Y-axis domain
  // ... other cetz args
)[
  // Drawing commands
]
```

### `polar-canvas`
Polar coordinate system with radial grid.
```typst
#polar-canvas(
  radius: (0, 5),
  angle: (0deg, 360deg),
)[
  // Drawing commands
]
```

### `space-canvas`
3D Cartesian coordinate system.
```typst
#space-canvas(
  x: (-5, 5),
  y: (-5, 5),
  z: (-5, 5),
)[
  // Drawing commands
]
```
- **3D Points**: Render as true circles (screen-space) without perspective distortion
- **3D Vectors**: Labels use pill-style backgrounds centered on vectors

### `blank-canvas`
An empty canvas with no axes or grid, suitable for free-form diagrams or custom visualizations.
```typst
#blank-canvas(
  length: 1cm,
)[
  // Drawing commands
]
```

### `graph-canvas` & `trig-canvas`
Specialized variants of `cartesian-canvas` optimized for function plotting and trigonometric functions respectively.

## Drawing Primitives

The module exports a comprehensive set of drawing functions (`draw-*`) that handle styling, labeling, and coordinate mapping automatically.

### Basic Geometry

#### `draw-point`
Draws a point with an optional label.
```typst
#draw-point(
  (x: 1, y: 2, label: "P"), // Geometry object
  theme: active-theme
)
```

#### `draw-segment`
Draws a line segment between two points.
```typst
#draw-segment(
  (
    p1: (x: 0, y: 0), 
    p2: (x: 3, y: 4), 
    label: "d",
    style: (stroke: 2pt)
  ),
  theme: active-theme
)
```

#### `draw-line-infinite`
Draws a line passing through two points, clipped to the canvas bounds.
```typst
#draw-line-infinite(
  (p1: (x:0, y:0), p2: (x:1, y:1)),
  theme: active-theme,
  bounds: (x: (-5, 5), y: (-5, 5))
)
```

#### `draw-ray`
Draws a ray starting from an origin and passing through a point.
```typst
#draw-ray(
  (origin: (x:0, y:0), through: (x:1, y:1)),
  theme: active-theme,
  bounds: ...
)
```

#### `draw-circle-obj`
Draws a circle defined by center and radius.
```typst
#draw-circle-obj(
  (center: (x:0, y:0), radius: 2, label: "C"),
  theme: active-theme
)
```

#### `draw-arc`
Draws an arc.
```typst
#draw-arc(
  (center: (x:0, y:0), radius: 2, start: 0deg, end: 90deg),
  theme: active-theme
)
```

#### `draw-polygon-obj`
Draws a closed polygon from a list of points.
```typst
#draw-polygon-obj(
  (points: ( (x:0,y:0), (x:2,y:0), (x:1,y:2) ), label: "Tri"),
  theme: active-theme
)
```

### Angles

#### `draw-angle-marker`
Draws an angle marker between three points (p1-vertex-p2).
```typst
#draw-angle-marker(
  (vertex: (x:0,y:0), p1: (x:1,y:0), p2: (x:0,y:1), radius: 0.5, label: "{angle}"),
  theme: active-theme
)
```
- Supports `{angle}` smart label placeholder (automatically calculates degrees).

#### `draw-right-angle-marker`
Draws a square right-angle symbol.

### Vectors

#### `draw-vector`
Draws a vector arrow with **pill-style label** centered on the vector.
```typst
#draw-vector(
  (x: 2, y: 3, label: "v"),
  theme: active-theme,
  origin: (0, 0)
)
```
- Labels appear centered on the vector with a rounded background
- Works in both 2D and 3D contexts

#### `draw-vector-components`
Draws the x and y components (projections) of a vector as dotted lines.

#### `draw-vector-addition`
Visualizes vector addition (parallelogram or tip-to-tail).

#### `draw-vector-projection`
Visualizes the projection of one vector onto another.

## Styling & Labels

### Smart Labels
Labels support placeholders for automatic value calculation:
- `{angle}`: The measure of an angle (for angle markers).
- `{length}`: The length of a segment or vector.
- `{radius}`: The radius of a circle/arc.
- `{area}`: The area of a polygon or circle.
- `{circum}`: The circumference/perimeter.

### Theme Integration
The `theme` argument (usually passed as `active-theme`) controls:
- **Stroke**: Default line color.
- **Fill**: Default fill color (often transparentized).
- **Highlight**: Color for emphasized elements.
