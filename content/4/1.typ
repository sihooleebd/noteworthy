#import "../../templates/templater.typ": *

= Cartesian Canvas

The Canvas module provides rendering surfaces for shapes and graphs.

== Basic Canvas

#definition("cartesian-canvas")[
  Creates a 2D Cartesian coordinate system.
  ```typst
  cartesian-canvas(
    width: 8cm, height: 6cm,
    x-tick: 1, y-tick: 1,
    ..objects
  )
  ```
]

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  point(2, 3, label: "P"),
)

== Canvas Options

#notation("Key Parameters")[
  - `width`, `height` -- Canvas dimensions
  - `x-tick`, `y-tick` -- Grid spacing
  - `x-label`, `y-label` -- Axis labels
  - `show-grid` -- Toggle grid visibility
]

#cartesian-canvas(
  width: 10cm,
  height: 6cm,
  x-tick: 2,
  y-tick: 1,
  x-label: $x$,
  y-label: $y$,
  point(4, 2, label: "A"),
  point(-2, 1, label: "B"),
)

== Combining Shapes and Graphs

The cartesian canvas can display both shapes and graphs:

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  graph(x => x * x, domain: (-2, 2), label: $x^2$),
  point(1, 1, label: "P"),
  segment(point(-2, 0), point(2, 0)),
)

== Graph Canvas

For simpler function-only plots, use `graph-canvas`:

#graph-canvas(
  width: 10cm,
  height: 5cm,
  graph(x => x * x - 2, domain: (-3, 3), label: $x^2 - 2$),
)
