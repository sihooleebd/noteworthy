#import "../../templates/templater.typ": *

= Canvas System Overview

The Noteworthy canvas system provides unified object-oriented plotting.

== Canvas Types

Noteworthy provides four canvas types:

#definition("cartesian-canvas")[
  Standard 2D Cartesian coordinate system with axes,grids, and labels.
]

#definition("blank-canvas")[
  Canvas without axes - useful for diagrams and geometric constructions.
]

#definition("polar-canvas")[
  Polar coordinate system for circular plots.
]

#definition("space-canvas")[
  3D coordinate system with perspective projection.
]

== Basic Example

A simple Cartesian canvas with a point and line:

#let A = point(1, 1, label: "A")
#let B = point(3, 2, label: "B")

#cartesian-canvas(
  x-domain: (0, 4),
  y-domain: (0, 3),
  A,
  B,
  segment(A, B, label: "AB"),
)

== Blank Canvas

For diagrams without coordinate axes:

#let P = point(0, 0, label: "P")
#let Q = point(2, 0, label: "Q")
#let R = point(1, 1.5, label: "R")

#blank-canvas(
  P,
  Q,
  R,
  triangle(P, Q, R),
)
