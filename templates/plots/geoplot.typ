#import "@preview/cetz:0.4.2"
#import "@preview/cetz-plot:0.1.3": plot
#import "../../config.typ": render-sample-count

/// Draws a point on a 2D or 3D plot with optional label.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - xy: Coordinate tuple (x, y) for 2D or (x, y, z) for 3D
/// - label-content: Content to display as label
/// - pos: Anchor position for label (default: "west")
/// - padding: Padding around label (default: 0.2)
/// - color: Point fill color (default: theme.plot.highlight)
#let point(theme: (:), xy, label-content, pos: "west", padding: 0.2, color: auto) = {
  let fill-col = if color == auto { theme.plot.highlight } else { color }

  if xy.len() == 3 {
    // 3D mode: Raw draw for spaceplot
    import cetz.draw: *
    circle(xy, radius: 0.05, fill: fill-col, stroke: none)
    content(xy, padding: padding, anchor: pos, text(fill: theme.plot.stroke, label-content))
  } else {
    // 2D mode: Plot item for rect-plot
    plot.add((xy,), mark: "o", mark-style: (fill: fill-col, stroke: none))
    plot.annotate({
      import cetz.draw: *
      content(xy, padding: padding, anchor: pos, text(fill: theme.plot.stroke, label-content))
    })
  }
}

/// Adds a polar curve to a plot by converting polar coordinates to Cartesian.
///
/// Parameters:
/// - func: Function r(θ) defining the polar curve
/// - domain: Range of θ values (default: (0, 2π))
/// - style: Plot style dictionary
#let add-polar(func, domain: (0, 2 * calc.pi), style: (:)) = {
  plot.add(
    domain: domain,
    samples: render-sample-count,

    t => (func(t) * calc.cos(t), func(t) * calc.sin(t)),
    style: style,
  )
}

/// Draws an angle arc between two rays from an origin point.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - origin: Origin point of the angle (x, y) or (x, y, z)
/// - start-ang: Starting angle in degrees or radians
/// - delta: Angular width (positive = counterclockwise)
/// - label: Label content to display
/// - radius: Arc radius (default: 0.5)
/// - label-dist: Distance from origin to label (default: auto)
/// - col: Angle color (default: green)
#let add-angle(theme: (:), origin, start-ang, delta, label, radius: 0.5, label-dist: 0, col: green) = {
  let fill-color = if type(col) == color { col.transparentize(70%) } else { none }
  let label-radius = if label-dist == 0 { radius * 7 / 5 } else { label-dist }

  // Note: Currently only supports 2D angles
  // 3D angle support requires specifying the plane of rotation

  let starting = if delta.deg() >= 0 { (origin.at(0) + calc.cos(start-ang), origin.at(1) + calc.sin(start-ang)) } else {
    (origin.at(0) + calc.cos(start-ang + delta), origin.at(1) + calc.sin(start-ang + delta))
  }
  let ending = if delta.deg() <= 0 { (origin.at(0) + calc.cos(start-ang), origin.at(1) + calc.sin(start-ang)) } else {
    (origin.at(0) + calc.cos(start-ang + delta), origin.at(1) + calc.sin(start-ang + delta))
  }
  plot.annotate({
    cetz.angle.angle(
      origin,
      starting,
      ending,
      label: text(col, label),
      fill: fill-color,
      radius: radius,
      label-radius: label-radius,
      stroke: (theme.plot.stroke),
    )
  })
}

/// Draws a right angle (90°) marker at a specified orientation.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - origin: Origin point of the angle (x, y) or (x, y, z)
/// - start-ang: Starting angle in degrees or radians
/// - radius: Marker size (default: 0.5)
/// - label-dist: Unused parameter (kept for compatibility)
#let add-right-angle(theme: (:), origin, start-ang, radius: 0.5, label-dist: 0) = {
  let delta = 90deg
  let starting = if delta.deg() >= 0 { (origin.at(0) + calc.cos(start-ang), origin.at(1) + calc.sin(start-ang)) } else {
    (origin.at(0) + calc.cos(start-ang + delta), origin.at(1) + calc.sin(start-ang + delta))
  }
  let ending = if delta.deg() <= 0 { (origin.at(0) + calc.cos(start-ang), origin.at(1) + calc.sin(start-ang)) } else {
    (origin.at(0) + calc.cos(start-ang + delta), origin.at(1) + calc.sin(start-ang + delta))
  }
  plot.annotate({
    cetz.angle.right-angle(
      origin,
      starting,
      ending,
      label: "",
      radius: radius,
      stroke: (theme.plot.stroke),
    )
  })
}

/// Draws a rotated coordinate system with X and Y axes.
///
/// Parameters:
/// - phi-ang: Rotation angle of the coordinate system
/// - scale: Length scale factor for axes
/// - rad: Radius of angle marker (default: auto-calculated)
/// - X-pad: Padding for X label (default: 0)
/// - Y-pad: Padding for Y label (default: 0)
/// - X-pos: Anchor position for X label (default: "west")
/// - Y-pos: Anchor position for Y label (default: "north-east")
#let add-xy-axes(phi-ang, scale, rad: 0, X-pad: 0, Y-pad: 0, X-pos: "west", Y-pos: "north-east") = {
  import "../templater.typ": active-theme
  let radrad = if rad == 0 { scale / 6 } else { rad }
  scale = scale * calc.sqrt(2)
  plot.annotate({
    cetz.draw.line(
      (-scale * calc.cos(phi-ang), -scale * calc.sin(phi-ang)),
      (scale * calc.cos(phi-ang), scale * calc.sin(phi-ang)),
      name: "X",
      stroke: (paint: gray, dash: "dashed"),
      mark: (end: "stealth", scale: scale / 4),
    )
    cetz.draw.line(
      (-scale * calc.cos(phi-ang + 90deg), -scale * calc.sin(phi-ang + 90deg)),
      (scale * calc.cos(phi-ang + 90deg), scale * calc.sin(phi-ang + 90deg)),
      name: "Y",
      stroke: (paint: gray, dash: "dashed"),
      mark: (end: "stealth", scale: scale / 4),
    )
    cetz.draw.content("X.end", $X$, anchor: X-pos, padding: X-pad)
    cetz.draw.content("Y.end", $Y$, anchor: Y-pos, padding: Y-pad)
  })
  add-angle((0, 0), 0deg, phi-ang, $phi$, col: color.green, radius: radrad, theme: active-theme)
}

/// Draws a polygon with optional fill and label.
/// Automatically detects 2D vs 3D based on coordinate dimensions.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - points: Array of coordinate tuples
/// - fill: Fill color (default: none)
/// - stroke: Stroke style (default: theme.plot.stroke)
/// - label: Optional label to place at polygon centroid
/// - label-color: Label text color (default: theme.plot.stroke)
#let add-polygon(theme: (:), points, fill: none, stroke: auto, label: none, label-color: auto) = {
  let stroke-style = if stroke == auto { (paint: theme.plot.stroke) } else { stroke }
  let txt-color = if label-color == auto { theme.plot.stroke } else { label-color }

  let is-3d = points.any(p => p.len() == 3)

  let draw-cmd = {
    import cetz.draw: *
    group({
      // In plot.annotate context, we can't use fill parameter
      // So we just draw the outline
      line(..points, close: true, stroke: stroke-style)

      if label != none {
        let sum-x = 0
        let sum-y = 0
        let sum-z = 0
        for p in points {
          sum-x += p.at(0)
          sum-y += p.at(1)
          if p.len() > 2 { sum-z += p.at(2) }
        }
        let center = if is-3d {
          (sum-x / points.len(), sum-y / points.len(), sum-z / points.len())
        } else {
          (sum-x / points.len(), sum-y / points.len())
        }
        content(center, text(fill: txt-color, label))
      }
    })
  }

  if is-3d {
    // 3D mode: Raw draw
    draw-cmd
  } else {
    // 2D mode: Annotate
    plot.annotate(draw-cmd)
  }
}
