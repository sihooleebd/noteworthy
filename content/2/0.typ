#import "../../templates/templater.typ": *

= Function Graphs

Plot mathematical functions easily with the new geometry system.

== Cartesian Functions

#let parabola = graph(x => x * x - 2, domain: (-3, 3), label: $y = x^2 - 2$)

#cartesian-canvas(
  x-domain: (-4, 4),
  y-domain: (-3, 5),
  parabola,
)

== Parametric Functions (Circle)

#let unit-circle = parametric(t => (calc.cos(t), calc.sin(t)), label: "Circle")

#cartesian-canvas(
  x-domain: (-2, 2),
  y-domain: (-2, 2),
  unit-circle,
)

== Polar Functions (Cardioid)

#let cardioid = polar-func(t => 1 + calc.cos(t), label: "Cardioid")

#polar-canvas(
  radius: 3,
  cardioid,
)

