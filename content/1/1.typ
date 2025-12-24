#import "../../templates/templater.typ": *

= Vectors (Geoplot)

Visualize vectors using the unified object system.

== Vector Objects

#let u = vector(3, 2, label: $arrow(u)$, origin: (0, 0))
#let v = vector(1, 3, label: $arrow(v)$, origin: (0, 0), style: (stroke: red))

#blank-canvas(u, v)

== Vector Addition

Demonstrating the parallelogram method using object composition:

#let a = vector(3, 0, label: $arrow(a)$)
#let b = vector(1, 2, label: $arrow(b)$)
#let vec-sum = vec-add(a, b)
// Create display object for sum
#let sum-obj = vector(vec-sum.x, vec-sum.y, label: $sum$, style: (stroke: green))

// Dashed projection lines
#let b-shifted = vector(b.x, b.y, origin: (a.x, a.y), style: (stroke: (dash: "dashed", paint: gray)))
#let a-shifted = vector(a.x, a.y, origin: (b.x, b.y), style: (stroke: (dash: "dashed", paint: gray)))

#blank-canvas(
  a,
  b,
  sum-obj,
  b-shifted,
  a-shifted,
)

== Vector Projection

Visualizing projection of $a$ onto $b$.

#let vec-a = vector(2, 3, label: $arrow(a)$)
#let vec-b = vector(4, 0, label: $arrow(b)$)
#let proj = vec-project(vec-a, vec-b)
#let proj-obj = vector(proj.x, proj.y, label: $"proj"_b a$, style: (stroke: blue, thickness: 2pt))

// Perpendicular drop
#let drop = segment((proj.x, proj.y), (vec-a.x, vec-a.y), style: (stroke: (dash: "dotted")))

#blank-canvas(
  vec-a,
  vec-b,
  proj-obj,
  drop,
)
