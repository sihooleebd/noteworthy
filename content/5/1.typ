#import "../../templates/templater.typ": *

= Tables

The Data module provides table rendering with theme-aware styling.

== Table Plot

#definition("table-plot")[
  Creates a styled data table.
  ```typst
  table-plot(
    headers: ("x", "y", "z"),
    data: ((1, 2, 3), (4, 5, 6)),
  )
  ```
]

#table-plot(
  headers: ("Variable", "Mean", "Std Dev"),
  data: (
    ("Height", "175 cm", "8.5"),
    ("Weight", "70 kg", "12.3"),
    ("Age", "25 yr", "4.2"),
  ),
)

== Value Table

#definition("value-table")[
  Creates a function value table with variable and result rows.
  ```typst
  value-table(
    variable: $x$,
    func: $f(x)$,
    values: (1, 2, 3, 4),
    results: (1, 4, 9, 16),
  )
  ```
]

#value-table(
  variable: $x$,
  func: $x^2$,
  values: (-2, -1, 0, 1, 2),
  results: (4, 1, 0, 1, 4),
)

== Grid Table

#definition("grid-table")[
  Creates a grid layout for 2D data visualization.
  ```typst
  grid-table(
    data: ((1, 2, 3), (4, 5, 6)),
    show-indices: true,
  )
  ```
]

#grid-table(
  data: (
    (1, 2, 3),
    (4, 5, 6),
    (7, 8, 9),
  ),
  show-indices: true,
)

== Compact Table

For inline or small tables:

#compact-table(
  headers: ("n", "n!"),
  data: ((0, 1), (1, 1), (2, 2), (3, 6), (4, 24)),
)
