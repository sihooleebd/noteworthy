#import "../../templates/templater.typ": *

= Calculus Visualization

Tools for visualizing limits, derivatives, and integrals.

== Limits and Holes

Visualize discontinuities using the `hole` parameter.

#let rational(x) = if x == 1 { 2 } else { (x * x - 1) / (x - 1) }

#cartesian-canvas(
  x-domain: (-1, 3),
  y-domain: (0, 4),
  graph(rational, domain: (-1, 3), hole: (1,), label: $f(x) = (x^2-1)/(x-1)$),
)

== Derivatives (Tangents & Normals)

Visualize instantaneous rates of change.

#let curve(x) = x * x / 4 + 1
#let t = 2

#cartesian-canvas(
  x-domain: (-1, 4),
  y-domain: (0, 6),
  graph(curve, domain: (-1, 4), label: $f(x) = x^2/4 + 1$),
  tangent(curve, t, length: 3, style: (stroke: (paint: blue, dash: "dashed"))),
  normal(curve, t, length: 3, style: (stroke: (paint: red, dash: "dotted"))),
  point(t, curve(t), label: $P(2, 2)$),
)

== Integrals (Riemann Sums)

Visualize area approximation using Riemann sums.

#let f-int(x) = calc.sqrt(x) + 0.5
#let area-dom = (0.5, 3.5)

#cartesian-canvas(
  x-domain: (0, 4),
  y-domain: (0, 3),
  graph(f-int, domain: (0, 4), label: $f(x) = sqrt(x) + 0.5$),
  riemann-sum(f-int, area-dom, 6, method: "left", label: "Left Sum"),
)

#cartesian-canvas(
  x-domain: (0, 4),
  y-domain: (0, 3),
  graph(f-int, domain: (0, 4)),
  riemann-sum(f-int, area-dom, 8, method: "midpoint", label: "Midpoint Sum"),
)

#cartesian-canvas(
  x-domain: (0, 4),
  y-domain: (0, 3),
  graph(f-int, domain: (0, 4)),
  riemann-sum(f-int, area-dom, 10, method: "right", label: "Right Sum"),
)

#cartesian-canvas(
  x-domain: (0, 4),
  y-domain: (0, 3),
  graph(f-int, domain: (0, 4)),
  riemann-sum(f-int, area-dom, 12, method: "trapezoid", label: "Trapezoid Sum"),
)

#cartesian-canvas(
  x-domain: (0, 4),
  y-domain: (0, 3),
  graph(f-int, domain: (0, 4)),
  riemann-sum(f-int, area-dom, 50, method: "trapezoid", label: "∫ f(x) dx", smooth: true),
)
