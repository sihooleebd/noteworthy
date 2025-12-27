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

#let l1 = line(point(-2, -1), point(3, 2), label: $ell_1$)
#let l2 = line(point(-1, 3), point(2, -2), label: $ell_2$)

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  l1,
  l2,
  intersect-ll(l1, l2, label: "P"),
)

== Line-Circle Intersection

#definition("intersect-lc")[
  Finds intersections of a line and circle.
  ```typst
  intersect-lc(line, circle, labels: ("A", "B"))
  ```
]

#let c = circle(point(0, 0), radius: 2)
#let l = line(point(-3, 1), point(3, 1))

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  c,
  l,
  intersect-lc(l, c, labels: ("A", "B")),
)

== Constructions

#definition("midpoint")[
  Constructs the midpoint of a segment.
  ```typst
  midpoint(p1, p2, label: "M")
  ```
]

#let A = point(1, 1, label: "A")
#let B = point(5, 3, label: "B")

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  A,
  B,
  segment(A, B),
  midpoint(A, B, label: "M"),
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

#let l = line(point(0, 0), point(4, 2), label: $ell$)
#let P = point(1, 3, label: "P")

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  l,
  P,
  perpendicular(l, P),
  parallel(l, P),
)
