#import "../../templates/templater.typ": *

= Vectors (Vectorplot)

Visualize vectors with automatic scaling and labeling.

== Basic Vectors

#let u = vector(3, 2, label: $arrow(u)$)
#let v = vector(1, 3, label: $arrow(v)$, style: (stroke: red))

#blank-canvas(u, v)

== Vector Addition

The parallelogram method:

#let a = vector(3, 0, label: $arrow(a)$)
#let b = vector(1, 2, label: $arrow(b)$)

#blank-canvas(
  a,
  b,
  vec-add(a, b, helplines: true),
)

== Vector with Custom Origin

#let origin-vec = vector(2, 1, origin: (1, 1), label: $arrow(w)$)

#cartesian-canvas(
  x-domain: (0, 4),
  y-domain: (0, 3),
  origin-vec,
)

== Multiple Vectors

#let v1 = vector(2, 0, label: $hat(i)$, style: (stroke: red))
#let v2 = vector(0, 2, label: $hat(j)$, style: (stroke: green))
#let v3 = vector(2, 2, label: $hat(i) + hat(j)$, style: (stroke: blue))

#blank-canvas(v1, v2, v3)

== Vector Projection

Project vector $arrow(a)$ onto $arrow(b)$:

#let proj-a = vector(8, 6, label: $arrow(a)$)
#let proj-b = vector(10, 0, label: $arrow(b)$)

#blank-canvas(
  proj-a,
  proj-b,
  vec-project(proj-a, proj-b, label: $"proj"_(arrow(a)) arrow(b)$, helplines: true),
)

#note("Vector Notation")[
  Vectors are defined by `vector(dx, dy, ...)` where `dx` and `dy` are the components.
]
