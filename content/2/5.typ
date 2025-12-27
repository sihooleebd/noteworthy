#import "../../templates/templater.typ": *

= Data Visualization

Function plotting and data series.

== Function Graphs

Plot mathematical functions with `graph`:

#cartesian-canvas(
  x-domain: (-3, 3),
  y-domain: (-1, 5),
  axis-labels: ($x$, $y$),
  graph(x => calc.pow(x, 2), label: $y = x^2$),
)

== Multiple Functions

#cartesian-canvas(
  x-domain: (-2, 2),
  y-domain: (-2, 4),
  graph(x => calc.pow(x, 2), domain: (-2, 2), label: $x^2$),
  graph(x => calc.pow(x, 3), domain: (-2, 2), label: $x^3$, style: (stroke: red)),
  graph(x => calc.abs(x), label: $|x|$, style: (stroke: green)),
)

== Trigonometric Functions

#cartesian-canvas(
  x-domain: (-3.5, 3.5),
  y-domain: (-1.5, 1.5),
  graph(x => calc.sin(x), label: $sin(x)$),
  graph(x => calc.cos(x), label: $cos(x)$, style: (stroke: red)),
)

== Data Series

Plot data points from arrays:

#let measurements = (
  (0, 0.2),
  (1, 1.1),
  (2, 3.9),
  (3, 9.2),
  (4, 16.1),
)

#cartesian-canvas(
  x-domain: (-0.5, 5),
  y-domain: (-1, 18),
  data-series(measurements, plot-type: "both", label: "Data"),
  graph(x => calc.pow(x, 2), label: "Fit", style: (stroke: blue.transparentize(50%))),
)

#note("Data Series")[
  Use `data-series(data, plot-type: "scatter" | "line" | "both")` to plot data points.
]

== CSV Data

Load data from CSV files:

```typst
#let my-data = csv-series(
  read("path/to/data.csv"),
  plot-type: "scatter",
  has-header: true,
)
```
This can be then used to draw the data series:

#let my-data-1 = csv-series(
  read("../data/sample.csv"),
  plot-type: "line",
  has-header: true,
)
#let my-data-2 = csv-series(
  read("../data/sample.csv"),
  plot-type: "scatter",
  has-header: true,
)
#let my-data-3 = csv-series(
  read("../data/sample.csv"),
  plot-type: "both",
  has-header: true,
)
#cartesian-canvas(
  x-domain: (-0.5, 5),
  y-domain: (-1, 18),
  my-data-1,
)

#cartesian-canvas(
  x-domain: (-0.5, 5),
  y-domain: (-1, 18),
  my-data-2,
)
#cartesian-canvas(
  x-domain: (-0.5, 5),
  y-domain: (-1, 18),
  my-data-3,
)
