#import "../../templates/templater.typ": *

= Geometry (Geoplot)

Create Euclidean geometry constructions with the geometry object system.

== Points & Labels

#let A = point(0, 0, label: "A")
#let B = point(3, 0, label: "B")
#let C = point(1.5, 2.5, label: "C")

#cartesian-canvas(
  x-domain: (-0.5, 4),
  y-domain: (-0.5, 3),
  A,
  B,
  C,
)

== Lines & Segments

#cartesian-canvas(
  x-domain: (-0.5, 4),
  y-domain: (-0.5, 3),
  A,
  B,
  C,
  segment(A, B, label: "c"),
  segment(B, C, label: "a"),
  segment(C, A, label: "b"),
)

== Triangles

The `triangle` object draws all three sides:

#cartesian-canvas(
  x-domain: (-0.5, 4),
  y-domain: (-0.5, 3),
  triangle(A, B, C, label: "△ABC"),
  A,
  B,
  C,
)

== Circles

#let center = point(2, 1.5, label: "O")

#cartesian-canvas(
  x-domain: (-0.5, 5),
  y-domain: (-0.5, 4),
  center,
  circle(center, 1.5, label: "r = 1.5"),
)

== Angles

#let origin = point(0, 0, label: "O")
#let p1 = point(2, 0)
#let p2 = point(1.5, 1.5)

#cartesian-canvas(
  x-domain: (-0.5, 3),
  y-domain: (-0.5, 2.5),
  origin,
  segment(origin, p1),
  segment(origin, p2),
  angle(p1, origin, p2, label: "{angle}"),
)

== Curves

Connect points with polylines or smooth splines:

#let pts = ((0, 0), (1, 2), (2, 0.5), (3, 1.5), (4, 0))

=== Polyline (curve-through)

#cartesian-canvas(
  x-domain: (-0.5, 5),
  y-domain: (-0.5, 3),
  curve-through(..pts, label: "Polyline"),
  point(0, 0),
  point(1, 2),
  point(2, 0.5),
  point(3, 1.5),
  point(4, 0),
)

=== Smooth Spline (smooth-curve)

#cartesian-canvas(
  x-domain: (-0.5, 5),
  y-domain: (-0.5, 3),
  smooth-curve(..pts, label: "Spline", style: (stroke: blue)),
  point(0, 0),
  point(1, 2),
  point(2, 0.5),
  point(3, 1.5),
  point(4, 0),
)

=== Tension Control

Higher tension creates tighter curves:

#cartesian-canvas(
  x-domain: (-0.5, 5),
  y-domain: (-0.5, 3),
  smooth-curve(..pts, label: "t=0", style: (stroke: blue)),
  smooth-curve(..pts, tension: 0.5, label: "t=0.5", style: (stroke: red)),
)
