#import "../../templates/templater.typ": *

= Geometry (Geoplot)

The geometry module provides a unified object-oriented system for constructing Euclidean geometry, with intelligent labeling and comprehensive style support.

== Points & Triangles

#let A = point(1, 1, label: "A")
#let B = point(3, 1, label: "B")
#let C = point(2, 3, label: "C")
#let tri = triangle(A, B, C, label: "ABC")

#cartesian-canvas(
  x-domain: (0, 4),
  y-domain: (0, 4),
  A,
  B,
  C,
  tri,
)

== Lines & Segments

#let P = point(0, 0, label: "P")
#let Q = point(4, 3, label: "Q")
#let seg-PQ = segment(P, Q, label: "PQ")
#let M = midpoint(seg-PQ)
#let M-labeled = with-label(M, "M")

#cartesian-canvas(
  x-domain: (-1, 5),
  y-domain: (-1, 4),
  P,
  Q,
  seg-PQ,
  M-labeled,
)

== Angles & Circles

#let O = point(0, 0)
#let A2 = point(2, 0)
#let B2 = point(1.414, 1.414)
#let ang = angle(A2, O, B2, label: $theta$, radius: 0.6)
#let circ = circle(O, 2, label: "C", style: (stroke: (dash: "dashed")))

#cartesian-canvas(
  x-domain: (-3, 3),
  y-domain: (-3, 3),
  O,
  A2,
  B2,
  segment(O, A2),
  segment(O, B2),
  ang,
  circ,
)

== Polar Plots

#let rose = polar-func(t => 2 * calc.sin(3 * t))

#polar-canvas(
  radius: 3,
  rose,
)
