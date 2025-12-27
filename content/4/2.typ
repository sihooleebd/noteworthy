#import "../../templates/templater.typ": *

= Polar & Trig Canvas

Specialized canvases for polar coordinates and trigonometry.

== Polar Canvas

#definition("polar-canvas")[
  Creates a polar coordinate system with radial and angular axes.
  ```typst
  polar-canvas(
    width: 8cm,
    r-max: 3,
    ..objects
  )
  ```
]

#polar-canvas(
  width: 8cm,
  polar-func(t => 2, label: "r=2"),
)

== Polar Functions

Use `polar-func` to plot $r = f(theta)$:

#polar-canvas(
  width: 8cm,
  polar-func(t => 1 + calc.cos(t), domain: (0, 2 * calc.pi), label: "Cardioid"),
)

== Trig Canvas

#definition("trig-canvas")[
  A Cartesian canvas with ticks at multiples of pi.
  ```typst
  trig-canvas(
    width: 10cm,
    ..objects
  )
  ```
]

#trig-canvas(
  width: 10cm,
  graph(x => calc.sin(x), domain: (-calc.pi, calc.pi), label: $sin(x)$),
  graph(x => calc.cos(x), domain: (-calc.pi, calc.pi), label: $cos(x)$),
  graph(x => calc.tan(x), domain: (-calc.pi, calc.pi), label: $tan(x)$),
)

== Rose Curves

#example("Polar Rose")[
  $r = cos(3 theta)$ creates a 3-petal rose:

  #polar-canvas(
    width: 8cm,
    polar-func(t => calc.cos(3 * t), domain: (0, calc.pi), label: "Rose"),
  )
]
