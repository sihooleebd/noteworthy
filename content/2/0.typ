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

== Robust Rendering (Singularity Handling)

The `robust-func` uses adaptive sampling to correctly render functions like $sin(pi/x)$ near singularities:

#let singular-func = robust-func(
  x => if x == 0 { 0 } else { calc.sin(calc.pi / x) },
  domain: (-0.5, 0.5),
  label: $sin(pi/x)$,
)


#cartesian-canvas(
  x-domain: (-0.6, 0.6),
  y-domain: (-1.5, 1.5),
  singular-func,
)
