// =====================================================
// VECTOR - Vector geometry object (extends point with operations)
// =====================================================

#import "point.typ": is-point, point, point-3d

/// Create a 2D vector
/// Vectors are like points but represent direction and magnitude, not position.
///
/// Parameters:
/// - x: X component
/// - y: Y component
/// - label: Optional label (e.g., $vec(v)$)
/// - style: Optional style overrides
#let vector(x, y, label: none, origin: (0, 0), style: auto) = (
  type: "vector",
  x: x,
  y: y,
  z: none,
  label: label,
  origin: origin,
  style: style,
)

/// Create a 3D vector
#let vector-3d(x, y, z, label: none, origin: (0, 0, 0), style: auto) = (
  type: "vector",
  x: x,
  y: y,
  z: z,
  label: label,
  origin: origin,
  style: style,
)

/// Create a vector from a point (position vector)
#let vector-from-point(p, label: none) = {
  if p.z != none {
    vector-3d(p.x, p.y, p.z, label: label, style: p.style)
  } else {
    vector(p.x, p.y, label: label, style: p.style)
  }
}

/// Check if object is a vector
#let is-vector(obj) = {
  type(obj) == dictionary and obj.at("type", default: none) == "vector"
}

// =====================================================
// Vector Operations
// =====================================================

/// Add two vectors - returns array: (result-vector, helplines-object)
/// The helplines object draws the parallelogram, result is a simple vector.
#let vec-add(v1, v2, label: none, helplines: true) = {
  let result = if v1.z != none or v2.z != none {
    let z1 = if v1.z == none { 0 } else { v1.z }
    let z2 = if v2.z == none { 0 } else { v2.z }
    vector-3d(v1.x + v2.x, v1.y + v2.y, z1 + z2, label: label)
  } else {
    vector(v1.x + v2.x, v1.y + v2.y, label: label)
  }

  // Return array: result vector + helplines object
  if helplines {
    (
      result,
      (
        type: "vec-add-helplines",
        v1: v1,
        v2: v2,
      ),
    )
  } else {
    (result,)
  }
}

/// Subtract two vectors (v1 - v2)
#let vec-sub(v1, v2) = {
  if v1.z != none or v2.z != none {
    let z1 = if v1.z == none { 0 } else { v1.z }
    let z2 = if v2.z == none { 0 } else { v2.z }
    vector-3d(v1.x - v2.x, v1.y - v2.y, z1 - z2)
  } else {
    vector(v1.x - v2.x, v1.y - v2.y)
  }
}

/// Scale a vector by a scalar
#let vec-scale(v, scalar) = {
  if v.z != none {
    vector-3d(v.x * scalar, v.y * scalar, v.z * scalar, label: v.label, style: v.style)
  } else {
    vector(v.x * scalar, v.y * scalar, label: v.label, style: v.style)
  }
}

/// Negate a vector
#let vec-neg(v) = vec-scale(v, -1)

/// Dot product of two vectors
#let vec-dot(v1, v2) = {
  let result = v1.x * v2.x + v1.y * v2.y
  if v1.z != none and v2.z != none {
    result += v1.z * v2.z
  }
  result
}

/// Cross product of two 3D vectors (returns a 3D vector)
#let vec-cross(v1, v2) = {
  let z1 = if v1.z == none { 0 } else { v1.z }
  let z2 = if v2.z == none { 0 } else { v2.z }

  vector-3d(
    v1.y * z2 - z1 * v2.y,
    z1 * v2.x - v1.x * z2,
    v1.x * v2.y - v1.y * v2.x,
  )
}

/// Magnitude (length) of a vector
#let vec-magnitude(v) = {
  if v.z != none {
    calc.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
  } else {
    calc.sqrt(v.x * v.x + v.y * v.y)
  }
}

/// Alias for magnitude
#let vec-length = vec-magnitude

/// Get unit vector (normalized)
#let vec-normalize(v) = {
  let mag = vec-magnitude(v)
  if mag == 0 { v } else { vec-scale(v, 1 / mag) }
}

/// Alias for normalize
#let vec-unit = vec-normalize

/// Project v1 onto v2 - returns array: (projection-vector, helplines-object)
#let vec-project(v1, v2, label: none, helplines: true) = {
  let dot = vec-dot(v1, v2)
  let mag-sq = vec-dot(v2, v2)
  if mag-sq == 0 {
    (vector(0, 0, label: label),)
  } else {
    let proj = vec-scale(v2, dot / mag-sq)
    let result = proj + (label: label)

    if helplines {
      (
        result,
        (
          type: "vec-proj-helplines",
          v1: v1,
          v2: v2,
          proj: result,
        ),
      )
    } else {
      (result,)
    }
  }
}

/// Angle between two vectors in radians
#let vec-angle-between(v1, v2) = {
  let dot = vec-dot(v1, v2)
  let m1 = vec-magnitude(v1)
  let m2 = vec-magnitude(v2)
  if m1 == 0 or m2 == 0 { 0 } else {
    calc.acos(dot / (m1 * m2))
  }
}

/// Check if two vectors are parallel
#let vec-parallel(v1, v2) = {
  let cross = v1.x * v2.y - v1.y * v2.x
  calc.abs(cross) < 0.0001
}

/// Check if two vectors are perpendicular
#let vec-perpendicular(v1, v2) = {
  calc.abs(vec-dot(v1, v2)) < 0.0001
}
