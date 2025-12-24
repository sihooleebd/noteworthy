#import "../../templates/templater.typ": *

= Combinatorics

Visualizations for counting problems.

== Stars and Bars (Boxes)

#blank-canvas(
  draw-boxes(3, (2, 1, 3)),
)

== Linear Arrangements

#blank-canvas(
  draw-linear(("A", "B", "C", "D")),
)

== Circular Arrangements

#blank-canvas(
  draw-circular(("A", "B", "C", "D", "E"), radius: 2),
)
