# Geometry Module

The `geometry` (or `shape`) module allows you to define geometric objects and perform construction and intersection operations. These objects can then be drawn using the `canvas` module.

## Import

```typst
#import "../../templates/templater.typ": *
```

## Geometric Objects

### Basic Types

-   **`point(x, y, label: none)`**: A 2D point.
-   **`line(p1, p2, label: none)`**: An infinite line passing through `p1` and `p2`.
-   **`ray(origin, through, label: none)`**: A ray starting at `origin` and passing through `through`.
-   **`segment(p1, p2, label: none)`**: A finite segment between `p1` and `p2`.
-   **`circle(center, radius, label: none)`**: A circle.
-   **`angle(vertex, p1, p2, radius: 1, label: none)`**: An angle defined by three points.
-   **`polygon(..points, label: none)`**: A closed polygon.

## Constructions

The module provides tools to construct new geometry from existing objects.

### Point Constructions
-   **`midpoint(segment)`** or **`midpoint(p1, p2)`**: Returns the midpoint.
-   **`divide-segment(segment, n)`**: Returns `n-1` points dividing the segment into `n` equal parts.
-   **`point-on-segment(segment, t)`**: Returns a point at parameter $t \in [0, 1]$.

### Line Constructions
-   **`perpendicular(line, through)`**: Creates a line perpendicular to `line` passing through `through`.
-   **`parallel(line, through)`**: Creates a line parallel to `line` passing through `through`.
-   **`perpendicular-bisector(segment)`**: Creates the perpendicular bisector line.
-   **`bisector(p1, vertex, p2)`**: Creates the angle bisector ray.

### Circle Constructions
-   **`circle-through-point(center, point)`**: Creates a circle centered at `center` passing through `point`.
-   **`tangent-at(circle, point)`**: Creates the tangent line at a specific point on the circle.
-   **`tangent-from(circle, external-point)`**: Returns an array of tangent lines from an external point to the circle (0, 1, or 2 lines).

### Transformations
-   **`reflect-point(point, line)`**: Reflects a point across a line.
-   **`rotate-point(point, center, angle)`**: Rotates a point around a center.
-   **`translate-point(point, dx, dy)`**: Translates a point.
-   **`scale-point(point, center, factor)`**: Dilates a point from a center.

## Intersections

Use the `intersect` function to find intersection points between any two geometry objects (Line-Line, Line-Circle, Circle-Circle).

```typst
// General intersection
#let pts = intersect(obj1, obj2)

// Convenience aliases with labeling
#let p = intersect-ll(line1, line2, label: "P")
#let pts = intersect-lc(line1, circle1, labels: ("A", "B"))
#let pts = intersect-cc(circle1, circle2, labels: ("C", "D"))
```

### Supported Intersections
-   **Linear-Linear**: Returns a single `point` or `none`.
-   **Linear-Circle**: Returns an array of 0, 1, or 2 points.
-   **Circle-Circle**: Returns an array of 0, 1, or 2 points.
