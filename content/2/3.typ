#import "../../templates/templater.typ": *

= Intersections & Constructions

Find intersections and construct derived objects.

== Line-Line Intersection

#definition("intersect-ll")[
  Finds the intersection of two lines.
  ```typst
  intersect-ll(line1, line2, label: "P")
  ```
]

#let l1 = shape.line(shape.point(-2, -1), shape.point(3, 2), label: $ell_1$, label-anchor: "south")
#let l2 = shape.line(shape.point(-1, 3), shape.point(2, -2), label: $ell_2$, label-anchor: "west")

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  l1,
  l2,
  shape.intersect-ll(l1, l2, label: "P"),
)

== Line-Circle Intersection

#definition("intersect-lc")[
  Finds intersections of a line and circle.
  ```typst
  intersect-lc(line, circle, labels: ("A", "B"))
  ```
]

#let c = shape.circle(shape.point(0, 0), radius: 2)
#let l = shape.line(shape.point(-3, 1), shape.point(3, 1))

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  c,
  l,
  shape.intersect-lc(l, c, labels: ("A", "B")),
)

== Constructions

#definition("midpoint")[
  Constructs the midpoint of a segment.
  ```typst
  midpoint(p1, p2, label: "M", label-anchor: "south", label-distance: 0.2)
  ```
]

#let A = shape.point(1, 1, label: "A", label-anchor: "south-west")
#let B = shape.point(5, 3, label: "B", label-anchor: "north-east")

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  A,
  B,
  shape.segment(A, B),
  shape.midpoint(A, B, label: "M", label-anchor: "south"),
)

== Perpendicular & Parallel

#definition("perpendicular")[
  Constructs a line perpendicular to a given line through a point.
  ```typst
  perpendicular(line, point, label: none)
  ```
]

#definition("parallel")[
  Constructs a line parallel to a given line through a point.
  ```typst
  parallel(line, point, label: none)
  ```
]

#let l = shape.line(shape.point(0, 0), shape.point(4, 2), label: $ell$, label-anchor: "south")
#let P = shape.point(1, 3, label: "P", label-anchor: "east")

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  l,
  P,
  shape.perpendicular(l, P),
  shape.parallel(l, P),
)
