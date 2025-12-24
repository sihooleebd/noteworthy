// =====================================================
// CIRCLE, ARC - Circular geometry objects
// =====================================================

#import "point.typ": is-point, point

/// Create a circle
///
/// Parameters:
/// - center: Center point (point object or (x, y) tuple)
/// - radius: Circle radius
/// - label: Optional label
/// - style: Optional style overrides (stroke, fill)
#let circle(center, radius, label: none, fill: none, style: auto) = {
  let pt = if is-point(center) { center } else { point(center.at(0), center.at(1)) }

  (
    type: "circle",
    center: pt,
    radius: radius,
    label: label,
    fill: fill,
    style: style,
  )
}

/// Create a circle through three points
///
/// Parameters:
/// - p1, p2, p3: Three points on the circle
/// - label: Optional label
#let circle-through(p1, p2, p3, label: none, style: auto) = {
  let pt1 = if is-point(p1) { p1 } else { point(p1.at(0), p1.at(1)) }
  let pt2 = if is-point(p2) { p2 } else { point(p2.at(0), p2.at(1)) }
  let pt3 = if is-point(p3) { p3 } else { point(p3.at(0), p3.at(1)) }

  // Calculate circumcenter using perpendicular bisectors
  let ax = pt1.x
  let ay = pt1.y
  let bx = pt2.x
  let by = pt2.y
  let cx = pt3.x
  let cy = pt3.y

  let d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
  if calc.abs(d) < 0.0001 {
    // Points are collinear, return degenerate circle
    return circle((0, 0), 0, label: label)
  }

  let ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
  let uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d

  let r = calc.sqrt((ax - ux) * (ax - ux) + (ay - uy) * (ay - uy))

  circle(point(ux, uy), r, label: label, style: style)
}

/// Create an arc (portion of a circle)
///
/// Parameters:
/// - center: Center point
/// - radius: Arc radius
/// - start-angle: Starting angle (radians or degrees)
/// - end-angle: Ending angle
/// - label: Optional label
/// - style: Optional style overrides
#let arc(center, radius, start-angle, end-angle, label: none, style: auto) = {
  let pt = if is-point(center) { center } else { point(center.at(0), center.at(1)) }

  (
    type: "arc",
    center: pt,
    radius: radius,
    start: start-angle,
    end: end-angle,
    label: label,
    style: style,
  )
}

/// Create a semicircle
#let semicircle(center, radius, start-angle: 0deg, label: none, style: auto) = {
  arc(center, radius, start-angle, start-angle + 180deg, label: label, style: style)
}

/// Check if object is a circle
#let is-circle(obj) = {
  type(obj) == dictionary and obj.at("type", default: none) == "circle"
}

/// Check if object is an arc
#let is-arc(obj) = {
  type(obj) == dictionary and obj.at("type", default: none) == "arc"
}

/// Get a point on the circle at a given angle
#let circle-point-at(circ, angle, label: none) = {
  point(
    circ.center.x + circ.radius * calc.cos(angle),
    circ.center.y + circ.radius * calc.sin(angle),
    label: label,
  )
}

/// Get the circumference of a circle
#let circumference(circ) = 2 * calc.pi * circ.radius

/// Get the area of a circle
#let circle-area(circ) = calc.pi * circ.radius * circ.radius
