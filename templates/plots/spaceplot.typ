#import "@preview/cetz:0.4.2"

/// Draws a 3D coordinate system with axes, grid, and optional tick marks.
/// This function creates a complete 3D plotting environment.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - x-domain: Range for X axis as (min, max) (default: (0, 5))
/// - y-domain: Range for Y axis as (min, max) (default: (0, 5))
/// - z-domain: Range for Z axis as (min, max) (default: (0, 4))
/// - view: Camera rotation angles as (x:, y:, z:) dictionary (default: standard isometric view)
/// - step: Grid line spacing (default: 1)
/// - x-label: Label for X axis (default: $x$)
/// - y-label: Label for Y axis (default: $y$)
/// - z-label: Label for Z axis (default: $z$)
/// - draw-axes: Whether to draw coordinate axes (default: true)
/// - draw-grid: Whether to draw XY grid at z=0 (default: true)
/// - draw-ticks: Whether to draw tick marks on axes (default: false)
/// - body: Content to draw within the 3D coordinate system
#let space-plot(
  theme: (:),
  x-domain: (0, 5),
  y-domain: (0, 5),
  z-domain: (0, 4),
  // Default view: Z pointing up, X left, Y right
  view: (x: -90deg, y: -120deg, z: 0deg),
  step: 1,
  x-label: $x$,
  y-label: $y$,
  z-label: $z$,
  draw-axes: true,
  draw-grid: true,
  draw-ticks: false,
  body,
) = {
  import cetz.draw: *

  // Define styles from theme
  let axis-color = theme.at("text-main", default: black)
  let grid-color = theme.at("plot", default: (:)).at("grid", default: gray)

  let axis-style = (paint: axis-color, thickness: 1pt)
  let grid-style = (paint: grid-color, thickness: 0.5pt)
  let tick-style = (paint: axis-color, thickness: 1pt)

  cetz.canvas({
    // Apply rotation to achieve desired 3D view
    rotate(x: view.at("x", default: 0deg), y: view.at("y", default: 0deg), z: view.at("z", default: 0deg))

    let (x-min, x-max) = x-domain
    let (y-min, y-max) = y-domain
    let (z-min, z-max) = z-domain

    // --- DRAW GRID ---
    if draw-grid {
      for i in range(int(x-min / step), int(x-max / step) + 1) {
        let x = i * step
        line((x, y-min, 0), (x, y-max, 0), stroke: grid-style)
      }
      for i in range(int(y-min / step), int(y-max / step) + 1) {
        let y = i * step
        line((x-min, y, 0), (x-max, y, 0), stroke: grid-style)
      }
    }

    // --- DRAW AXES ---
    if draw-axes {
      // Z-Axis (vertical)
      line((0, 0, 0), (0, 0, z-max + 1), stroke: axis-style, name: "z-axis")
      content((0, 0, z-max + 1.2), z-label)

      // X-Axis
      line((0, 0, 0), (x-max + 1, 0, 0), stroke: axis-style, name: "x-axis")
      content((x-max + 1.2, 0, 0), x-label)

      // Y-Axis
      line((0, 0, 0), (0, y-max + 1, 0), stroke: axis-style, name: "y-axis")
      content((0, y-max + 1.2, 0), y-label)

      // --- DRAW TICKS ---
      if draw-ticks {
        let tick-len = 0.2
        // X-ticks
        for i in range(int(x-min / step), int(x-max / step) + 1) {
          if i != 0 {
            let x = i * step
            line((x, 0, -tick-len), (x, 0, tick-len), stroke: tick-style)
          }
        }
        // Y-ticks
        for i in range(int(y-min / step), int(y-max / step) + 1) {
          if i != 0 {
            let y = i * step
            line((0, y, -tick-len), (0, y, tick-len), stroke: tick-style)
          }
        }
        // Z-ticks
        for i in range(int(z-min / step), int(z-max / step) + 1) {
          if i != 0 {
            let z = i * step
            line((-tick-len, 0, z), (tick-len, 0, z), stroke: tick-style)
          }
        }
      }
    }

    // Draw the user content
    body
  })
}
