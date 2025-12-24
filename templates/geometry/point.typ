// =====================================================
// POINT - Fundamental geometry object
// =====================================================

#import "core.typ": polar-to-cartesian

/// Create a 2D point from Cartesian coordinates
///
/// Parameters:
/// - x: X coordinate
/// - y: Y coordinate
/// - label: Optional label to display
/// - style: Optional style overrides (stroke, fill, size)
#let point(x, y, label: none, style: auto) = (
  type: "point",
  x: x,
  y: y,
  z: none,
  label: label,
  style: style,
)

/// Create a 3D point
///
/// Parameters:
/// - x, y, z: Coordinates
/// - label: Optional label
/// - style: Optional style overrides
#let point-3d(x, y, z, label: none, style: auto) = (
  type: "point",
  x: x,
  y: y,
  z: z,
  label: label,
  style: style,
)

/// Create a point from polar coordinates
///
/// Parameters:
/// - r: Radius (distance from origin)
/// - theta: Angle in radians or degrees
/// - label: Optional label
/// - style: Optional style overrides
#let point-polar(r, theta, label: none, style: auto) = {
  let (x, y) = polar-to-cartesian(r, theta)
  point(x, y, label: label, style: style)
}

/// Check if object is a point
#let is-point(obj) = {
  type(obj) == dictionary and obj.at("type", default: none) == "point"
}

/// Get point coordinates as tuple
#let point-coords(p) = {
  if p.z != none { (p.x, p.y, p.z) } else { (p.x, p.y) }
}

/// Get point as (x, y) tuple (for 2D operations)
#let point-xy(p) = (p.x, p.y)

/// Create a labeled copy of a point
#let with-label(p, label) = {
  let result = p
  result.label = label
  result
}

/// Create a styled copy of a point
#let with-style(p, style) = {
  let result = p
  result.style = style
  result
}
