#import "../../templates/templater.typ": *

= Circles & Polygons

Create circles and multi-sided shapes.

== Circles

#definition("circle")[
  Creates a circle from center and radius, or center and a point on the circle.
  ```typst
  circle(center, radius: r, label: none, label-anchor: "north", label-distance: 0.15)
  circle(center, through: point, label: none, label-anchor: "north", label-distance: 0.15)
  ```
]

#let O = shape.point(0, 0, label: "O", label-anchor: "south")
#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  shape.circle(O, radius: 2, label: $C$, label-anchor: "south-west"),
  O,
)

== Circle Through Point

#let O = shape.point(1, 1, label: "O", label-anchor: "south")
#let P = shape.point(3, 2, label: "P", label-anchor: "west")

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  O,
  P,
  shape.circle(O, through: P),
)

== Polygons

#definition("polygon")[
  Creates a closed polygon from vertices.
  ```typst
  polygon(p1, p2, p3, ..., label: none, label-anchor: "north", label-distance: 0.15)
  ```
]

#let A = shape.point(0, 0, label: "A", label-anchor: "south-west")
#let B = shape.point(4, 0, label: "B", label-anchor: "south-east")
#let C = shape.point(4, 3, label: "C", label-anchor: "north-east")
#let D = shape.point(0, 3, label: "D", label-anchor: "north-west")

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  shape.polygon(A, B, C, D, label: "Rectangle", label-anchor: "center"),
)

== Regular Polygons

#definition("regular-polygon")[
  Creates a regular n-sided polygon from a center and first vertex.
  ```typst
  regular-polygon(center, first-vertex, n, label: none, label-anchor: "north", label-distance: 0.15)
  ```
  The vertex position defines both the radius and orientation.
]

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  canvas.blank-canvas(
    width: 4cm,
    shape.regular-polygon(shape.point(0, 0), shape.point(0, 1.5), 3, label: "Triangle"),
  ),
  canvas.blank-canvas(
    width: 4cm,
    shape.regular-polygon(shape.point(0, 0), shape.point(1.5, 1.5), 5, label: "Pentagon"),
  ),
)

== Arcs

#definition("arc")[
  Creates an arc from a center and two points on the arc.
  ```typst
  arc(center, p1, p2, label: none, label-anchor: "north", label-distance: 0.15)
  ```
  The arc is drawn from `p1` to `p2`. The radius is derived from the center-to-p1 distance.
]

#let O = shape.point(0, 0, label: "O", label-anchor: "south")
#let A = shape.point(2, 0, label: "A", label-anchor: "east")
#let B = shape.point(0, 2, label: "B", label-anchor: "north")

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  O,
  A,
  B,
  shape.arc(O, A, B),
)

== Point at Angle

#definition("point-at-angle")[
  Creates a point at a given angle and radius from a center.
  ```typst
  point-at-angle(center, angle, radius, from: none, label: none, label-anchor: "north", label-distance: 0.2)
  ```
  When `from` is specified, the angle is measured counterclockwise from the center→from direction.
]

#example("67° Arc")[
  #let O = shape.point(0, 0, label: "O")
  #let A = shape.point(2, 0, label: "A")
  #let B = shape.point-at-angle(O, 67deg, 2, from: A, label: "B")

  #canvas.cartesian-canvas(
    x-tick: 1,
    y-tick: 1,
    O,
    A,
    B,
    shape.arc(O, A, B),
    shape.angle(A, O, B, label: "67°"),
  )
]

== Semicircles

#definition("semicircle")[
  Creates a 180° arc from a center and starting point.
  ```typst
  semicircle(center, start-point, label: none, style: auto)
  ```
]

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  shape.semicircle(shape.point(0, 0), shape.point(2, 0)),
)

== Angles

#definition("angle")[
  Creates an angle marker between three points.
  ```typst
  angle(p1, vertex, p2, label: $theta$, label-anchor: "center", label-distance: none)
  ```
]

#let O = shape.point(0, 0, label: "O")
#let A = shape.point(3, 0, label: "A")
#let B = shape.point(2, 2, label: "B")

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  O,
  A,
  B,
  shape.segment(O, A),
  shape.segment(O, B),
  shape.angle(A, O, B, label: $theta$),
)
