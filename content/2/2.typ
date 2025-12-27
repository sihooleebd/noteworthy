#import "../../templates/templater.typ": *

= Circles & Polygons

Create circles and multi-sided shapes.

== Circles

#definition("circle")[
  Creates a circle from center and radius, or center and a point on the circle.
  ```typst
  circle(center, radius: r, label: none, style: auto)
  circle(center, through: point, label: none, style: auto)
  ```
]

#let O = point(0, 0, label: "O")
#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  circle(O, radius: 2, label: $C$),
  O,
)

== Circle Through Point

#let O = point(1, 1, label: "O")
#let P = point(3, 2, label: "P")

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  O,
  P,
  circle(O, through: P),
)

== Polygons

#definition("polygon")[
  Creates a closed polygon from vertices.
  ```typst
  polygon(p1, p2, p3, ..., label: none, style: auto)
  ```
]

#let A = point(0, 0, label: "A")
#let B = point(4, 0, label: "B")
#let C = point(4, 3, label: "C")
#let D = point(0, 3, label: "D")

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  polygon(A, B, C, D, label: "Rectangle"),
)

== Regular Polygons

#example("Regular Shapes")[
  #grid(
    columns: (1fr, 1fr),
    gutter: 1em,
    cartesian-canvas(
      width: 4cm,
      polygon(point(0, 0), point(2, 0), point(1, 1.73)),
    ),
    cartesian-canvas(
      width: 4cm,
      polygon(point(0, 0), point(2, 0), point(2, 2), point(0, 2)),
    ),
  )
]

== Angles

#definition("angle")[
  Creates an angle marker between three points.
  ```typst
  angle(p1, vertex, p2, label: $theta$, style: auto)
  ```
]

#let O = point(0, 0, label: "O")
#let A = point(3, 0, label: "A")
#let B = point(2, 2, label: "B")

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  O,
  A,
  B,
  segment(O, A),
  segment(O, B),
  angle(A, O, B, label: $theta$),
)
