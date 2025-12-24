#import "../../templates/templater.typ": *

= 3D Space (Spaceplot)

Render 3D scenes with correct perspective using `space-canvas`.

#space-canvas(
  view: (x: -90deg, y: -70deg, z: 0deg),
  vector-3d(2, 0, 0, origin: (0, 0, 0), label: $x$, style: (stroke: red)),
  vector-3d(0, 2, 0, origin: (0, 0, 0), label: $y$, style: (stroke: green)),
  vector-3d(0, 0, 2, origin: (0, 0, 0), label: $z$, style: (stroke: blue)),

  point-3d(3, 3, 3, label: "P"),
  vector-3d(3, 3, 3, origin: (0, 0, 0), label: $arrow(p)$),
)
