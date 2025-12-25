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
  // Skip x=0 if it might cause issues (very common singularity)
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



/// Adaptive sampler based on slope change (curvature)
/// Starts from left, adjusting step size based on the "change rate of the current slope"
#let adaptive-sample(f, x-min, x-max, samples: 200, tolerance: 1.0) = {
  let range-width = x-max - x-min
  let min-step = range-width / (samples * 100)
  let max-step = range-width / (samples / 5)
  if min-step < 1e-9 { min-step = 1e-9 }
  
  let points = ()
  let x = x-min
  let h = range-width / samples // Initial step guess
  
  // Evaluation cache to avoid re-calculating
  let x-curr = x
  let y-curr = safe-eval(f, x-curr)
  
  points.push(if y-curr != none { (x-curr, y-curr) } else { none })
  
  while x < x-max {
    // Clamp h
    if h < min-step { h = min-step }
    if h > max-step { h = max-step }
    if x + h > x-max { h = x-max - x }
    if h <= 0 { break }
    
    let x-next = x + h
    let y-next = safe-eval(f, x-next)
    
    // If we hit an invalid point (singularity), just step over it
    if y-next == none {
      points.push(none)
      x = x-next
      x-curr = x
      y-curr = safe-eval(f, x) // Try to get back on track
      // if y-curr is still none, next loop will handle
      if y-curr != none { points.push((x-curr, y-curr)) }
      continue
    }
    
    if y-curr == none {
      // We were in invalid territory, now valid
      x = x-next
      x-curr = x
      y-curr = y-next
      points.push((x-curr, y-curr))
      continue
    }
    
    // Calculate slope change
    // We check the midpoint to see if it aligns linearly
    let x-mid = x + h / 2
    let y-mid = safe-eval(f, x-mid)
    
    let accept = true
    
    if y-mid != none {
      let s1 = (y-mid - y-curr) / (h / 2)
      let s2 = (y-next - y-mid) / (h / 2)
      let change = calc.abs(s2 - s1)
      
      if change > tolerance and h > min-step {
        // Curvature too high, refine step
        h = h / 2
        accept = false
      } else {
        // Accept step
        points.push((x-mid, y-mid))
        points.push((x-next, y-next))
        
        // If very flat, try increasing step for next time
        if change < tolerance * 0.1 {
          h = h * 1.5
        }
      }
    } else {
      // Midpoint invalid? Treat as discontinuity
      points.push(none)
      points.push((x-next, y-next))
    }
    
    if accept {
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
  // Compute cached points if robust mode
  let cached = if adaptive and func-type == "standard" {
    adaptive-sample(f, domain.at(0), domain.at(1), samples: samples)
  } else {
    none
  }
  
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
