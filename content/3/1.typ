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

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  graph.graph(x => x * x, domain: (-2, 2), label: $x^2$),
)

== Multiple Functions

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  graph.graph(x => x * x, domain: (-2, 2), label: $x^2$),
  graph.graph(x => x, domain: (-2, 2), label: $x$),
  graph.graph(x => 2 * x - 1, domain: (-2, 2), label: $2x - 1$),
)

== Trigonometric Functions

#canvas.trig-canvas(
  width: 10cm,
  graph.graph(x => calc.sin(x), domain: (-calc.pi, calc.pi), label: $sin(x)$),
  graph.graph(x => calc.cos(x), domain: (-calc.pi, calc.pi), label: $cos(x)$),
)

== Parametric Functions

#definition("parametric")[
  Plots a parametric curve $(x(t), y(t))$.
  ```typst
  parametric(t => (x(t), y(t)), domain: (min, max), label: none)
  ```
]

#canvas.cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  graph.parametric(t => (calc.cos(t) * 2, calc.sin(t) * 2), domain: (0, 2 * calc.pi), label: "Circle"),
)
