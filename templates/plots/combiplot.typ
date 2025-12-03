#import "@preview/cetz:0.4.2"

/// Visualizes combinatorics problems using boxes and balls.
/// Displays a row of boxes with filled circles representing items.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - n-boxes: Number of boxes to draw
/// - counts: Array of ball counts for each box
/// - x: X-coordinate offset (default: 0)
/// - y: Y-coordinate offset (default: 0)
/// - label: Optional label to display below the boxes
#let draw-boxes(theme: (:), n-boxes, counts, x: 0, y: 0, label: none) = {
  import cetz.draw: *
  let stroke-col = theme.plot.stroke
  let fill-col = theme.plot.highlight

  let box-width = 1.2
  let box-height = 2.5
  let spacing = 0.5
  let ball-radius = 0.25
  let start-x = float(x)
  let start-y = float(y)

  for i in range(n-boxes) {
    let current-x = start-x + i * (box-width + spacing)
    let n-balls = counts.at(i, default: 0)

    line(
      (current-x, start-y + box-height),
      (current-x, start-y),
      (current-x + box-width, start-y),
      (current-x + box-width, start-y + box-height),
      stroke: (paint: stroke-col, thickness: 1.5pt),
    )

    for b in range(n-balls) {
      let ball-cx = current-x + (box-width / 2)
      let ball-cy = start-y + ball-radius + (b * ball-radius * 2.1)

      circle(
        (ball-cx, ball-cy),
        radius: ball-radius * 0.85,
        fill: fill-col,
        stroke: none,
      )
    }
  }

  if label != none {
    let total-width = (n-boxes * box-width) + ((n-boxes - 1) * spacing)
    let center-x = start-x + (total-width / 2)
    content((center-x, start-y - 0.5), text(fill: stroke-col, label))
  }
}


/// Draws a linear arrangement of items (e.g., for permutations).
/// Items are displayed in a horizontal row of circles.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - items: Array of items to display (can be numbers, letters, etc.)
/// - x: X-coordinate offset (default: 0)
/// - y: Y-coordinate offset (default: 0)
/// - label: Optional label to display below the arrangement
#let draw-linear(theme: (:), items, x: 0, y: 0, label: none) = {
  import cetz.draw: *

  let stroke-col = theme.text-accent
  let text-col = theme.text-main

  let ball-radius = 0.4
  let spacing = 0.4
  let start-x = float(x)
  let start-y = float(y)

  for (i, item) in items.enumerate() {
    let current-x = start-x + i * (ball-radius * 2 + spacing)

    circle(
      (current-x, start-y),
      radius: ball-radius,
      stroke: (paint: stroke-col, thickness: 1.5pt),
      fill: none,
    )

    content(
      (current-x, start-y),
      text(fill: text-col, weight: "bold")[#item],
    )
  }

  if label != none {
    let total-width = (items.len() * ball-radius * 2) + ((items.len() - 1) * spacing)
    let center-x = start-x + (total-width / 2) - ball-radius
    content((center-x, start-y - 1), text(fill: stroke-col, label))
  }
}


/// Draws a circular arrangement of items (e.g., for circular permutations).
/// Items are displayed around a circle.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - items: Array of items to display
/// - x: X-coordinate of circle center (default: 0)
/// - y: Y-coordinate of circle center (default: 0)
/// - radius: Radius of the arrangement circle (default: 1.5)
/// - label: Optional label to display at center
#let draw-circular(theme: (:), items, x: 0, y: 0, radius: 1.5, label: none) = {
  import cetz.draw: *

  let fill-col = theme.plot.highlight
  let grid-col = theme.plot.stroke

  let n = items.len()
  let ball-radius = 0.4
  let start-x = float(x)
  let start-y = float(y)

  // Draw dashed circle
  circle(
    (start-x, start-y),
    radius: radius,
    stroke: (paint: grid-col, dash: "dashed", thickness: 0.5pt),
  )

  for (i, item) in items.enumerate() {
    // Start at top (90°) and go clockwise
    let angle = 90deg - (i * 360deg / n)

    let cx = start-x + radius * calc.cos(angle)
    let cy = start-y + radius * calc.sin(angle)

    circle(
      (cx, cy),
      radius: ball-radius,
      fill: fill-col,
      stroke: none,
    )

    content(
      (cx, cy),
      text(fill: theme.text-main, weight: "bold")[#item],
    )
  }

  if label != none {
    content(
      (start-x, start-y),
      text(fill: theme.text-accent, weight: "bold", label),
    )
  }
}
