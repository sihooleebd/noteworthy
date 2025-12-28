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

#definition("regular-polygon")[
  Creates a regular n-sided polygon from a center and first vertex.
  ```typst
  regular-polygon(center, first-vertex, n, label: none, style: auto)
  ```
  The vertex position defines both the radius and orientation.
]

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  blank-canvas(
    width: 4cm,
    regular-polygon(point(0, 0), point(0, 1.5), 3, label: "Triangle"),
  ),
  blank-canvas(
    width: 4cm,
    regular-polygon(point(0, 0), point(1.5, 1.5), 5, label: "Pentagon"),
  ),
)

== Arcs

#definition("arc")[
  Creates an arc from a center and two points on the arc.
  ```typst
  arc(center, p1, p2, label: none, style: auto)
  ```
  The arc is drawn from `p1` to `p2`. The radius is derived from the center-to-p1 distance.
]

#let O = point(0, 0, label: "O")
#let A = point(2, 0, label: "A")
#let B = point(0, 2, label: "B")

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  O,
  A,
  B,
  arc(O, A, B),
)

== Point at Angle

#definition("point-at-angle")[
  Creates a point at a given angle and radius from a center.
  ```typst
  point-at-angle(center, angle, radius, baseline: none, label: none)
  ```
  When `baseline` is specified, the angle is measured counterclockwise from the center→baseline direction.
]

#example("67° Arc")[
  #let O = point(0, 0, label: "O")
  #let A = point(2, 0, label: "A")
  #let B = point-at-angle(O, 67deg, 2, baseline: A, label: "B")

  #cartesian-canvas(
    x-tick: 1,
    y-tick: 1,
    O,
    A,
    B,
    arc(O, A, B),
    angle(A, O, B, label: "67°"),
  )
]

== Semicircles

#definition("semicircle")[
  Creates a 180° arc from a center and starting point.
  ```typst
  semicircle(center, start-point, label: none, style: auto)
  ```
]

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  semicircle(point(0, 0), point(2, 0)),
)

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
