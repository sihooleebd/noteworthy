#import "@preview/cetz:0.4.2"
#import "@preview/cetz-plot:0.1.3": plot

/// Creates a rectangular coordinate plot with labeled axes and grid.
/// This is the standard Cartesian plotting environment for 2D functions.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - size: Canvas size as (width, height) tuple (default: auto → (10, 10))
/// - x-domain: X-axis range as (min, max) (default: (-4.5, 5.5))
/// - y-domain: Y-axis range as (min, max) (default: (-5.5, 5.5))
/// - x-tick: X-axis tick spacing (default: 1)
/// - y-tick: Y-axis tick spacing (default: 1)
/// - body: Plot content (functions, points, annotations)
/// - draw-content: Additional CeTZ drawing commands (optional)
#let rect-plot(
  theme: (:),
  size: auto,
  x-domain: (-4.5, 5.5),
  y-domain: (-5.5, 5.5),
  x-tick: 1,
  y-tick: 1,
  body,
  draw-content: none,
) = {
  let actual-size = if size == auto { (10, 10) } else { size }
  cetz.canvas({
    import cetz.draw: *

    set-style(
      stroke: theme.plot.stroke,
      fill: none,
    )

    plot.plot(
      size: actual-size,
      axis-style: "school-book",
      x-tick-step: x-tick,
      y-tick-step: y-tick,
      x-grid: false,
      y-grid: false,

      legend-style: (
        stroke: theme.plot.stroke,
        fill: none,
        padding: 0.5,
        item: (spacing: 0.5),
      ),

      x-label: text(fill: theme.plot.stroke, $x$),
      y-label: text(fill: theme.plot.stroke, $y$),

      x-format: x => text(fill: theme.plot.stroke, size: 8pt, str(x)),
      y-format: y => text(fill: theme.plot.stroke, size: 8pt, str(y)),

      x-min: x-domain.at(0),
      x-max: x-domain.at(1),
      y-min: y-domain.at(0),
      y-max: y-domain.at(1),

      {
        body
        if draw-content != none {
          plot.annotate({
            draw-content
          })
        }
      },
    )
  })
}


/// Creates a polar coordinate plot with concentric circles and radial lines.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - size: Canvas size as (width, height) tuple (default: auto → (10, 10))
/// - radius: Maximum radius for polar grid (default: 5.5)
/// - tick: Radial tick spacing (default: 1)
/// - margin: Extra margin beyond radius (default: 0.5)
/// - body: Plot content (polar curves, points)
/// - draw-content: Additional CeTZ drawing commands (optional)
#let polar-plot(
  theme: (:),
  size: auto,
  radius: 5.5,
  tick: 1,
  margin: 0.5,
  body,
  draw-content: none,
) = {
  let actual-size = if size == auto { (10, 10) } else { size }
  let effective-radius = radius + margin
  let grid-color = theme.plot.grid

  cetz.canvas({
    import cetz.draw: *
    set-style(
      stroke: theme.plot.stroke,
      fill: theme.plot.stroke,
    )

    plot.plot(
      size: actual-size,
      axis-style: none,
      x-tick-step: none,
      y-tick-step: none,
      x-grid: false,
      y-grid: false,
      x-min: -effective-radius,
      x-max: effective-radius,
      y-min: -effective-radius,
      y-max: effective-radius,
      {
        // Draw polar grid inside plot coordinate system
        plot.annotate({
          on-layer(
            -1,
            {
              // Draw concentric circles
              let num-circles = calc.floor(radius / tick)
              for i in range(1, num-circles + 1) {
                let r = i * tick
                circle((0, 0), radius: r, stroke: (paint: grid-color, thickness: 0.75pt), fill: none)
              }
              // Draw radial lines
              for deg in range(0, 180, step: 30) {
                line(
                  (calc.cos(deg * 1deg) * effective-radius, calc.sin(deg * 1deg) * effective-radius),
                  (calc.cos((deg + 180) * 1deg) * effective-radius, calc.sin((deg + 180) * 1deg) * effective-radius),
                  stroke: (paint: grid-color, thickness: 0.75pt),
                )
              }
              // Draw polar axis (bold line from origin to right with arrow)
              line(
                (0, 0),
                (effective-radius, 0),
                stroke: (paint: theme.plot.stroke, thickness: 1pt),
                mark: (end: ">", fill: theme.plot.stroke),
              )

              // Add radius tick labels along polar axis
              for i in range(1, num-circles + 1) {
                let r = i * tick
                let label = if calc.rem(r, 1) == 0 { str(int(r)) } else { str(calc.round(r, digits: 2)) }
                content((r, -0.3), text(fill: theme.plot.stroke, size: 7.5pt, label), anchor: "north")
              }

              if draw-content != none {
                draw-content
              }
            },
          )
        })

        // Draw the actual polar curve
        body
      },
    )
  })
}

/// Creates a simple canvas for drawing combinatorics diagrams.
/// No axes or grids, just a blank CeTZ canvas.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - body: Drawing commands
#let combi-plot(
  theme: (:),
  body,
) = {
  cetz.canvas({
    import cetz.draw: *
    set-style(stroke: theme.plot.stroke, fill: none)
    body
  })
}

/// Creates a coordinate system without visible axes for custom drawings.
/// Useful for diagrams where you need coordinate mapping but no visible grid.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - size: Canvas size as (width, height) tuple (default: auto → (10, 10))
/// - x-domain: X-axis range for coordinate mapping (default: (-5, 5))
/// - y-domain: Y-axis range for coordinate mapping (default: (-5, 5))
/// - body: Plot content
/// - draw-content: Additional CeTZ drawing commands (optional)
#let blank-plot(
  theme: (:),
  size: auto,
  x-domain: (-5, 5),
  y-domain: (-5, 5),
  body,
  draw-content: none,
) = {
  let actual-size = if size == auto { (10, 10) } else { size }
  cetz.canvas({
    import cetz.draw: *

    set-style(stroke: theme.plot.stroke, fill: theme.plot.stroke)

    plot.plot(
      size: actual-size,
      axis-style: none,
      x-grid: false,
      y-grid: false,

      x-min: x-domain.at(0),
      x-max: x-domain.at(1),
      y-min: y-domain.at(0),
      y-max: y-domain.at(1),

      {
        body

        if draw-content != none {
          plot.annotate({
            draw-content
          })
        }
      },
    )
  })
}
