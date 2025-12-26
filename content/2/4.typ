#import "../../templates/templater.typ": *

= 3D Space (Spaceplot)

Render 3D scenes with perspective projection.

== Coordinate Axes

#space-canvas(
  view: (x: -90deg, y: -70deg, z: 0deg),
  vector-3d(2, 0, 0, origin: (0, 0, 0), label: $x$, style: (stroke: red)),
  vector-3d(0, 2, 0, origin: (0, 0, 0), label: $y$, style: (stroke: green)),
  vector-3d(0, 0, 2, origin: (0, 0, 0), label: $z$, style: (stroke: blue)),
)

== 3D Points

#space-canvas(
  view: (x: -90deg, y: -70deg, z: 0deg),
  vector-3d(2, 0, 0, origin: (0, 0, 0), label: $x$, style: (stroke: red)),
  vector-3d(0, 2, 0, origin: (0, 0, 0), label: $y$, style: (stroke: green)),
  vector-3d(0, 0, 2, origin: (0, 0, 0), label: $z$, style: (stroke: blue)),
  point-3d(1, 2, 1.5, label: "P"),
)

== 3D Vectors

#space-canvas(
  view: (x: -90deg, y: -70deg, z: 0deg),
  vector-3d(3, 3, 3, origin: (0, 0, 0), label: $arrow(r)$),
  point-3d(3, 3, 3, label: "P(3,3,3)"),
)

== Custom View Angles

Change perspective with the `view` parameter:

#space-canvas(
  view: (x: -45deg, y: -45deg, z: 0deg),
  vector-3d(2, 0, 0, origin: (0, 0, 0), style: (stroke: red)),
  vector-3d(0, 2, 0, origin: (0, 0, 0), style: (stroke: green)),
  vector-3d(0, 0, 2, origin: (0, 0, 0), style: (stroke: blue)),
  point-3d(1, 1, 1, label: "(1,1,1)"),
)

#note("View Angle")[
  The `view` parameter takes rotation angles for each axis to control the 3D projection.
]
