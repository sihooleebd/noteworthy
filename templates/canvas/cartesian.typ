// =====================================================
// CARTESIAN CANVAS - 2D rectangular coordinate system
// =====================================================

#import "@preview/cetz:0.4.2"
#import "@preview/cetz-plot:0.1.3": plot
#import "draw.typ": draw-data-series-obj, draw-func-obj, draw-geo

/// Create a Cartesian (rectangular) coordinate canvas
/// Renders geometry objects with x-y axes.
///
/// Parameters:
/// - theme: Theme dictionary for styling
/// - size: Canvas size as (width, height) (default: (10, 10))
/// - x-domain: X-axis range as (min, max) (default: (-5, 5))
/// - y-domain: Y-axis range as (min, max) (default: (-5, 5))
/// - x-tick: X-axis tick spacing (default: 1)
/// - y-tick: Y-axis tick spacing (default: 1)
/// - show-grid: Whether to show grid lines (default: false)
/// - axis-style: Style of axes - "school-book", "scientific", or none (default: "school-book")
/// - ..objects: Geometry objects to render
#let cartesian-canvas(
  theme: (:),
  size: (10, 10),
  x-domain: (-5, 5),
  y-domain: (-5, 5),
  x-tick: 1,
  y-tick: 1,
  show-grid: false,
  axis-style: "school-book",
  ..objects,
) = {
  let stroke-col = theme.at("plot", default: (:)).at("stroke", default: black)
  let grid-col = theme.at("plot", default: (:)).at("grid", default: gray)

  cetz.canvas({
    import cetz.draw: *

    set-style(
      stroke: stroke-col,
      fill: none,
    )

    plot.plot(
      size: size,
      axis-style: axis-style,
      x-tick-step: x-tick,
      y-tick-step: y-tick,
      x-grid: show-grid,
      y-grid: show-grid,

      x-label: text(fill: stroke-col, $x$),
      y-label: text(fill: stroke-col, $y$),

      x-format: x => text(fill: stroke-col, size: 8pt, str(x)),
      y-format: y => text(fill: stroke-col, size: 8pt, str(y)),

      x-min: x-domain.at(0),
      x-max: x-domain.at(1),
      y-min: y-domain.at(0),
      y-max: y-domain.at(1),

      {
        // Workaround for cetz-plot annotation crash: initialize data bounds
        plot.add(((0, 0),), style: (stroke: none), mark: none)

        // Draw all objects
        let bounds = (x: x-domain, y: y-domain)

        for obj in objects.pos() {
          if type(obj) == dictionary {
            let t = obj.at("type", default: none)

            if t == "func" {
              // Functions need to be added via plot.add (with adaptive sampling context)
              draw-func-obj(obj, theme, x-domain: x-domain, y-domain: y-domain, size: size)
            } else if t == "data-series" {
              // Data series are drawn via plot context
              draw-data-series-obj(obj, theme, x-domain: x-domain, y-domain: y-domain)
            } else if t != none {
              // Other geometry objects are drawn via annotate
              let aspect = (x-domain, y-domain, size.at(0), size.at(1))
              plot.annotate({
                draw-geo(obj, theme, bounds: bounds, aspect: aspect)
              })
            }
          } else if type(obj) == array {
            // Handle arrays of objects
            for sub-obj in obj {
              if type(sub-obj) == dictionary and sub-obj.at("type", default: none) == "func" {
                draw-func-obj(sub-obj, theme, x-domain: x-domain, y-domain: y-domain, size: size)
              } else if type(sub-obj) == dictionary and sub-obj.at("type", default: none) == "data-series" {
                draw-data-series-obj(sub-obj, theme, x-domain: x-domain, y-domain: y-domain)
              } else if type(sub-obj) == dictionary {
                let aspect = (x-domain, y-domain, size.at(0), size.at(1))
                plot.annotate({
                  draw-geo(sub-obj, theme, bounds: bounds, aspect: aspect)
                })
              }
            }
          }
        }
      },
    )
  })
}

/// Shorthand for a plot with functions only
#let graph-canvas(
  theme: (:),
  size: (10, 8),
  x-domain: (-5, 5),
  y-domain: (-5, 5),
  ..funcs,
) = {
  cartesian-canvas(
    theme: theme,
    size: size,
    x-domain: x-domain,
    y-domain: y-domain,
    axis-style: "school-book",
    ..funcs,
  )
}

/// Canvas with pi-labeled x-axis (for trigonometric functions)
#let trig-canvas(
  theme: (:),
  size: (10, 8),
  x-domain: (-2 * calc.pi, 2 * calc.pi),
  y-domain: (-2, 2),
  pi-divisor: 2, // Tick every π/pi-divisor
  ..objects,
) = {
  let stroke-col = theme.at("plot", default: (:)).at("stroke", default: black)

  let d = pi-divisor
  let gcd(a, b) = if b == 0 { a } else { gcd(b, calc.rem(a, b)) }

  let x-format = x => {
    let n = int(calc.round(x * d / calc.pi))
    let g = gcd(calc.abs(n), d)
    let num = calc.quo(n, g)
    let denom = calc.quo(d, g)

    text(fill: stroke-col, size: 8pt, {
      if num == 0 { $0$ } else if denom == 1 {
        if num == 1 { $pi$ } else if num == -1 { $-pi$ } else { $#num pi$ }
      } else {
        if num == 1 { $pi / #denom$ } else if num == -1 { $-pi / #denom$ } else { $#num / #denom pi$ }
      }
    })
  }

  cetz.canvas({
    import cetz.draw: *

    set-style(stroke: stroke-col, fill: none)

    plot.plot(
      size: size,
      axis-style: "school-book",
      x-tick-step: calc.pi / d,
      y-tick-step: 1,

      x-label: text(fill: stroke-col, $x$),
      y-label: text(fill: stroke-col, $y$),

      x-format: x-format,
      y-format: y => text(fill: stroke-col, size: 8pt, str(y)),

      x-min: x-domain.at(0),
      x-max: x-domain.at(1),
      y-min: y-domain.at(0),
      y-max: y-domain.at(1),

      {
        let bounds = (x: x-domain, y: y-domain)
        for obj in objects.pos() {
          if type(obj) == dictionary {
            let t = obj.at("type", default: none)
            if t == "func" { draw-func-obj(obj, theme, x-domain: x-domain, y-domain: y-domain, size: size) } else if (
              t != none
            ) {
              plot.annotate({ draw-geo(obj, theme, bounds: bounds) })
            }
          }
        }
      },
    )
  })
}
