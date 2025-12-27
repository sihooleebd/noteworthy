#import "../../templates/templater.typ": *

= Smooth Curves

Draw smooth curves through data points using spline interpolation.

== Curve Through Points

#definition("curve-through")[
  Creates a smooth curve through a set of points.
  ```typst
  curve-through(
    (p1, p2, p3, ...),
    label: "Curve",
    tension: 0.5,
  )
  ```

  - `tension`: Controls curve tightness (0 = linear, 1 = tight)
]

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  curve-through(
    ((0, 1), (1, 3), (2, 2), (3, 4), (4, 3)),
    label: "Smooth",
  ),
)

== Tension Control

#example("Tension Comparison")[
  Lower tension creates smoother curves:

  #grid(
    columns: (1fr, 1fr),
    gutter: 1em,
    [
      *Tension: 0.3*
      #cartesian-canvas(
        width: 5cm,
        x-tick: 1,
        y-tick: 1,
        curve-through(
          ((0, 1), (1, 3), (2, 1), (3, 3)),
          tension: 0.3,
        ),
      )
    ],
    [
      *Tension: 0.8*
      #cartesian-canvas(
        width: 5cm,
        x-tick: 1,
        y-tick: 1,
        curve-through(
          ((0, 1), (1, 3), (2, 1), (3, 3)),
          tension: 0.8,
        ),
      )
    ],
  )
]

== Smooth Curve

#definition("smooth-curve")[
  Alternative curve function with automatic tension.
  ```typst
  smooth-curve(
    (p1, p2, p3, ...),
    label: "Curve",
  )
  ```
]

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  smooth-curve(
    ((0, 0), (1, 2), (2, 1), (3, 3), (4, 2)),
    label: "Auto-smooth",
  ),
)
