#import "../../templates/templater.typ": *

= Data Plotting

Plot data from CSV files or arrays using scatter plots and line plots.

== Scatter Plot from CSV

Load data directly from a CSV file and display as a scatter plot.

#let csv-data = parse-csv(read("../data/sample.csv"))
#let sample-data = data-series(csv-data, plot-type: "scatter", label: "Measurements")

#cartesian-canvas(
  x-domain: (0, 6),
  y-domain: (0, 12),
  sample-data,
)

== Line Plot from Array

Create a line plot from inline data.

#let trend-data = data-series(
  ((0, 1), (1, 2), (2, 4), (3, 3), (4, 5), (5, 7)),
  plot-type: "line",
  label: "Trend",
)

#cartesian-canvas(
  x-domain: (0, 6),
  y-domain: (0, 8),
  trend-data,
)

== Combined Scatter + Line

Show both points and connecting lines.

#let combined-data = data-series(
  ((0, 0), (1, 1), (2, 1.5), (3, 2.8), (4, 4), (5, 5.2)),
  plot-type: "both",
  label: "Data",
)

#cartesian-canvas(
  x-domain: (0, 6),
  y-domain: (0, 6),
  combined-data,
)
