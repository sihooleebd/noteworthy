#import "@preview/cetz:0.4.2"

// Beautiful themed table renderer
#let table-plot(
  theme: (:),
  headers: (),
  data: (),
  align-cols: auto,
  width: 100%,
  header-fill: auto,
  row-fill: auto,
  stroke-color: auto,
) = {
  // Use theme colors or defaults
  let actual-header-fill = if header-fill == auto {
    theme.blocks.theorem.fill
  } else {
    header-fill
  }

  let actual-stroke = if stroke-color == auto {
    theme.blocks.theorem.stroke.transparentize(50%)
  } else {
    stroke-color
  }

  let actual-row-fill = if row-fill == auto {
    (theme.page-fill, theme.blocks.definition.fill.transparentize(50%))
  } else {
    row-fill
  }

  // Set up alignment
  let num-cols = headers.len()
  let alignments = if align-cols == auto {
    (center,) * num-cols
  } else {
    align-cols
  }

  // Build the table
  table(
    columns: (auto,) * num-cols,
    align: (col, row) => {
      if row == 0 { center } else { alignments.at(calc.min(col, alignments.len() - 1)) }
    },
    fill: (col, row) => {
      if row == 0 {
        actual-header-fill
      } else {
        actual-row-fill.at(calc.rem(row - 1, actual-row-fill.len()))
      }
    },
    stroke: (x, y) => {
      // Thicker stroke for header bottom
      if y == 0 {
        (bottom: 2pt + actual-stroke, rest: 1pt + actual-stroke)
      } else if y == 1 {
        (top: 2pt + actual-stroke, rest: 1pt + actual-stroke)
      } else {
        1pt + actual-stroke
      }
    },
    inset: 10pt,

    // Header row
    ..headers.map(h => text(
      fill: theme.text-heading,
      weight: "bold",
      size: 11pt,
      font: theme.at("title-font", default: "IBM Plex Serif"),
    )[#h]),

    // Data rows
    ..data
      .flatten()
      .map(cell => text(
        fill: theme.text-main,
        size: 10pt,
      )[#cell]),
  )
}

// Compact table version for smaller datasets
#let compact-table(
  theme: (:),
  headers: (),
  data: (),
  align-cols: auto,
) = {
  table-plot(
    theme: theme,
    headers: headers,
    data: data,
    align-cols: align-cols,
    width: auto,
  )
}

// Value comparison table (for showing function values, etc.)
#let value-table(
  theme: (:),
  variable: $x$,
  values: (),
  func: $f(x)$,
  results: (),
) = {
  table-plot(
    theme: theme,
    headers: (variable, func),
    data: values.zip(results),
    align-cols: (center, center),
  )
}

// Grid-style table for matrices or coordinate data
#let grid-table(
  theme: (:),
  data: (),
  show-indices: false,
) = {
  let num-cols = if data.len() > 0 { data.at(0).len() } else { 0 }

  if show-indices {
    let headers = range(num-cols).map(i => str(i))
    table-plot(
      theme: theme,
      headers: headers,
      data: data,
      align-cols: (center,) * num-cols,
    )
  } else {
    // No headers - render data directly as a simple table
    let actual-stroke = theme.blocks.theorem.stroke.transparentize(50%)
    let actual-row-fill = (theme.page-fill, theme.blocks.definition.fill.transparentize(50%))

    table(
      columns: (auto,) * num-cols,
      align: center,
      fill: (col, row) => actual-row-fill.at(calc.rem(row, actual-row-fill.len())),
      stroke: 1pt + actual-stroke,
      inset: 10pt,
      ..data
        .flatten()
        .map(cell => text(
          fill: theme.text-main,
          size: 10pt,
        )[#cell]),
    )
  }
}
