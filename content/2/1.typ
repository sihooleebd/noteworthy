#import "../../templates/templater.typ": *

= Points & Lines

The Shape module provides 2D geometric primitives.

== Creating Points

#definition("point")[
  Creates a point at coordinates $(x, y)$.
  ```typst
  point(x, y, label: "A", style: auto)
  ```
]

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  point(2, 3, label: "A"),
  point(-1, 2, label: "B"),
  point(3, -1, label: "C"),
)

== Creating Lines

#definition("line")[
  Creates an infinite line through two points.
  ```typst
  line(p1, p2, label: none, style: auto)
  ```
]

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  line(point(-2, -1), point(3, 2), label: $ell$),
)

== Line Segments

Use `segment` for lines with definite endpoints:

#definition("segment")[
  Creates a finite line segment between two points.
  ```typst
  segment(p1, p2, label: none, style: auto)
  ```
]

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  point(-2, 1, label: "A"),
  point(3, 2, label: "B"),
  segment(point(-2, 1), point(3, 2)),
)

== Combining Points and Lines

#example("Triangle Vertices")[
  #let A = point(0, 0, label: "A")
  #let B = point(4, 0, label: "B")
  #let C = point(2, 3, label: "C")

  #cartesian-canvas(
    x-tick: 1,
    y-tick: 1,
    A,
    B,
    C,
    segment(A, B),
    segment(B, C),
    segment(C, A),
  )
]
