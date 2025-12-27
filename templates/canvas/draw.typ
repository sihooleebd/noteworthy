// =====================================================
// DRAW - Rendering functions for geometry objects
// =====================================================
// Converts geometry objects to CeTZ drawing commands.
// Theme-aware rendering with automatic styling.

#import "@preview/cetz:0.4.2"
#import "@preview/cetz-plot:0.1.3": plot
#import "../geometry/func.typ": adaptive-sample

// =====================================================
// Style Helpers
// =====================================================

/// Get point style from theme and object
#let get-point-style(obj, theme) = {
  let base = (
    fill: theme.at("plot", default: (:)).at("highlight", default: black),
    stroke: none,
    radius: 0.08,
  )

  if obj.style != auto and obj.style != none {
    base + obj.style
  } else {
    base
  }
}

/// Get line style from theme and object
#let get-line-style(obj, theme) = {
  let base = (
    stroke: (paint: theme.at("plot", default: (:)).at("stroke", default: black), thickness: 1pt),
  )

  if obj.style != auto and obj.style != none {
    base + obj.style
  } else {
    base
  }
}

/// Get fill style for polygons/circles
#let get-fill-style(obj, theme) = {
  if obj.at("fill", default: none) != none {
    obj.fill
  } else {
    none
  }
}

/// Compute smart label position for a vector in a group
/// Returns: (position, anchor) tuple
/// Parameters:
/// - vec: The vector object (with x, y components)
/// - origin: Origin point (x, y)
/// - all-angles: Array of all vector angles in the group (in degrees, 0-360)
/// - this-angle: This vector's angle (in degrees)
/// - theme: Theme for background color
#let compute-vector-label-pos(vec, origin, all-angles, this-angle, theme) = {
  let sx = origin.at(0)
  let sy = origin.at(1)
  let vx = vec.x
  let vy = vec.y
  let len = calc.sqrt(vx * vx + vy * vy)

  if len == 0 {
    return ((sx, sy), "south")
  }

  // Unit vectors
  let ux = vx / len
  let uy = vy / len
  let nx-ccw = -uy // Perpendicular CCW
  let ny-ccw = ux
  let nx-cw = uy // Perpendicular CW
  let ny-cw = -ux

  // Midpoint
  let mid = (sx + vx / 2, sy + vy / 2)

  // Compute angular span if multiple vectors
  if all-angles.len() < 2 {
    // Single vector - use CCW perpendicular
    let offset = 0.3
    let pos = (mid.at(0) + nx-ccw * offset, mid.at(1) + ny-ccw * offset)
    let anchor = if ny-ccw >= 0 { "south" } else { "north" }
    return (pos, anchor)
  }

  // Sort angles to find span
  let sorted = all-angles.sorted()

  // Find angular span (handle wraparound)
  let max-gap = 0
  let gap-start = 0
  for i in range(sorted.len()) {
    let next-i = calc.rem(i + 1, sorted.len())
    let gap = if next-i == 0 { 360 - sorted.at(i) + sorted.at(0) } else { sorted.at(next-i) - sorted.at(i) }
    if gap > max-gap {
      max-gap = gap
      gap-start = sorted.at(next-i)
    }
  }

  // Angular span is 360 - max gap
  let span = 360 - max-gap

  // Leftmost = smallest angle after gap-start (CCW-most)
  // Rightmost = largest angle before gap-start wraps (CW-most)
  let leftmost = gap-start
  let rightmost = if gap-start == sorted.at(0) { sorted.last() } else {
    sorted.at(sorted.position(a => a == gap-start) - 1)
  }

  if span < 180 {
    // Use outer edges
    let offset = 0.3
    if calc.abs(this-angle - leftmost) < 1 {
      // Leftmost vector - CCW perpendicular
      let pos = (mid.at(0) + nx-ccw * offset, mid.at(1) + ny-ccw * offset)
      let anchor = if ny-ccw >= 0 { "south" } else { "north" }
      return (pos, anchor)
    } else if calc.abs(this-angle - rightmost) < 1 {
      // Rightmost vector - CW perpendicular
      let pos = (mid.at(0) + nx-cw * offset, mid.at(1) + ny-cw * offset)
      let anchor = if ny-cw >= 0 { "south" } else { "north" }
      return (pos, anchor)
    }
  }

  // Default: on-line with background (for middle vectors or span >= 180)
  (mid, "center")
}

/// Format label with intelligent substitution
#let format-label(obj, label) = {
  if type(label) != str { return label }

  let res = label

  // {angle} replacement
  if "{angle}" in res and obj.type == "angle" {
    let dx1 = obj.p1.x - obj.vertex.x
    let dy1 = obj.p1.y - obj.vertex.y
    let dx2 = obj.p2.x - obj.vertex.x
    let dy2 = obj.p2.y - obj.vertex.y
    let start-deg = calc.atan2(dy1, dx1).deg()
    let end-deg = calc.atan2(dy2, dx2).deg()
    if start-deg < 0 { start-deg += 360 }
    if end-deg < 0 { end-deg += 360 }
    // Strict CCW difference
    let diff = calc.rem(end-deg - start-deg + 360, 360)
    // Handle reflex override
    let is-reflex = obj.at("reflex", default: "auto")
    if is-reflex == "auto" {
      if diff > 180 { diff = 360 - diff }
    } else if is-reflex {
      diff = 360 - diff
    }

    // Round to reasonable decimals (e.g. integer if close)
    let val = if calc.abs(diff - calc.round(diff)) < 0.001 {
      str(int(calc.round(diff)))
    } else {
      str(calc.round(diff, digits: 1))
    }
    res = res.replace("{angle}", val + "°")
  }

  // {length} replacement (Segment, Vector)
  if "{length}" in res {
    let len = 0.0
    if obj.type == "segment" {
      let dx = obj.p2.x - obj.p1.x
      let dy = obj.p2.y - obj.p1.y
      let dz = if obj.p1.at("z", default: none) != none { obj.p2.z - obj.p1.z } else { 0 }
      len = calc.sqrt(dx * dx + dy * dy + dz * dz)
    } else if obj.type == "vector" {
      let dx = obj.x
      let dy = obj.y
      let dz = obj.at("z", default: 0)
      len = calc.sqrt(dx * dx + dy * dy + dz * dz)
    }

    let val = if calc.abs(len - calc.round(len)) < 0.001 {
      str(int(calc.round(len)))
    } else {
      str(calc.round(len, digits: 2))
    }
    res = res.replace("{length}", val)
  }

  // {radius} replacement
  if "{radius}" in res and (obj.type == "circle" or obj.type == "arc") {
    let val = str(calc.round(obj.radius, digits: 2))
    res = res.replace("{radius}", val)
  }

  // {area} replacement (Polygon, Circle)
  if "{area}" in res {
    let area = 0.0
    if obj.type == "circle" {
      area = calc.pi * obj.radius * obj.radius
    } else if obj.type == "polygon" {
      // Shoelace formula (2D only for now)
      let pts = obj.points
      let sum = 0.0
      for i in range(pts.len()) {
        let p1 = pts.at(i)
        let p2 = pts.at(calc.rem(i + 1, pts.len()))
        sum += p1.x * p2.y - p2.x * p1.y
      }
      area = calc.abs(sum) / 2.0
    }
    let val = str(calc.round(area, digits: 2))
    res = res.replace("{area}", val)
  }

  // {circum} replacement
  if "{circum}" in res {
    let circum = 0.0
    if obj.type == "circle" {
      circum = 2 * calc.pi * obj.radius
    } else if obj.type == "polygon" {
      let pts = obj.points
      for i in range(pts.len()) {
        let p1 = pts.at(i)
        let p2 = pts.at(calc.rem(i + 1, pts.len()))
        let dx = p2.x - p1.x
        let dy = p2.y - p1.y
        circum += calc.sqrt(dx * dx + dy * dy)
      }
    }
    let val = str(calc.round(circum, digits: 2))
    res = res.replace("{circum}", val)
  }

  res
}

// =====================================================
// Draw Functions for Each Object Type
// =====================================================

/// Draw a point
/// Parameters:
/// - obj: Point geometry object
/// - theme: Theme dictionary
/// - aspect: Optional (x-range, y-range, width, height) for aspect ratio correction
#let draw-point(obj, theme, aspect: none) = {
  import cetz.draw: *
  let style = get-point-style(obj, theme)
  let coords = if obj.at("z", default: none) != none { (obj.x, obj.y, obj.z) } else { (obj.x, obj.y) }

  // 3D Point: Use line with round cap to ensure spherical look (billboard)
  if obj.at("z", default: none) != none {
    let pt-radius = 5pt
    line(coords, coords, stroke: (cap: "round", thickness: pt-radius, paint: style.fill))
  } else {
    // 2D Point: Calculate aspect-corrected radii to render as true circles on screen
    let (rx, ry) = if aspect != none {
      let (x-range, y-range, width, height) = aspect
      let x-units-per-pt = (x-range.at(1) - x-range.at(0)) / width
      let y-units-per-pt = (y-range.at(1) - y-range.at(0)) / height
      // Convert screen radius to plot units for each axis
      let base-r = style.radius
      (base-r * x-units-per-pt, base-r * y-units-per-pt)
    } else {
      (style.radius, style.radius)
    }

    // Always draw ellipse with compensated radii (appears as circle on screen)
    if rx == ry or aspect == none {
      circle(coords, radius: style.radius, fill: style.fill, stroke: style.stroke)
    } else {
      // Draw ellipse in plot coordinates that appears circular on screen
      let steps = 32
      let pts = ()
      for i in range(steps) {
        let a = i / steps * 360deg
        pts.push((coords.at(0) + rx * calc.cos(a), coords.at(1) + ry * calc.sin(a)))
      }
      line(..pts, close: true, fill: style.fill, stroke: style.stroke)
    }
  }

  if obj.label != none {
    let bg-col = theme.at("page-fill", default: white)
    let stroke-col = theme.at("plot", default: (:)).at("stroke", default: black)

    // Smart anchor selection - prefer south, but use label-anchor if specified
    let anchor = obj.at("label-anchor", default: "south")

    content(
      coords,
      text(fill: stroke-col, format-label(obj, obj.label)),
      anchor: anchor,
      padding: 0.2,
      fill: bg-col,
      stroke: none,
    )
  }
}

/// Draw a segment
#let draw-segment(obj, theme) = {
  import cetz.draw: *
  let style = get-line-style(obj, theme)

  let p1 = if obj.p1.at("z", default: none) != none { (obj.p1.x, obj.p1.y, obj.p1.z) } else { (obj.p1.x, obj.p1.y) }
  let p2 = if obj.p2.at("z", default: none) != none { (obj.p2.x, obj.p2.y, obj.p2.z) } else { (obj.p2.x, obj.p2.y) }

  line(p1, p2, stroke: style.stroke)

  if obj.at("label", default: none) != none {
    let bg-col = theme.at("page-fill", default: white)

    // For 2D segments, use smart positioning with angle-aware anchors
    if p1.len() == 2 {
      let dx = p2.at(0) - p1.at(0)
      let dy = p2.at(1) - p1.at(1)
      let len = calc.sqrt(dx * dx + dy * dy)
      let mid = ((p1.at(0) + p2.at(0)) / 2, (p1.at(1) + p2.at(1)) / 2)

      if len > 0 {
        // Perpendicular unit vector (90 deg CCW)
        let nx = -dy / len
        let ny = dx / len
        let offset = 0.25
        let label-pos = (mid.at(0) + nx * offset, mid.at(1) + ny * offset)

        // Choose anchor based on perpendicular direction
        let anchor = if ny >= 0 { "south" } else { "north" }

        content(
          label-pos,
          text(fill: theme.plot.stroke, format-label(obj, obj.label)),
          anchor: anchor,
          padding: 0.1,
          fill: bg-col,
          stroke: none,
        )
      } else {
        content(
          mid,
          text(fill: theme.plot.stroke, format-label(obj, obj.label)),
          anchor: "south",
          padding: 0.1,
          fill: bg-col,
          stroke: none,
        )
      }
    } else {
      // 3D: simple midpoint label
      let mid = ((p1.at(0) + p2.at(0)) / 2, (p1.at(1) + p2.at(1)) / 2, (p1.at(2) + p2.at(2)) / 2)
      content(
        mid,
        text(fill: theme.plot.stroke, format-label(obj, obj.label)),
        anchor: "center",
        padding: 0.1,
        fill: bg-col,
        stroke: none,
      )
    }
  }
}

/// Draw an infinite line
#let draw-line-infinite(obj, theme, bounds) = {
  import cetz.draw: *
  let style = get-line-style(obj, theme)

  // 3D handling: If Z is present, just draw a long line (clipping in 3D is complex)
  let is-3d = obj.p1.at("z", default: none) != none

  let dx = obj.p2.x - obj.p1.x
  let dy = obj.p2.y - obj.p1.y
  let dz = if is-3d { obj.p2.z - obj.p1.z } else { 0 }

  let len = calc.sqrt(dx * dx + dy * dy + dz * dz)
  if len == 0 { return }

  let start = if is-3d { (obj.p1.x, obj.p1.y, obj.p1.z) } else { (obj.p1.x, obj.p1.y) }

  // Extend
  let extend = 20 // Fixed extension for 3D/Simple
  if not is-3d {
    let (x-min, x-max) = bounds.at("x", default: (-10, 10))
    let (y-min, y-max) = bounds.at("y", default: (-10, 10))
    extend = calc.max(x-max - x-min, y-max - y-min) * 2
  }

  let p1 = if is-3d {
    (start.at(0) - dx / len * extend, start.at(1) - dy / len * extend, start.at(2) - dz / len * extend)
  } else {
    (start.at(0) - dx / len * extend, start.at(1) - dy / len * extend)
  }
  let p2 = if is-3d {
    (start.at(0) + dx / len * extend, start.at(1) + dy / len * extend, start.at(2) + dz / len * extend)
  } else {
    (start.at(0) + dx / len * extend, start.at(1) + dy / len * extend)
  }

  line(p1, p2, stroke: style.stroke)
}

/// Draw a ray
#let draw-ray(obj, theme, bounds) = {
  import cetz.draw: *
  let style = get-line-style(obj, theme)

  let is-3d = obj.origin.at("z", default: none) != none

  let dx = obj.through.x - obj.origin.x
  let dy = obj.through.y - obj.origin.y
  let dz = if is-3d { obj.through.z - obj.origin.z } else { 0 }

  let len = calc.sqrt(dx * dx + dy * dy + dz * dz)
  if len == 0 { return }

  let start = if is-3d { (obj.origin.x, obj.origin.y, obj.origin.z) } else { (obj.origin.x, obj.origin.y) }

  // Extend
  let extend = 20
  if not is-3d {
    let (x-min, x-max) = bounds.at("x", default: (-10, 10))
    let (y-min, y-max) = bounds.at("y", default: (-10, 10))
    extend = calc.max(x-max - x-min, y-max - y-min) * 2
  }

  let p2 = if is-3d {
    (start.at(0) + dx / len * extend, start.at(1) + dy / len * extend, start.at(2) + dz / len * extend)
  } else {
    (start.at(0) + dx / len * extend, start.at(1) + dy / len * extend)
  }

  line(start, p2, stroke: style.stroke)
}

/// Draw a circle
#let draw-circle-obj(obj, theme) = {
  import cetz.draw: *
  let style = get-line-style(obj, theme)
  let fill = get-fill-style(obj, theme)

  // 3D check: CeTZ circle in 3D is a bit different.
  // We'll use discretized line for robust 3D support of circle/arc
  // But if Z is missing, use standard circle
  if obj.center.at("z", default: none) == none {
    circle(
      (obj.center.x, obj.center.y),
      radius: obj.radius,
      stroke: style.stroke,
      fill: fill,
    )
  } else {
    // 3D Circle (assumed on XY plane at Z)
    // Discretize
    let pts = ()
    let steps = 64
    for i in range(steps) {
      let a = i / steps * 360deg
      pts.push((
        obj.center.x + obj.radius * calc.cos(a),
        obj.center.y + obj.radius * calc.sin(a),
        obj.center.z,
      ))
    }
    line(..pts, close: true, stroke: style.stroke, fill: fill)
  }

  if obj.at("label", default: none) != none {
    let bg-col = theme.at("page-fill", default: white)

    // Configurable label angle (default 45°, can override with label-angle)
    let ang = obj.at("label-angle", default: 45deg)

    // Calculate label position at edge of circle
    let label-coords = if obj.center.at("z", default: none) != none {
      (obj.center.x + obj.radius * calc.cos(ang), obj.center.y + obj.radius * calc.sin(ang), obj.center.z)
    } else {
      (obj.center.x + obj.radius * calc.cos(ang), obj.center.y + obj.radius * calc.sin(ang))
    }

    // Smart anchor based on angle quadrant
    // Q1 (0-90): south-west, Q2 (90-180): south-east, Q3 (180-270): north-east, Q4 (270-360): north-west
    let ang-deg = if ang < 0deg { ang + 360deg } else { ang }
    let anchor = if ang-deg >= 0deg and ang-deg < 90deg { "south-west" } else if ang-deg >= 90deg and ang-deg < 180deg {
      "south-east"
    } else if ang-deg >= 180deg and ang-deg < 270deg { "north-east" } else { "north-west" }

    content(
      label-coords,
      text(fill: theme.plot.stroke, format-label(obj, obj.label)),
      anchor: anchor,
      padding: 0.1,
      fill: bg-col,
      stroke: none,
    )
  }
}

/// Draw an arc
#let draw-arc(obj, theme) = {
  import cetz.draw: *
  let style = get-line-style(obj, theme)

  if obj.center.at("z", default: none) == none {
    arc(
      (obj.center.x, obj.center.y),
      start: obj.start,
      stop: obj.end,
      radius: obj.radius,
      stroke: style.stroke,
      mode: "OPEN",
    )
  } else {
    // 3D Arc
    let pts = ()
    let steps = 32
    // Handle wrap around? Arc usually start->stop ccw.
    // Need diff logic again if going through 0 etc.
    // But obj.start/end are usually well defined.
    // Let's assume start/end are raw angles.
    let s = obj.start
    let e = obj.end
    // Simple linear interp
    for i in range(steps + 1) {
      let t = i / steps
      let a = s + (e - s) * t
      pts.push((
        obj.center.x + obj.radius * calc.cos(a),
        obj.center.y + obj.radius * calc.sin(a),
        obj.center.z,
      ))
    }
    line(..pts, stroke: style.stroke)
  }
}

/// Draw an angle marker (Always 2D for now, 3D angle markers are hard)
#let draw-angle-marker(obj, theme) = {
  import cetz.draw: *

  let stroke-col = theme.at("plot", default: (:)).at("stroke", default: black)
  let fill-col = if obj.fill == auto {
    stroke-col.transparentize(70%)
  } else if obj.fill != none {
    obj.fill
  } else {
    none
  }

  let dx1 = obj.p1.x - obj.vertex.x
  let dy1 = obj.p1.y - obj.vertex.y
  let dx2 = obj.p2.x - obj.vertex.x
  let dy2 = obj.p2.y - obj.vertex.y

  let start-deg = calc.atan2(dx1, dy1).deg()
  let end-deg = calc.atan2(dx2, dy2).deg()

  if start-deg < 0 { start-deg += 360 }
  if end-deg < 0 { end-deg += 360 }

  // Strict CCW difference
  let diff = calc.rem(end-deg - start-deg + 360, 360)

  // Handle reflex override
  let is-reflex = obj.at("reflex", default: "auto")
  if is-reflex == "auto" {
    if diff > 180 {
      diff = 360 - diff
      start-deg = end-deg
    }
  } else if is-reflex {
    diff = 360 - diff
    start-deg = end-deg
  }

  let start-ang = start-deg * 1deg
  let stop-ang = (start-deg + diff) * 1deg
  let angle-diff = diff * 1deg

  // Discretized pie slice to avoid CeTZ bugs
  let pts = ()
  pts.push((obj.vertex.x, obj.vertex.y)) // Start at vertex

  let steps = 30
  for i in range(steps + 1) {
    let a = start-deg + i / steps * diff
    let rad = a * 1deg
    pts.push((
      obj.vertex.x + obj.radius * calc.cos(rad),
      obj.vertex.y + obj.radius * calc.sin(rad),
    ))
  }

  line(..pts, close: true, fill: fill-col, stroke: (paint: stroke-col))

  if obj.at("label", default: none) != none {
    let mid-ang = start-ang + angle-diff / 2
    let label-r = if obj.at("label-radius", default: auto) != auto {
      obj.at("label-radius")
    } else {
      obj.radius * 1.5
    }
    let bg-col = theme.at("page-fill", default: white)
    content(
      (obj.vertex.x + label-r * calc.cos(mid-ang), obj.vertex.y + label-r * calc.sin(mid-ang)),
      text(fill: stroke-col, format-label(obj, obj.label)),
      anchor: "center",
      fill: bg-col,
      stroke: none,
    )
  }
}


/// Draw a right angle marker
#let draw-right-angle-marker(obj, theme) = {
  import cetz.draw: *
  let stroke-col = theme.at("plot", default: (:)).at("stroke", default: black)

  let dx1 = obj.p1.x - obj.vertex.x
  let dy1 = obj.p1.y - obj.vertex.y
  let len1 = calc.sqrt(dx1 * dx1 + dy1 * dy1)

  let dx2 = obj.p2.x - obj.vertex.x
  let dy2 = obj.p2.y - obj.vertex.y
  let len2 = calc.sqrt(dx2 * dx2 + dy2 * dy2)

  if len1 == 0 or len2 == 0 { return }

  let r = obj.radius
  let corner1 = (obj.vertex.x + r * dx1 / len1, obj.vertex.y + r * dy1 / len1)
  let corner2 = (obj.vertex.x + r * dx2 / len2, obj.vertex.y + r * dy2 / len2)
  let mid = (corner1.at(0) + r * dx2 / len2, corner1.at(1) + r * dy2 / len2)

  line(corner1, mid, corner2, stroke: (paint: stroke-col))
}

/// Draw a polygon
#let draw-polygon-obj(obj, theme) = {
  import cetz.draw: *
  let style = get-line-style(obj, theme)
  let fill = get-fill-style(obj, theme)

  // Apply theme color if fill is auto
  let final-fill = if fill == auto {
    theme.at("plot", default: (:)).at("highlight", default: black).transparentize(70%)
  } else {
    fill
  }

  // Support 3D points
  let coords = obj.points.map(p => {
    if p.at("z", default: none) != none { (p.x, p.y, p.z) } else { (p.x, p.y) }
  })

  line(..coords, close: true, stroke: style.stroke, fill: final-fill)

  if obj.at("label", default: none) != none {
    let bg-col = theme.at("page-fill", default: white)

    // Calculate centroid for primary position, or use label-position override
    let pos-type = obj.at("label-position", default: "centroid")

    let label-pos = if pos-type == "top-right" {
      // Original top-right corner positioning
      let max-x = calc.max(..obj.points.map(p => p.x))
      let max-y = calc.max(..obj.points.map(p => p.y))
      if obj.points.first().at("z", default: none) != none {
        let max-z = calc.max(..obj.points.map(p => p.at("z", default: 0)))
        (max-x, max-y, max-z)
      } else {
        (max-x, max-y)
      }
    } else {
      // Centroid positioning (default)
      let sum-x = obj.points.map(p => p.x).sum()
      let sum-y = obj.points.map(p => p.y).sum()
      let n = obj.points.len()
      if obj.points.first().at("z", default: none) != none {
        let sum-z = obj.points.map(p => p.at("z", default: 0)).sum()
        (sum-x / n, sum-y / n, sum-z / n)
      } else {
        (sum-x / n, sum-y / n)
      }
    }

    // Use appropriate anchor based on position type
    let anchor = if pos-type == "top-right" { "south-west" } else { "center" }

    content(
      label-pos,
      text(fill: theme.plot.stroke, format-label(obj, obj.label)),
      anchor: anchor,
      padding: 0.15,
      fill: bg-col,
      stroke: none,
    )
  }
}

/// Draw a vector (arrow)
#let draw-vector-obj(obj, theme, origin: (0, 0)) = {
  import cetz.draw: *

  let stroke-col = if obj.style != auto and obj.style != none and "stroke" in obj.style {
    obj.style.stroke
  } else {
    theme.at("plot", default: (:)).at("stroke", default: black)
  }

  // Use bound origin if present
  let eff-origin = obj.at("origin", default: origin)

  // Handle 3D origin and vector components
  let start = if type(eff-origin) == dictionary {
    if eff-origin.at("z", default: none) != none { (eff-origin.x, eff-origin.y, eff-origin.z) } else {
      (eff-origin.x, eff-origin.y)
    }
  } else { eff-origin }

  // start can be (x,y) or (x,y,z)
  // Ensure vector also has Z if start has Z, or vice versa
  let vz = obj.at("z", default: 0)

  let end = if start.len() == 3 {
    (start.at(0) + obj.x, start.at(1) + obj.y, start.at(2) + vz)
  } else {
    (start.at(0) + obj.x, start.at(1) + obj.y)
  }

  let final-stroke = if type(stroke-col) == dictionary {
    stroke-col + (thickness: 1.5pt) // Default thickness, but allow override if in stroke-col? Typst + operator overwrites left with right? No, left has priority? Typst (a:1) + (a:2) -> (a:2). So put defaults first.
    (thickness: 1.5pt) + stroke-col
  } else {
    (paint: stroke-col, thickness: 1.5pt)
  }

  // Extract paint for fill if possible
  let fill-paint = if type(stroke-col) == dictionary {
    stroke-col.at("paint", default: stroke-col.at("stroke", default: black)) // Try to find a color
  } else {
    stroke-col
  }

  line(
    start,
    end,
    stroke: final-stroke,
    mark: (end: "stealth", fill: fill-paint),
  )

  if obj.at("label", default: none) != none {
    let bg-col = theme.at("page-fill", default: white)

    // For 2D vectors, use smart label positioning with fallbacks
    if start.len() == 2 {
      let dx = end.at(0) - start.at(0)
      let dy = end.at(1) - start.at(1)
      let len = calc.sqrt(dx * dx + dy * dy)

      if len > 0 {
        // Normalized direction vector
        let ux = dx / len
        let uy = dy / len
        // Perpendicular unit vector (90 deg CCW)
        let nx = -uy
        let ny = ux

        // Midpoint
        let mid = ((start.at(0) + end.at(0)) / 2, (start.at(1) + end.at(1)) / 2)

        // Smart position selection based on vector angle
        // For near-horizontal vectors: prefer above/below (use perp offset)
        // For near-vertical vectors: prefer left/right
        let offset = 0.3

        // Determine best position based on vector direction
        // Use angle to pick the most natural label placement
        let angle = calc.atan2(dy, dx)

        // Position 1: Perpendicular CCW (primary)
        let pos-ccw = (mid.at(0) + nx * offset, mid.at(1) + ny * offset)
        // Position 2: Perpendicular CW (opposite side)
        let pos-cw = (mid.at(0) - nx * offset, mid.at(1) - ny * offset)
        // Position 3: Near tip (offset from end)
        let pos-tip = (end.at(0) - ux * 0.3 + nx * 0.15, end.at(1) - uy * 0.3 + ny * 0.15)
        // Position 4: Near tail (offset from start)
        let pos-tail = (start.at(0) + ux * 0.3 + nx * 0.15, start.at(1) + uy * 0.3 + ny * 0.15)

        // Choose anchor based on primary position relative to vector
        // If label is above vector (ny > 0), anchor south; if below, anchor north
        let anchor = if ny >= 0 { "south" } else { "north" }

        // Use primary position (could add overlap detection here in future)
        content(
          pos-ccw,
          text(fill: stroke-col, format-label(obj, obj.label)),
          anchor: anchor,
          padding: 0.1,
          fill: bg-col,
          stroke: none,
        )
      } else {
        // Zero-length vector, place at midpoint
        let mid = ((start.at(0) + end.at(0)) / 2, (start.at(1) + end.at(1)) / 2)
        content(
          mid,
          text(fill: stroke-col, format-label(obj, obj.label)),
          anchor: "south",
          padding: 0.1,
          fill: bg-col,
          stroke: none,
        )
      }
    } else {
      // 3D: Use simple perpendicular offset in XY plane
      let mid = ((start.at(0) + end.at(0)) / 2, (start.at(1) + end.at(1)) / 2, (start.at(2) + end.at(2)) / 2)
      let dx = end.at(0) - start.at(0)
      let dy = end.at(1) - start.at(1)
      let len = calc.sqrt(dx * dx + dy * dy)
      let label-pos = if len > 0 {
        let nx = -dy / len
        let ny = dx / len
        (mid.at(0) + nx * 0.25, mid.at(1) + ny * 0.25, mid.at(2))
      } else {
        (mid.at(0), mid.at(1), mid.at(2) + 0.25)
      }
      content(
        label-pos,
        text(fill: stroke-col, format-label(obj, obj.label)),
        anchor: "center",
        padding: 0.1,
        fill: bg-col,
        stroke: none,
      )
    }
  }
}


/// Draw vec-add helplines only (parallelogram sides)
/// Vectors are drawn separately by canvas with global smart labeling.
#let draw-vec-add-helplines(obj, theme, origin: (0, 0)) = {
  import cetz.draw: *

  let v1 = obj.v1
  let v2 = obj.v2

  let start = origin
  let sx = if type(start) == dictionary { start.x } else { start.at(0) }
  let sy = if type(start) == dictionary { start.y } else { start.at(1) }

  let v1-end = (sx + v1.x, sy + v1.y)
  let v2-end = (sx + v2.x, sy + v2.y)
  let sum-end = (sx + v1.x + v2.x, sy + v1.y + v2.y)

  line(v1-end, sum-end, stroke: (paint: gray, thickness: 1.5pt, dash: "dotted"))
  line(v2-end, sum-end, stroke: (paint: gray, thickness: 1.5pt, dash: "dotted"))
}

/// Draw vec-project helplines only (extended axis, perpendicular, right angle)
/// Vectors are drawn separately by canvas with global smart labeling.
#let draw-vec-proj-helplines(obj, theme, origin: (0, 0)) = {
  import cetz.draw: *

  let v1 = obj.v1
  let v2 = obj.v2
  let proj = obj.proj

  let start = origin
  let sx = if type(start) == dictionary { start.x } else { start.at(0) }
  let sy = if type(start) == dictionary { start.y } else { start.at(1) }

  let a-end = (sx + v1.x, sy + v1.y)
  let proj-end = (sx + proj.x, sy + proj.y)

  // Extended axis line
  let b-scale = 1.3
  line(
    (sx - v2.x * 0.2, sy - v2.y * 0.2),
    (sx + v2.x * b-scale, sy + v2.y * b-scale),
    stroke: (paint: gray, thickness: 1.5pt, dash: "dotted"),
  )

  // Perpendicular line
  line(a-end, proj-end, stroke: (paint: gray, thickness: 1.5pt, dash: "dotted"))

  // Right angle marker
  let p-a = (x: a-end.at(0), y: a-end.at(1))
  let p-proj = (x: proj-end.at(0), y: proj-end.at(1))
  let p-start = (x: sx, y: sy)
  draw-right-angle-marker((type: "right-angle", p1: p-a, vertex: p-proj, p2: p-start, radius: 0.3), theme)
}

/// Draw a function using CeTZ plot
/// For robust/adaptive functions, uses adaptive sampling algorithm
#let draw-func-obj(obj, theme, x-domain: auto, y-domain: auto, size: (10, 10)) = {
  let stroke-col = if obj.style != auto and obj.style != none and "stroke" in obj.style {
    obj.style.stroke
  } else {
    theme.at("plot", default: (:)).at("highlight", default: black)
  }

  let style = (stroke: stroke-col)

  // Use adaptive sampling for robust functions with "standard" type
  if obj.robust and obj.func-type == "standard" {
    // Get domain from object or fallback to passed domain
    let dom = obj.domain
    let x-min = dom.at(0)
    let x-max = dom.at(1)

    // Get y-domain for clipping (use passed or default)
    let y-min = if y-domain == auto { -10 } else { y-domain.at(0) }
    let y-max = if y-domain == auto { 10 } else { y-domain.at(1) }

    // Call adaptive sampler
    let points = adaptive-sample(
      obj.f,
      x-min,
      x-max,
      samples: obj.samples,
      tolerance: 0.1,
    )

    // Split at none markers and render segments
    let segment = ()
    for pt in points {
      if pt == none {
        // Break marker - render current segment if non-empty
        if segment.len() >= 2 {
          plot.add(segment, style: style)
        }
        segment = ()
      } else {
        segment.push(pt)
      }
    }
    // Render final segment
    if segment.len() >= 2 {
      plot.add(segment, style: style)
    }
  } else if obj.func-type == "parametric" {
    // Parametric curve
    plot.add(domain: obj.domain, samples: obj.samples, style: style, obj.f)
  } else {
    // Standard function (non-adaptive)
    plot.add(domain: obj.domain, samples: obj.samples, style: style, obj.f)
  }

  // Draw empty holes (open circles) using plot markers for proper aspect ratio
  if obj.at("hole", default: ()).len() > 0 {
    let page-fill = theme.at("page-fill", default: white)
    let hole-pts = ()
    for h in obj.hole {
      // Evaluate f(h) approx (limit) since f(h) is likely undefined or 0/0
      let y = (obj.f)(h + 0.0001)
      hole-pts.push((h, y))
    }
    // Use plot.add with circle marker for proper circular rendering
    plot.add(
      hole-pts,
      style: (stroke: none),
      mark: "o",
      mark-style: (fill: page-fill, stroke: style.stroke),
      mark-size: 0.16,
    )
  }

  // Draw filled holes using plot markers for proper aspect ratio
  if obj.at("filled-hole", default: ()).len() > 0 {
    let hole-pts = ()
    for h in obj.at("filled-hole") {
      let y = (obj.f)(h + 0.0001)
      hole-pts.push((h, y))
    }
    // Use plot.add with filled circle marker
    plot.add(
      hole-pts,
      style: (stroke: none),
      mark: "o",
      mark-style: (fill: stroke-col, stroke: style.stroke),
      mark-size: 0.16,
    )
  }

  if obj.at("label", default: none) != none {
    // Find the last visible point on the curve
    // Use visible x-domain end (clamped)
    let vis-x-end = if obj.func-type == "standard" and x-domain != auto {
      calc.min(obj.domain.at(1), x-domain.at(1))
    } else {
      obj.domain.at(1)
    }

    // Sample at the visible x-end
    let raw-y = if obj.func-type == "standard" {
      (obj.f)(vis-x-end)
    } else {
      (obj.f)(vis-x-end).at(1)
    }

    // Clamp y to the visible y-domain to get the actual last plotted point
    let label-y = raw-y
    if y-domain != auto {
      label-y = calc.clamp(raw-y, y-domain.at(0), y-domain.at(1))
    }

    // Add an invisible point with label - the stroke style creates the colored line in the legend
    plot.add(
      ((vis-x-end, label-y),),
      style: (stroke: stroke-col),
      mark: none,
      label: format-label(obj, obj.label),
    )
  }
}

/// Clip a line segment (p1, p2) to the rectangle defined by bounds (x-min, x-max, y-min, y-max)
/// Returns array of segments (usually 0 or 1 segment: ((x1, y1), (x2, y2)))
#let clip-segment(p1, p2, bounds) = {
  let (x-min, x-max) = bounds.x
  let (y-min, y-max) = bounds.y

  let x1 = p1.at(0)
  let y1 = p1.at(1)
  let x2 = p2.at(0)
  let y2 = p2.at(1)

  // Cohen-Sutherland Line Clipping
  let INSIDE = 0
  let LEFT = 1
  let RIGHT = 2
  let BOTTOM = 4
  let TOP = 8

  let compute-out-code = (x, y) => {
    let code = INSIDE
    if x < x-min { code = code + LEFT } else if x > x-max { code = code + RIGHT }
    if y < y-min { code = code + BOTTOM } else if y > y-max { code = code + TOP }
    code
  }

  let code1 = compute-out-code(x1, y1)
  let code2 = compute-out-code(x2, y2)
  let accept = false

  let max-iter = 10 // Safety break
  let iter = 0

  while iter < max-iter {
    if (code1.bit-and(code2) != 0) {
      // Both points outside same region -> reject
      return ()
    } else if (code1.bit-or(code2) == 0) {
      // Both points inside -> accept
      accept = true
      break
    } else {
      // At least one point outside
      let code-out = if code1 != 0 { code1 } else { code2 }
      let x = 0.0
      let y = 0.0

      // Find intersection point
      if (code-out.bit-and(TOP) != 0) {
        x = x1 + (x2 - x1) * (y-max - y1) / (y2 - y1)
        y = y-max
      } else if (code-out.bit-and(BOTTOM) != 0) {
        x = x1 + (x2 - x1) * (y-min - y1) / (y2 - y1)
        y = y-min
      } else if (code-out.bit-and(RIGHT) != 0) {
        y = y1 + (y2 - y1) * (x-max - x1) / (x2 - x1)
        x = x-max
      } else if (code-out.bit-and(LEFT) != 0) {
        y = y1 + (y2 - y1) * (x-min - x1) / (x2 - x1)
        x = x-min
      }

      if code-out == code1 {
        x1 = x
        y1 = y
        code1 = compute-out-code(x1, y1)
      } else {
        x2 = x
        y2 = y
        code2 = compute-out-code(x2, y2)
      }
    }
    iter += 1
  }

  if accept {
    (((x1, y1), (x2, y2)),)
  } else {
    ()
  }
}

/// Draw a data series (scatter plot, line plot, or both)
#let draw-data-series-obj(obj, theme, x-domain: auto, y-domain: auto) = {
  let stroke-col = if obj.style != auto and obj.style != none and "stroke" in obj.style {
    obj.style.stroke
  } else {
    theme.at("plot", default: (:)).at("highlight", default: black)
  }

  let fill-col = if obj.style != auto and obj.style != none and "fill" in obj.style {
    obj.style.fill
  } else {
    stroke-col
  }

  let marker-size = if obj.style != auto and obj.style != none and "size" in obj.style {
    obj.style.size
  } else {
    0.08
  }

  let plot-type = obj.at("plot-type", default: "scatter")
  let data = obj.data

  let bounds = if x-domain != auto and y-domain != auto {
    (x: x-domain, y: y-domain)
  } else {
    none
  }

  // Draw line if plot-type is "line" or "both"
  if plot-type == "line" or plot-type == "both" {
    if data.len() >= 2 {
      if bounds == none {
        // Standard drawing (no manual clipping)
        plot.add(data, style: (stroke: stroke-col), mark: none)
      } else {
        // Manual clipping + Multiple Segments
        let segments = ()
        let current-segment = ()

        for i in range(data.len() - 1) {
          let p1 = data.at(i)
          let p2 = data.at(i + 1)

          let result = clip-segment(p1, p2, bounds)
          if result.len() > 0 {
            // We have a visible segment
            let seg = result.first()

            // If current segment is empty, start it
            if current-segment.len() == 0 {
              current-segment.push(seg.at(0))
              current-segment.push(seg.at(1))
            } else {
              // Check continuity with previous point
              let last-pt = current-segment.last()
              let new-start = seg.at(0)

              // Basic float equality check
              let dist_sq = calc.pow(last-pt.at(0) - new-start.at(0), 2) + calc.pow(last-pt.at(1) - new-start.at(1), 2)

              if dist_sq < 0.000001 {
                // Continuous, append end point
                current-segment.push(seg.at(1))
              } else {
                // Gap detected (clipped part), flush current and start new
                plot.add(current-segment, style: (stroke: stroke-col), mark: none)
                current-segment = (seg.at(0), seg.at(1))
              }
            }
          }
        }

        // Flush final segment
        if current-segment.len() >= 2 {
          plot.add(current-segment, style: (stroke: stroke-col), mark: none)
        }
      }
    }
  }

  // Draw points if plot-type is "scatter" or "both"
  if plot-type == "scatter" or plot-type == "both" {
    let pts-to-draw = if bounds != none {
      data.filter(pt => {
        let (x, y) = pt
        x >= bounds.x.at(0) and x <= bounds.x.at(1) and y >= bounds.y.at(0) and y <= bounds.y.at(1)
      })
    } else {
      data
    }

    if pts-to-draw.len() > 0 {
      plot.add(
        pts-to-draw,
        style: (stroke: none),
        mark: "o",
        mark-style: (fill: fill-col, stroke: none),
        mark-size: marker-size * 2,
      )
    }
  }

  // Draw label in legend if present
  if obj.at("label", default: none) != none and data.len() > 0 {
    // Add an invisible point with label - creates legend entry
    let last-pt = data.last()
    plot.add(
      (last-pt,),
      style: (stroke: stroke-col),
      mark: "o",
      mark-style: (fill: fill-col, stroke: none),
      mark-size: 0.001, // Invisible but triggers legend
      label: obj.label,
    )
  }
}

// =====================================================
// Curve Drawing (Splines)
// =====================================================

/// Draw a curve object
#let draw-curve-obj(obj, theme) = {
  import cetz.draw: *
  let style = get-line-style(obj, theme)
  let pts = obj.points

  if pts.len() < 2 { return }

  let coords = pts.map(p => if type(p) == dictionary { (p.x, p.y) } else { (p.at(0), p.at(1)) })

  if obj.interpolation == "linear" {
    line(..coords, stroke: style.stroke)
  } else if obj.interpolation == "spline" {
    // Spline segments are pre-calculated in the object constructor (func.typ)
    let segments = obj.at("segments", default: ())

    for seg in segments {
      // seg is (start, c1, c2, end)

      // Safely handle stroke for bezier
      let s = style.stroke
      bezier(seg.at(0), seg.at(3), seg.at(1), seg.at(2), stroke: s)
    }
  }


  if obj.at("label", default: none) != none {
    // Label at last point for now
    let last = coords.last()

    // Extract paint safely
    let text-fill = if type(style.stroke) == dictionary {
      style.stroke.at("paint", default: black)
    } else {
      style.stroke
    }

    let seg-len = obj.at("segments", default: ()).len()
    let debug-label = format-label(obj, obj.label) + " [" + str(seg-len) + "]"

    content(
      (last.at(0) + 0.2, last.at(1)),
      text(fill: text-fill, debug-label),
      anchor: "west",
    )
  }
}


// =====================================================
// Universal Draw Dispatcher
// =====================================================

/// Draw any geometry object
///
/// Parameters:
/// - obj: The geometry object to draw
/// - theme: The active theme
/// - bounds: Canvas bounds for infinite objects (optional)
/// - origin: Origin for vectors (optional)
/// - aspect: Aspect ratio info (x-range, y-range, width, height) for point circle correction
#let draw-geo(obj, theme, bounds: (x: (-10, 10), y: (-10, 10)), origin: (0, 0), aspect: none) = {
  let t = obj.at("type", default: none)

  if t == "point" { draw-point(obj, theme, aspect: aspect) } else if t == "segment" {
    draw-segment(obj, theme)
  } else if t == "line" {
    draw-line-infinite(obj, theme, bounds)
  } else if t == "ray" { draw-ray(obj, theme, bounds) } else if t == "circle" { draw-circle-obj(obj, theme) } else if (
    t == "arc"
  ) { draw-arc(obj, theme) } else if t == "angle" { draw-angle-marker(obj, theme) } else if t == "right-angle" {
    draw-right-angle-marker(obj, theme)
  } else if t == "polygon" { draw-polygon-obj(obj, theme) } else if t == "vector" {
    draw-vector-obj(obj, theme, origin: origin)
  } else if t == "vec-add-helplines" {
    draw-vec-add-helplines(obj, theme, origin: origin)
  } else if t == "vec-proj-helplines" {
    draw-vec-proj-helplines(obj, theme, origin: origin)
  } else if t == "curve" {
    draw-curve-obj(obj, theme)
  }
  // Note: func and data-series objects are handled separately in plot context
}

/// Draw function for use in plot context (handles func and data-series)
#let draw-plot-obj(obj, theme, x-domain: auto, y-domain: auto) = {
  let t = obj.at("type", default: none)
  if t == "func" {
    draw-func-obj(obj, theme)
  } else if t == "data-series" {
    draw-data-series-obj(obj, theme, x-domain: x-domain, y-domain: y-domain)
  }
}
