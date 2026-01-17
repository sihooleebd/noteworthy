#import "../../templates/templater.typ": *

= Points & Lines

The Shape module provides 2D geometric primitives.

== Creating Points

#definition("point")[
  Creates a point at coordinates $(x, y)$.
  ```typst
  point(x, y, label: "A", label-anchor: "south", label-distance: 0.2)
  ```
]

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  shape.point(2, 3, label: "A", label-anchor: "south"),
  shape.point(-1, 2, label: "B", label-anchor: "east"),
  shape.point(3, -1, label: "C", label-anchor: "north"),
)

== Creating Lines

#definition("line")[
  Creates an infinite line through two points.
  ```typst
  line(p1, p2, label: none, label-anchor: "south", label-distance: 0.15)
  ```
]

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  shape.line(shape.point(-2, -1), shape.point(3, 2), label: $ell$, label-anchor: "west"),
)

== Line Segments

Use `segment` for lines with definite endpoints:

#definition("segment")[
  Creates a finite line segment between two points.
  ```typst
  segment(p1, p2, label: none, label-anchor: "south", label-distance: 0.15)
  ```
]

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  shape.point(-2, 1, label: "A", label-anchor: "west"),
  shape.point(3, 2, label: "B", label-anchor: "east"),
  shape.segment(shape.point(-2, 1), shape.point(3, 2)),
)

== Combining Points and Lines

#example("Triangle Vertices")[
  #let A = shape.point(0, 0, label: "A", label-anchor: "south-east")
  #let B = shape.point(4, 0, label: "B", label-anchor: "south-east")
  #let C = shape.point(2, 3, label: "C", label-anchor: "north")

  #canvas.cartesian-canvas(
    x-tick: 1,
    y-tick: 1,
    A,
    B,
    C,
    shape.segment(A, B),
    shape.segment(B, C),
    shape.segment(C, A),
  )
]
