#import "../../templates/templater.typ": *

= Function Plotting

The Graph module provides function plotting and mathematical visualization.

== The graph Function

#definition("graph")[
  Plots a function $y = f(x)$ over a domain.
  ```typst
  graph(x => expr, domain: (min, max), label: $f(x)$)
  ```
]

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  graph(x => x * x, domain: (-2, 2), label: $x^2$),
)

== Multiple Functions

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  graph(x => x * x, domain: (-2, 2), label: $x^2$),
  graph(x => x, domain: (-2, 2), label: $x$),
  graph(x => 2 * x - 1, domain: (-2, 2), label: $2x - 1$),
)

== Trigonometric Functions

#trig-canvas(
  width: 10cm,
  graph(x => calc.sin(x), domain: (-calc.pi, calc.pi), label: $sin(x)$),
  graph(x => calc.cos(x), domain: (-calc.pi, calc.pi), label: $cos(x)$),
)

== Parametric Functions

#definition("parametric")[
  Plots a parametric curve $(x(t), y(t))$.
  ```typst
  parametric(t => (x(t), y(t)), domain: (min, max), label: none)
  ```
]

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  parametric(t => (calc.cos(t) * 2, calc.sin(t) * 2), domain: (0, 2 * calc.pi), label: "Circle"),
)
