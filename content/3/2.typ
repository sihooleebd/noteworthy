#import "../../templates/templater.typ": *

= Vectors

The Graph module includes vector operations for 2D vector mathematics.

== Creating Vectors

#definition("vec")[
  Creates a 2D vector object.
  ```typst
  vec((x, y), label: $arrow(v)$, origin: (0, 0))
  ```
]

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  graph.vec((3, 2), label: $arrow(v)$),
)

== Vector from Point

Vectors can start from any origin:

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  shape.point(1, 1, label: "A", label-anchor: "south"),
  graph.vec((2, 1.5), origin: (1, 1), label: $arrow(v)$),
)

== Vector Addition

#definition("vec-add")[
  Visualizes vector addition with parallelogram.
  ```typst
  vec-add(v1, v2, helplines: true)
  ```
]

#canvas.blank-canvas(
  x-tick: 1,
  y-tick: 1,
  graph.vec((3, 1), label: $arrow(a)$),
  graph.vec((1, 2), label: $arrow(b)$),
  graph.vec-add(
    graph.vec((3, 1), label: $arrow(a)$),
    graph.vec((1, 2), label: $arrow(b)$),
    helplines: true,
  ),
)

== Vector Components

#definition("vec-components")[
  Shows vector decomposition into components.
  ```typst
  vec-components(v, labels: ($v_x$, $v_y$))
  ```
]

#canvas.blank-canvas(
  x-tick: 1,
  y-tick: 1,
  graph.vec((4, 3)),
  graph.vec-components(
    graph.vec((4, 3)),
    labels: ($v_x$, $v_y$),
    helplines: true,
  ),
)

== Vector Projection

#definition("vec-project")[
  Projects one vector onto another.
  ```typst
  vec-project(v, onto: w, helplines: true)
  ```
]

#canvas.blank-canvas(
  x-tick: 1,
  y-tick: 1,
  graph.vec((3, 4)),
  graph.vec-project(
    graph.vec((3, 4), label: $arrow(v)$),
    onto: graph.vec((5, 0), label: $arrow(w)$),
    helplines: true,
  ),
)
