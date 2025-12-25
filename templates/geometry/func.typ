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

/// Helper: Check if value is valid
#let is-valid(val) = {
  val != none and val == val and val != calc.inf and val != -calc.inf and calc.abs(val) < 1e10
}

/// Helper: Safely evaluate function, returning none for errors
#let safe-eval(f, x) = {
  // Only skip exactly 0 to avoid division by zero in 1/x terms
  // Use a much smaller epsilon - we want to sample as close to 0 as possible
  let eps = 1e-15
  if x == 0 or calc.abs(x) < eps {
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

/// Adaptive sampler with zone-based refinement for oscillatory functions.
/// Forces dense sampling near x=0 where 1/x-type singularities cause rapid oscillation.
#let adaptive-sample(f, x-min, x-max, y-min: -10, y-max: 10, width: 10, height: 10, samples: 200, tolerance: 0.1) = {
  let range-width = x-max - x-min
  let range-height = y-max - y-min

  let x-scale = if range-width == 0 { 1 } else { width / range-width }
  let y-scale = if range-height == 0 { 1 } else { height / range-height }

  // Base limits
  let min-step = range-width / 4000
  let max-step = range-width / (samples / 5)

  let points = ()
  let x = x-min
  let h = range-width / samples

  let x-curr = x
  let y-curr = safe-eval(f, x-curr)
  points.push(if y-curr != none { (x-curr, y-curr) } else { none })

  let safety-limit = 10000
  let count = 0

  while x < x-max {
    count += 1
    if count > safety-limit { break }

    // ZONE-BASED SAMPLING: Force smaller steps near x=0
    // Functions with 1/x terms oscillate faster as x approaches 0
    let zone-factor = 1.0
    if calc.abs(x) < 0.5 {
      // The closer to 0, the smaller the step should be
      // At x=0.1, factor = 0.2; at x=0.01, factor = 0.02
      zone-factor = calc.max(0.02, calc.abs(x) * 2)
    }
    let local-max-step = max-step * zone-factor

    // Clamp h with zone-aware max
    if h < min-step { h = min-step }
    if h > local-max-step { h = local-max-step }
    if x + h > x-max { h = x-max - x }
    if h <= 1e-15 { break }

    let x-next = x + h
    let y-next = safe-eval(f, x-next)

    // Handle invalid points
    if y-next == none {
      points.push(none)
      x = x-next
      x-curr = x
      y-curr = safe-eval(f, x)
      if y-curr != none { points.push((x-curr, y-curr)) }
      continue
    }

    if y-curr == none {
      x = x-next
      x-curr = x
      y-curr = y-next
      points.push((x-curr, y-curr))
      continue
    }

    // Sample midpoint and quarter points for oscillation detection
    let x-mid = x + h * 0.5
    let x-q1 = x + h * 0.25
    let x-q3 = x + h * 0.75
    let y-mid = safe-eval(f, x-mid)
    let y-q1 = safe-eval(f, x-q1)
    let y-q3 = safe-eval(f, x-q3)

    let accept = true

    if y-mid != none {
      let y-predict = (y-curr + y-next) / 2.0
      let chord-error = calc.abs(y-mid - y-predict) * y-scale

      // SECOND DERIVATIVE CHECK: Detect oscillation even with small amplitude
      // If midpoint is above/below the line by much relative to the local values
      let local-variation = calc.max(calc.abs(y-curr), calc.abs(y-next), 0.001)
      let relative-error = calc.abs(y-mid - y-predict) / local-variation

      // Refine if: chord error high OR significant relative deviation
      if chord-error > tolerance or relative-error > 0.3 {
        if h > min-step * 1.1 {
          h = h / 2
          accept = false
        }
      } else if chord-error < tolerance * 0.1 and relative-error < 0.05 and zone-factor >= 1.0 {
        // Only accelerate if NOT in a sensitive zone and very flat
        h = h * 1.3
      }
    } else {
      points.push(none)
      points.push((x-next, y-next))
    }

    if accept {
      // Include interior points for smooth rendering
      if y-q1 != none { points.push((x-q1, y-q1)) }
      if y-mid != none { points.push((x-mid, y-mid)) }
      if y-q3 != none { points.push((x-q3, y-q3)) }
      points.push((x-next, y-next))

      x = x-next
      x-curr = x
      y-curr = y-next
    }
  }

  // Filter adjacent nones
  let result = ()
  let last-none = false
  for p in points {
    if p == none {
      if not last-none {
        result.push(none)
        last-none = true
      }
    } else {
      result.push(p)
      last-none = false
    }
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
  adaptive: true,
  hole: (),
  filled-hole: (),
  label: none,
  style: auto,
) = {
  // DEFER: cached-points is now always none for adaptive graphs
  // Sampling happens in draw-func-obj where screen size is known
  let cached = none

  (
    type: "func",
    f: f,
    domain: domain,
    func-type: func-type,
    samples: samples,
    robust: adaptive,
    hole: hole,
    filled-hole: filled-hole,
    label: label,
    style: style,
    cached-points: cached,
  )
}

#let graph(f, domain: (-5, 5), samples: 200, adaptive: true, hole: (), filled-hole: (), label: none, style: auto) = {
  func(
    f,
    domain: domain,
    func-type: "standard",
    samples: samples,
    adaptive: adaptive,
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
