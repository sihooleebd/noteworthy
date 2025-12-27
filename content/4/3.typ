#import "../../templates/templater.typ": *

= 3D Space Canvas

Visualize 3D geometry and vectors.

== Space Canvas

#definition("space-canvas")[
  Creates a 3D coordinate system with perspective.
  ```typst
  space-canvas(
    width: 8cm,
    ..objects
  )
  ```
]

#space-canvas(
  width: 10cm,
  point(2, 1, z: 3, label: "P"),
)

== 3D Points

Use `point()` with z coordinate for 3D points:

#space-canvas(
  width: 10cm,
  point(0, 0, z: 0, label: "O"),
  point(3, 0, z: 0, label: "A"),
  point(0, 3, z: 0, label: "B"),
  point(0, 0, z: 3, label: "C"),
)

== 3D Vectors

Use `vec()` with 3 components for 3D vectors:

#definition("vec (3D)")[
  Creates a 3D vector from origin.
  ```typst
  vec((x, y, z), label: $arrow(v)$)
  ```
]

#space-canvas(
  width: 10cm,
  vec((2, 1, 2), label: $arrow(v)$),
  vec((1, 3, 1), label: $arrow(w)$),
  vec-project(vec((2, 1, 2)), onto: vec((1, 3, 1))),
)

== Coordinate Axes

The space canvas follows the right-hand rule:
- x-axis points right
- y-axis points forward
- z-axis points up
