// =====================================================
// BLANK CANVAS - Simple canvas without axes
// =====================================================

#import "@preview/cetz:0.4.2"
#import "draw.typ": draw-geo

/// Create a blank canvas for diagrams
/// No axes or grid, just a drawing area.
///
/// Parameters:
/// - theme: Theme dictionary for styling
/// - size: Canvas dimensions (default: auto)
/// - ..objects: Geometry objects to render
#let blank-canvas(
  theme: (:),
  size: auto,
  ..objects,
) = {
  let stroke-col = theme.at("plot", default: (:)).at("stroke", default: black)

  cetz.canvas({
    import cetz.draw: *
    set-style(stroke: stroke-col, fill: none)

    let bounds = (x: (-10, 10), y: (-10, 10))

    for obj in objects.pos() {
      if type(obj) == dictionary and obj.at("type", default: none) != none {
        draw-geo(obj, theme, bounds: bounds)
      } else {
        obj
      }
    }
  })
}

/// Create a simple canvas with custom drawing commands
/// Useful for direct CeTZ usage with theme styling.
///
/// Parameters:
/// - theme: Theme dictionary for styling
/// - body: CeTZ drawing commands
#let simple-canvas(
  theme: (:),
  body,
) = {
  let stroke-col = theme.at("plot", default: (:)).at("stroke", default: black)

  cetz.canvas({
    import cetz.draw: *
    set-style(stroke: stroke-col, fill: none)
    body
  })
}
