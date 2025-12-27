#import "../../templates/templater.typ": *

= Data Series & CSV

Plot data points from arrays or CSV files.

== Data Series

#definition("data-series")[
  Creates a plotable data series from coordinate pairs.
  ```typst
  data-series(
    ((x1, y1), (x2, y2), ...),
    label: "Series",
    style: auto,
  )
  ```
]

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  data-series(
    ((0, 0), (1, 2), (2, 3), (3, 2.5), (4, 4)),
    label: "Data",
  ),
)

== Multiple Series

#cartesian-canvas(
  x-tick: 1,
  y-tick: 1,
  data-series(
    ((0, 1), (1, 3), (2, 2), (3, 4)),
    label: "Series A",
  ),
  data-series(
    ((0, 2), (1, 1), (2, 3), (3, 2)),
    label: "Series B",
  ),
)

== CSV Import

#definition("csv-series")[
  Loads data from a CSV file.
  ```typst
  csv-series(
    "path/to/data.csv",
    x-col: 0,
    y-col: 1,
    label: "CSV Data",
  )
  ```
]

#note("CSV Format")[
  The CSV file should have numeric data. Header rows are automatically detected and skipped.
]

== Polar Data Series

#definition("polar-data-series")[
  Creates a data series in polar coordinates (r, θ).
  ```typst
  polar-data-series(
    ((r1, θ1), (r2, θ2), ...),
    label: "Polar",
  )
  ```
]

Use `polar-data-series` with `polar-canvas` for radial data visualization.
