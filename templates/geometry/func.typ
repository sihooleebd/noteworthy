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
    val != none and val == val and val != calc.inf and val != -calc.inf and calc.abs(val) < 1e10
  }

  // Helper: Safely evaluate function, returning none for errors
  // Typst doesn't have try-catch, so we check for common error patterns
  let safe-eval(f, x) = {
    // Skip x=0 if it might cause issues (very common singularity)
    // Also skip values very close to integers that are common singularities
    let eps = 1e-10

    // Try to evaluate - if x is extremely small, it might cause division issues
    if calc.abs(x) < eps {
      return none
    }

    // Evaluate the function
    let y = f(x)

    // Check if result is valid
    if is-valid(y) {
      y
    } else {
      none
    }
  }

  let points = ()
  let step = (x-max - x-min) / samples
  let prev-y = none
  let in-segment = false

  for i in range(samples + 1) {
    let x = x-min + i * step
    let y = safe-eval(f, x)

    if y != none {
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

  // Helper: Safely evaluate, handling division by zero gracefully
  let safe-eval(f, x) = {
    let eps = 1e-10
    if calc.abs(x) < eps {
      return none
    }
    let y = f(x)
    if is-valid(y) { y } else { none }
  }

  let points = ()
  let prev-y = none
  let in-segment = false

  for i in range(samples + 1) {
    // Use cubic spacing to concentrate samples near center
    // u^3 is flat at 0, meaning small change in output for change in input -> high density
    let t = i / samples // 0 to 1
    let u = 2 * t - 1 // -1 to 1
    let warped = u * u * u // -1 to 1, dense near 0
    let t-warped = (warped + 1) / 2 // 0 to 1

    // Map to x-range with density near center
    let x = if center >= x-min and center <= x-max {
      // Warp around center
      let half-range = calc.max(center - x-min, x-max - center)
      center + warped * half-range // Use raw warped (-1 to 1) directly scaled
    } else {
      x-min + t * (x-max - x-min)
    }

    // Clamp to domain
    if x < x-min or x > x-max { continue }

    let y = safe-eval(f, x)

    if y != none {
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
  singularity: 0,
  hole: (),
  filled-hole: (),
  label: none,
  style: auto,
) = {
  // Compute cached points if robust mode
  let cached = if robust and func-type == "standard" {
    oscillation-sample(f, domain.at(0), domain.at(1), center: singularity)
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
    hole: hole,
    filled-hole: filled-hole,
    label: label,
    style: style,
    cached-points: cached,
  )
}

#let graph(f, domain: (-5, 5), hole: (), filled-hole: (), label: none, style: auto) = {
  func(f, domain: domain, func-type: "standard", hole: hole, filled-hole: filled-hole, label: label, style: style)
}

/// Create a robust function (for singularities)
#let robust-func(f, domain: (-5, 5), singularity: 0, hole: (), filled-hole: (), label: none, style: auto) = {
  func(
    f,
    domain: domain,
    func-type: "standard",
    robust: true,
    singularity: singularity,
    hole: hole,
    filled-hole: filled-hole,
    label: label,
    style: style,
  )
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
