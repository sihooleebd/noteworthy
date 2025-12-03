#import "../../templates/templater.typ": *

= Combinatorics

Visualizations for counting problems.

== Stars and Bars (Boxes)

#combi-plot({
  draw-boxes(3, (2, 1, 3))
})

== Linear Arrangements

#combi-plot({
  draw-linear(("A", "B", "C", "D"))
})

== Circular Arrangements

#combi-plot({
  draw-circular(("A", "B", "C", "D", "E"), radius: 2)
})
