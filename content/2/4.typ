#import "../../templates/templater.typ": *

= Data Plotting

Plot data from CSV files or arrays using scatter plots and line plots.

== Scatter Plot from CSV

Load data directly from a CSV file and display as a scatter plot.

#let csv-data = parse-csv(read("../data/sample.csv"))
#let sample-data = data-series(csv-data, plot-type: "scatter", label: "Measurements")
#let trend-data = data-series(csv-data, plot-type: "line", label: "Trend")
#let combined-data = data-series(csv-data, plot-type: "both", label: "Data")

#cartesian-canvas(
  x-domain: (0, 6),
  y-domain: (0, 12),
  sample-data,
)

== Line Plot from Array

Create a line plot from inline data.

#cartesian-canvas(
  x-domain: (0, 6),
  y-domain: (0, 12),
  trend-data,
)

== Combined Scatter + Line

Show both points and connecting lines.

#cartesian-canvas(
  x-domain: (0, 6),
  y-domain: (0, 12),
  combined-data,
)
