// =====================================================
// POLAR CANVAS - Polar coordinate system
// =====================================================

#import "@preview/cetz:0.4.2"
#import "@preview/cetz-plot:0.1.3": plot
#import "draw.typ": draw-func-obj, draw-geo

/// Create a polar coordinate canvas
/// Renders geometry objects with circular grid and radial lines.
///
/// Parameters:
/// - theme: Theme dictionary for styling
/// - size: Canvas size as (width, height) (default: (10, 10))
/// - radius: Maximum radius (default: 5)
/// - tick: Radial tick spacing (default: 1)
/// - margin: Extra margin beyond radius (default: 0.5)
/// - show-angles: Whether to show angle labels (default: true)
/// - ..objects: Geometry objects to render
#let polar-canvas(
  theme: (:),
  size: (10, 10),
  radius: 5,
  tick: 1,
  margin: 0.5,
  show-angles: true,
  ..objects,
) = {
  let stroke-col = theme.at("plot", default: (:)).at("stroke", default: black)
  let grid-col = theme.at("plot", default: (:)).at("grid", default: gray)
  let effective-radius = radius + margin

  cetz.canvas({
    import cetz.draw: *

    set-style(stroke: stroke-col, fill: stroke-col)

    plot.plot(
      size: size,
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
        // Workaround for cetz-plot crash: initialize data bounds
        plot.add(((0, 0),), style: (stroke: none), mark: none)

        // Draw polar grid as annotation
        plot.annotate({
          on-layer(-1, {
            // Concentric circles
            let num-circles = calc.floor(radius / tick)
            for i in range(1, num-circles + 1) {
              let r = i * tick
              circle((0, 0), radius: r, stroke: (paint: grid-col, thickness: 0.75pt), fill: none)
            }

            // Radial lines (every 30°)
            for deg in range(0, 180, step: 30) {
              line(
                (calc.cos(deg * 1deg) * effective-radius, calc.sin(deg * 1deg) * effective-radius),
                (calc.cos((deg + 180) * 1deg) * effective-radius, calc.sin((deg + 180) * 1deg) * effective-radius),
                stroke: (paint: grid-col, thickness: 0.75pt),
              )
            }

            // Polar axis (bold arrow)
            line(
              (0, 0),
              (effective-radius, 0),
              stroke: (paint: stroke-col, thickness: 1pt),
              mark: (end: ">", fill: stroke-col),
            )

            // Radius tick labels
            for i in range(1, num-circles + 1) {
              let r = i * tick
              let label = if calc.rem(r, 1) == 0 { str(int(r)) } else { str(calc.round(r, digits: 2)) }
              content((r, -0.3), text(fill: stroke-col, size: 7.5pt, label), anchor: "north")
            }

            // Angle labels
            if show-angles {
              for deg in (0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330) {
                let rad = deg * 1deg
                let label-r = effective-radius + 0.3
                let anchor = if deg == 0 { "west" } else if deg == 90 { "south" } else if deg == 180 {
                  "east"
                } else if deg == 270 { "north" } else if deg < 90 { "south-west" } else if deg < 180 {
                  "south-east"
                } else if deg < 270 { "north-east" } else { "north-west" }

                content(
                  (label-r * calc.cos(rad), label-r * calc.sin(rad)),
                  text(fill: stroke-col, size: 7pt, $#deg degree$),
                  anchor: anchor,
                )
              }
            }
          })
        })

        // Draw geometry objects
        let bounds = (x: (-effective-radius, effective-radius), y: (-effective-radius, effective-radius))

        for obj in objects.pos() {
          if type(obj) == dictionary {
            let t = obj.at("type", default: none)
            if t == "func" {
              draw-func-obj(obj, theme)
            } else if t != none {
              plot.annotate({ draw-geo(obj, theme, bounds: bounds) })
            }
          }
        }
      },
    )
  })
}
