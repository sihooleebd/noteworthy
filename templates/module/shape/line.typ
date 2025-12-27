// =====================================================
// LINE, SEGMENT, RAY - Linear geometry objects
// =====================================================

#import "point.typ": is-point, point

/// Create a line segment between two points
/// A segment has definite endpoints and finite length.
///
/// Parameters:
/// - p1: First endpoint (point object or (x, y) tuple)
/// - p2: Second endpoint
/// - label: Optional label
/// - style: Optional style overrides
#let segment(p1, p2, label: none, style: auto) = {
  // Convert tuples to points if needed
  let pt1 = if is-point(p1) { p1 } else { point(p1.at(0), p1.at(1)) }
  let pt2 = if is-point(p2) { p2 } else { point(p2.at(0), p2.at(1)) }

  (
    type: "segment",
    p1: pt1,
    p2: pt2,
    label: label,
    style: style,
  )
}

/// Create an infinite line through two points
/// A line extends infinitely in both directions.
///
/// Parameters:
/// - p1: First point on the line
/// - p2: Second point on the line
/// - style: Optional style overrides
#let line(p1, p2, label: none, style: auto) = {
  let pt1 = if is-point(p1) { p1 } else { point(p1.at(0), p1.at(1)) }
  let pt2 = if is-point(p2) { p2 } else { point(p2.at(0), p2.at(1)) }

  (
    type: "line",
    p1: pt1,
    p2: pt2,
    label: label,
    style: style,
  )
}

/// Create a ray starting at origin, passing through a point
/// A ray extends infinitely in one direction from its origin.
///
/// Parameters:
/// - origin: Starting point of the ray
/// - through: A point the ray passes through
/// - style: Optional style overrides
#let ray(origin, through, label: none, style: auto) = {
  let pt1 = if is-point(origin) { origin } else { point(origin.at(0), origin.at(1)) }
  let pt2 = if is-point(through) { through } else { point(through.at(0), through.at(1)) }

  (
    type: "ray",
    origin: pt1,
    through: pt2,
    label: label,
    style: style,
  )
}

/// Create a line from point and angle
///
/// Parameters:
/// - p: Point on the line
/// - angle: Direction angle
/// - style: Optional style overrides
#let line-through-angle(p, angle, style: auto) = {
  let pt = if is-point(p) { p } else { point(p.at(0), p.at(1)) }
  let p2 = point(pt.x + calc.cos(angle), pt.y + calc.sin(angle))
  line(pt, p2, style: style)
}

/// Check if object is a segment
#let is-segment(obj) = {
  type(obj) == dictionary and obj.at("type", default: none) == "segment"
}

/// Check if object is a line
#let is-line(obj) = {
  type(obj) == dictionary and obj.at("type", default: none) == "line"
}

/// Check if object is a ray
#let is-ray(obj) = {
  type(obj) == dictionary and obj.at("type", default: none) == "ray"
}

/// Check if object is any linear type
#let is-linear(obj) = is-segment(obj) or is-line(obj) or is-ray(obj)

/// Get the direction vector of a linear object
#let linear-direction(obj) = {
  let p1 = if obj.type == "ray" { obj.origin } else { obj.p1 }
  let p2 = if obj.type == "ray" { obj.through } else { obj.p2 }
  (p2.x - p1.x, p2.y - p1.y)
}

/// Get the length of a segment
#let segment-length(seg) = {
  let dx = seg.p2.x - seg.p1.x
  let dy = seg.p2.y - seg.p1.y
  calc.sqrt(dx * dx + dy * dy)
}
