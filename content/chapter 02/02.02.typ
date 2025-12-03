#import "../../templates/templater.typ": *

= Geometry (Geoplot)

The `geoplot` module provides tools for Euclidean geometry constructions.

== Points & Polygons

#rect-plot({
  point((1, 1), "A", pos: "north")
  point((3, 1), "B", pos: "north")
  point((2, 3), "C", pos: "north")

  // Draw triangle connecting the points
  add-polygon(((1, 1), (3, 1), (2, 3)), label: "ABC")
})
