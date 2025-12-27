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

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  vec((3, 2), label: $arrow(v)$),
)

== Vector from Point

Vectors can start from any origin:

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  point(1, 1, label: "A"),
  vec((2, 1.5), origin: (1, 1), label: $arrow(v)$),
)

== Vector Addition

#definition("vec-add")[
  Visualizes vector addition with parallelogram.
  ```typst
  vec-add(v1, v2, helplines: true)
  ```
]

#blank-canvas(
  x-tick: 1,
  y-tick: 1,
  vec((3, 1), label: $arrow(a)$),
  vec((1, 2), label: $arrow(b)$),
  vec-add(
    vec((3, 1), label: $arrow(a)$),
    vec((1, 2), label: $arrow(b)$),
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

#blank-canvas(
  x-tick: 1,
  y-tick: 1,
  vec((4, 3)),
  vec-components(
    vec((4, 3)),
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

#blank-canvas(
  x-tick: 1,
  y-tick: 1,
  vec((3, 4)),
  vec-project(
    vec((3, 4), label: $arrow(v)$),
    onto: vec((5, 0), label: $arrow(w)$),
    helplines: true,
  ),
)
