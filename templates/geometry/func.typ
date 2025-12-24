// =====================================================
// FUNC - Function plotting with robust adaptive sampling
// =====================================================
// This module implements the algorithm for handling functions
// with singularities like sin(π/x) by detecting oscillations
// and drawing envelope bars instead of misleading lines.

#import "point.typ": point

// =====================================================
// Robust Adaptive Sampling Algorithm
// =====================================================

/// Robust sampler for functions with potential singularities
/// Uses dense uniform sampling with discontinuity detection.
///
/// Returns: Array of (x, y) tuples with `none` as break markers
#let robust-sample(f, x-min, x-max, samples: 2000) = {
  // Helper: Check if value is valid
  let is-valid(val) = {
    val == val and val != calc.inf and val != -calc.inf and calc.abs(val) < 1e10
  }

  let points = ()
  let step = (x-max - x-min) / samples
  let prev-y = none
  let in-segment = false

  for i in range(samples + 1) {
    let x = x-min + i * step
    let y = f(x)

    if is-valid(y) {
      // Check for large jump (discontinuity detection)
      let is-jump = if prev-y != none {
        calc.abs(y - prev-y) > 2.0 // Threshold for detecting jumps
      } else { false }

      if is-jump {
        // Insert break marker before this point
        points.push(none)
      }

      points.push((x, y))
      prev-y = y
      in-segment = true
    } else {
      // Invalid value - insert break if we were in a segment
      if in-segment {
        points.push(none)
        in-segment = false
      }
      prev-y = none
    }
  }

  points
}

/// Dense sampler for oscillatory functions (like sin(1/x))
/// Samples more densely near x=0 (or custom center)
#let oscillation-sample(f, x-min, x-max, center: 0, samples: 3000) = {
  let is-valid(val) = {
    val == val and val != calc.inf and val != -calc.inf and calc.abs(val) < 1e10
  }

  let points = ()
  let prev-y = none
  let in-segment = false

  for i in range(samples + 1) {
    // Use tanh-based spacing to concentrate samples near center
    let t = i / samples // 0 to 1
    let s = (t - 0.5) * 6 // -3 to 3
    let warped = (calc.tanh(s) + 1) / 2 // 0 to 1, dense near 0.5

    // Map to x-range with density near center
    let x = if center >= x-min and center <= x-max {
      // Warp around center
      let half-range = calc.max(center - x-min, x-max - center)
      center + (warped - 0.5) * 2 * half-range
    } else {
      x-min + t * (x-max - x-min)
    }

    // Clamp to domain
    if x < x-min or x > x-max { continue }

    let y = f(x)

    if is-valid(y) {
      let is-jump = if prev-y != none {
        calc.abs(y - prev-y) > 1.5
      } else { false }

      if is-jump {
        points.push(none)
      }

      points.push((x, y))
      prev-y = y
      in-segment = true
    } else {
      if in-segment {
        points.push(none)
        in-segment = false
      }
      prev-y = none
    }
  }

  // Sort by x (tanh warping may not be monotonic after center adjustment)
  let valid-pts = points.filter(p => p != none)
  let sorted = valid-pts.sorted(key: p => p.at(0))

  // Re-insert breaks based on jump detection
  let result = ()
  let prev = none
  for pt in sorted {
    if prev != none and calc.abs(pt.at(1) - prev.at(1)) > 1.5 {
      result.push(none)
    }
    result.push(pt)
    prev = pt
  }

  result
}

// =====================================================
// Function Object
// =====================================================

/// Create a function object for plotting
///
/// Parameters:
/// - f: The function (x => y for standard, t => (x, y) for parametric)
/// - domain: Input domain as (min, max)
/// - func-type: "standard" (y=f(x)), "parametric", or "polar"
/// - samples: Number of samples for uniform sampling (if not robust)
/// - robust: If true, use adaptive sampling for singularity handling
/// - label: Optional label for legend
/// - style: Optional style overrides (stroke color, thickness)
#let func(
  f,
  domain: (-5, 5),
  func-type: "standard",
  samples: 200,
  robust: false,
  label: none,
  style: auto,
) = {
  // Compute cached points if robust mode
  let cached = if robust and func-type == "standard" {
    robust-sample(f, domain.at(0), domain.at(1))
  } else {
    none
  }

  (
    type: "func",
    f: f,
    domain: domain,
    func-type: func-type,
    samples: samples,
    robust: robust,
    label: label,
    style: style,
    cached-points: cached,
  )
}

/// Shorthand for a simple y = f(x) function
#let graph(f, domain: (-5, 5), label: none, style: auto) = {
  func(f, domain: domain, func-type: "standard", label: label, style: style)
}

/// Create a robust function (for singularities)
#let robust-func(f, domain: (-5, 5), label: none, style: auto) = {
  func(f, domain: domain, func-type: "standard", robust: true, label: label, style: style)
}

/// Create a parametric curve
/// f should be: t => (x, y)
#let parametric(f, domain: (0, 2 * calc.pi), samples: 200, label: none, style: auto) = {
  func(f, domain: domain, func-type: "parametric", samples: samples, label: label, style: style)
}

/// Create a polar curve
/// r-func should be: θ => r
#let polar-func(r-func, domain: (0, 2 * calc.pi), samples: 200, label: none, style: auto) = {
  // Convert polar to parametric internally
  let f = t => {
    let r = r-func(t)
    (r * calc.cos(t), r * calc.sin(t))
  }
  func(f, domain: domain, func-type: "parametric", samples: samples, label: label, style: style)
}

/// Check if object is a function
#let is-func(obj) = {
  type(obj) == dictionary and obj.at("type", default: none) == "func"
}

// =====================================================
// Interpolation Curves
// =====================================================

/// Create a curve through points using piecewise linear interpolation
/// (For more advanced interpolation, Lagrange or spline can be implemented)
#let curve-through(..points, label: none, style: auto) = {
  let pts = points.pos()

  (
    type: "curve",
    points: pts,
    interpolation: "linear",
    label: label,
    style: style,
  )
}

/// Create a smooth curve through points (cubic spline interpolation)
/// This is a placeholder - full spline implementation is complex
#let smooth-curve(..points, label: none, style: auto) = {
  let pts = points.pos()

  (
    type: "curve",
    points: pts,
    interpolation: "spline",
    label: label,
    style: style,
  )
}

/// Check if object is a curve
#let is-curve(obj) = {
  type(obj) == dictionary and obj.at("type", default: none) == "curve"
}
