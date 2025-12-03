#import "../../templates/templater.typ": *

= Vectors (Vectorplot)

Visualize vectors and vector operations.

== Vector Drawing

#combi-plot({
  draw-vec((0, 0), (3, 2), label: $vec(u)$)
  draw-vec((0, 0), (1, 3), label: $vec(v)$, color: red)
})

== Vector Components

Shows the x and y components of a vector.

#combi-plot({
  // Draw the main vector first
  draw-vec((0, 0), (3, 2), label: $vec(v)$)
  // Then show its components
  draw-vec-comps((3, 2), label-x: "3", label-y: "2")
})

== Vector Addition

#combi-plot({
  draw-vec-sum((3, 0), (1, 2), mode: "parallelogram")
})

== Vector Projection

#combi-plot({
  draw-vec-proj((2, 3), (4, 0))
})
