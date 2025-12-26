// Table objects and rendering - OO style
// Object constructors return dictionaries, rendering is separate

#import "../setup.typ": *

// =====================================================
// OBJECT CONSTRUCTORS
// =====================================================

/// Creates a table-data object
/// - headers: Array of column headers
/// - data: Array of rows (each row is an array of cells)
/// - style: Optional style overrides (header-fill, row-fill, stroke-color, align-cols)
#let table-data(
  headers,
  data,
  style: (:),
) = (
  type: "table-data",
  headers: headers,
  data: data,
  style: style,
)

/// Creates a value-table object (for function values)
/// - variable: Variable name (e.g. $x$)
/// - func: Function name (e.g. $f(x)$)
/// - values: Array of input values
/// - results: Array of output values
#let value-table-data(
  variable,
  func,
  values,
  results,
  style: (:),
) = table-data(
  (variable, func),
  values.zip(results),
  style: style,
)

/// Creates a grid-table object (for matrices)
/// - data: 2D array of cells
/// - show-indices: Whether to show column indices as headers
#let grid-data(
  data,
  show-indices: false,
  style: (:),
) = (
  type: "grid-data",
  data: data,
  show-indices: show-indices,
  style: style,
)

// =====================================================
// RENDERING FUNCTIONS
// =====================================================

/// Renders a table-data object
#let render-table(obj, theme) = {
  let headers = obj.headers
  let data = obj.data
  let style = obj.style

  let header-fill = style.at("header-fill", default: theme.blocks.theorem.fill)
  let stroke-color = style.at("stroke-color", default: theme.blocks.theorem.stroke.transparentize(50%))
  let row-fill = style.at("row-fill", default: (theme.page-fill, theme.blocks.definition.fill.transparentize(50%)))

  let num-cols = headers.len()
  let align-cols = style.at("align-cols", default: (center,) * num-cols)

  table(
    columns: (auto,) * num-cols,
    align: (col, row) => {
      if row == 0 { center } else { align-cols.at(calc.min(col, align-cols.len() - 1)) }
    },
    fill: (col, row) => {
      if row == 0 {
        header-fill
      } else {
        row-fill.at(calc.rem(row - 1, row-fill.len()))
      }
    },
    stroke: (x, y) => {
      if y == 0 {
        (bottom: 2pt + stroke-color, rest: 1pt + stroke-color)
      } else if y == 1 {
        (top: 2pt + stroke-color, rest: 1pt + stroke-color)
      } else {
        1pt + stroke-color
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

/// Renders a grid-data object
#let render-grid(obj, theme) = {
  let data = obj.data
  let show-indices = obj.show-indices
  let style = obj.style

  let num-cols = if data.len() > 0 { data.at(0).len() } else { 0 }

  if show-indices {
    let headers = range(num-cols).map(i => str(i))
    render-table(table-data(headers, data, style: style), theme)
  } else {
    let stroke-color = style.at("stroke-color", default: theme.blocks.theorem.stroke.transparentize(50%))
    let row-fill = style.at("row-fill", default: (theme.page-fill, theme.blocks.definition.fill.transparentize(50%)))

    table(
      columns: (auto,) * num-cols,
      align: center,
      fill: (col, row) => row-fill.at(calc.rem(row, row-fill.len())),
      stroke: 1pt + stroke-color,
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
