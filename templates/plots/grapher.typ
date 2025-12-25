#import "@preview/cetz:0.4.2"
#import "@preview/cetz-plot:0.1.3": plot
#import "../setup.typ": render-implicit-count, render-sample-count

/// Plots a mathematical function in various coordinate systems.
/// Supports standard functions, parametric equations, polar curves, implicit equations, and interpolation.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - func: Function to plot (signature depends on type)
/// - type: Function type - "y=x" (standard), "parametric", "polar", "implicit", or "interpolate" (default: "y=x")
/// - domain: Input domain - (x-min, x-max) or (t-min, t-max) depending on type (default: auto)
/// - y-domain: Y range for implicit plots only (default: (-5, 5))
/// - samples: Number of sample points for rendering (default: from config)
/// - label: Optional curve label for legend
/// - color: Override stroke color for the function (default: auto, uses theme)
/// - dashed: Whether to use a dashed line style (default: false)
/// - hole: Array of x (or t) values where holes should appear (default: ())
/// - hole-radius: Radius around each hole point to exclude (default: 0.1)
/// - colored: Interval or array of intervals to fill under the curve (default: ())
///            Single interval: (start, end) or array of intervals: ((start1, end1), (start2, end2))
/// - fill-color: Color for filled areas (default: auto, uses stroke color with 70% transparency)
/// - style: Additional CeTZ plot style dictionary
///
/// Function Types:
/// - "y=x": Standard function f(x) → y
/// - "parametric": Parametric function t → (x(t), y(t))
/// - "polar": Polar function θ → r(θ)
/// - "implicit": Implicit function (x, y) → z for z = 0 contour
/// - "interpolate": Array of points ((x1, y1), (x2, y2), ...) for Lagrangian interpolation
#let plot-function(
  theme: (:),
  func,
  type: "y=x",
  domain: auto,
  y-domain: (-5, 5),
  samples: render-sample-count,
  label: none,
  color: auto,
  dashed: false,
  hole: (),
  hole-radius: 0.05,
  colored: (),
  fill-color: auto,
  style: (:),
) = {
  let highlight-col = if "plot" in theme and "highlight" in theme.plot {
    theme.plot.highlight
  } else {
    black
  }

  let base-color = if color != auto {
    color
  } else if "stroke" in style {
    style.stroke
  } else {
    highlight-col
  }

  let stroke-style = if dashed {
    (paint: base-color, dash: "dashed")
  } else {
    base-color
  }

  let final-style = (stroke: stroke-style) + style

  // Normalize colored parameter to array of intervals
  // If colored is (num, num) -> single interval, wrap it
  // If colored is ((num, num), ...) -> already array of intervals
  let colored-intervals = if colored == () or colored == none {
    ()
  } else {
    // Check if first element starts with "(" in repr (meaning it's an array/tuple)
    let first-repr = repr(colored.at(0))
    if first-repr.starts-with("(") {
      // Already array of intervals
      colored
    } else {
      // Single interval, wrap it
      (colored,)
    }
  }

  // Determine fill color
  let area-fill-color = if fill-color == auto {
    base-color.transparentize(70%)
  } else {
    fill-color
  }

  // Helper function to split domain into segments around holes
  // Returns array of (start, end) tuples for each segment
  let split-domain(dom, holes, radius) = {
    if holes.len() == 0 {
      return ((dom.at(0), dom.at(1)),)
    }

    // Sort holes
    let sorted-holes = holes.sorted()

    // Filter holes that are within the domain (with some margin)
    let valid-holes = sorted-holes.filter(h => h > dom.at(0) and h < dom.at(1))

    if valid-holes.len() == 0 {
      return ((dom.at(0), dom.at(1)),)
    }

    let segments = ()
    let current-start = dom.at(0)

    for h in valid-holes {
      let seg-end = h - radius
      if seg-end > current-start {
        segments.push((current-start, seg-end))
      }
      current-start = h + radius
    }

    // Add final segment
    if current-start < dom.at(1) {
      segments.push((current-start, dom.at(1)))
    }

    segments
  }

  // Calculate samples for a segment proportionally
  let segment-samples(seg, total-dom, total-samples) = {
    let total-len = total-dom.at(1) - total-dom.at(0)
    let seg-len = seg.at(1) - seg.at(0)
    let proportion = seg-len / total-len
    int(calc.max(2, calc.round(total-samples * proportion)))
  }

  let common-args = (
    style: final-style,
  )

  if label != none {
    // Wrap label in theme's text color
    let colored-label = text(fill: theme.plot.stroke, label)
    common-args.insert("label", colored-label)
  }

  if type == "y=x" {
    // Standard Function: y = f(x)
    let x-dom = if domain == auto { (-5, 5) } else { domain }
    let segments = split-domain(x-dom, hole, hole-radius)

    // Draw filled areas first (so they appear behind the curve)
    for interval in colored-intervals {
      let fill-samples = segment-samples(interval, x-dom, samples)
      plot.add(
        domain: interval,
        samples: fill-samples,
        fill: true,
        style: (stroke: none, fill: area-fill-color),
        func,
      )
    }

    for (idx, seg) in segments.enumerate() {
      let seg-samples = segment-samples(seg, x-dom, samples)
      let seg-args = common-args
      seg-args.insert("samples", seg-samples)
      // Only add label to first segment
      if idx > 0 {
        let _ = seg-args.remove("label", default: none)
      }
      plot.add(
        domain: seg,
        ..seg-args,
        func,
      )
    }
    
    // Draw explicit hole markers (poked holes)
    for h in hole {
      // Calculate y value for the hole
      // Note: We assume the hole is at f(h), even if undefined, we approximate or expect user to know. 
      // But typically a hole exists because the limit exists.
      // We can try to evaluate f(h+epsilon) approx.
      let y-val = try { func(h) } catch(e) { func(h + 0.0001) }
      
      // If still failing, skip
      if y-val != none {
        plot.add(
           ((h, y-val),),
           mark: "o",
           mark-size: .15,
           style: (stroke: final-style.stroke, fill: white),
        )
      }
    }
  } else if type == "parametric" {
    // Parametric Curve: (x(t), y(t))
    let t-dom = if domain == auto { (0, 2 * calc.pi) } else { domain }
    let segments = split-domain(t-dom, hole, hole-radius)

    for (idx, seg) in segments.enumerate() {
      let seg-samples = segment-samples(seg, t-dom, samples)
      let seg-args = common-args
      seg-args.insert("samples", seg-samples)
      if idx > 0 {
        let _ = seg-args.remove("label", default: none)
      }
      plot.add(
        domain: seg,
        ..seg-args,
        func,
      )
    }
  } else if type == "polar" {
    // Polar Curve: r(θ)
    let t-dom = if domain == auto { (0, 2 * calc.pi) } else { domain }
    let segments = split-domain(t-dom, hole, hole-radius)
    let polar-func = t => (func(t) * calc.cos(t), func(t) * calc.sin(t))

    // Draw filled areas first (so they appear behind the curve)
    for interval in colored-intervals {
      let fill-samples = segment-samples(interval, t-dom, samples)
      plot.add(
        domain: interval,
        samples: fill-samples,
        fill: true,
        style: (stroke: none, fill: area-fill-color),
        polar-func,
      )
    }

    for (idx, seg) in segments.enumerate() {
      let seg-samples = segment-samples(seg, t-dom, samples)
      let seg-args = common-args
      seg-args.insert("samples", seg-samples)
      if idx > 0 {
        let _ = seg-args.remove("label", default: none)
      }
      plot.add(
        domain: seg,
        ..seg-args,
        polar-func,
      )
    }
  } else if type == "implicit" {
    // Implicit Equation: f(x, y) = 0
    let x-dom = if domain == auto { (-5, 5) } else { domain }

    // Use implicit count if samples is still default
    let effective-samples = if samples == render-sample-count { render-implicit-count } else { samples }

    plot.add-contour(
      x-domain: x-dom,
      y-domain: y-domain,
      x-samples: effective-samples,
      y-samples: effective-samples,
      z: 0,
      fill: false,
      style: final-style,
      func,
    )

    if label != none {
      plot.annotate({
        import cetz.draw: *
        content(
          (x-dom.at(1), y-domain.at(1)),
          text(fill: theme.plot.stroke, label),
          anchor: "south-east",
          padding: 0.2,
          fill: none,
          stroke: none,
        )
      })
    }
  } else if type == "interpolate" {
    // Lagrangian Interpolation from array of points
    // func is expected to be an array of (x, y) points: ((x1, y1), (x2, y2), ...)
    let points = func

    // Extract x and y values
    let xs = points.map(p => p.at(0))
    let ys = points.map(p => p.at(1))
    let n = points.len()

    // Lagrangian interpolation polynomial
    // P(x) = Σᵢ yᵢ * Lᵢ(x)
    // where Lᵢ(x) = Πⱼ≠ᵢ (x - xⱼ) / (xᵢ - xⱼ)
    let lagrange-func = x => {
      let result = 0
      for i in range(n) {
        // Compute Lᵢ(x)
        let li = 1
        for j in range(n) {
          if i != j {
            li = li * (x - xs.at(j)) / (xs.at(i) - xs.at(j))
          }
        }
        result = result + ys.at(i) * li
      }
      result
    }

    // Determine domain from points if not specified
    let x-dom = if domain == auto {
      let x-min = calc.min(..xs)
      let x-max = calc.max(..xs)
      let padding = (x-max - x-min) * 0.1
      (x-min - padding, x-max + padding)
    } else {
      domain
    }

    let segments = split-domain(x-dom, hole, hole-radius)

    // Draw filled areas first (so they appear behind the curve)
    for interval in colored-intervals {
      let fill-samples = segment-samples(interval, x-dom, samples)
      plot.add(
        domain: interval,
        samples: fill-samples,
        fill: true,
        style: (stroke: none, fill: area-fill-color),
        lagrange-func,
      )
    }

    for (idx, seg) in segments.enumerate() {
      let seg-samples = segment-samples(seg, x-dom, samples)
      let seg-args = common-args
      seg-args.insert("samples", seg-samples)
      // Only add label to first segment
      if idx > 0 {
        let _ = seg-args.remove("label", default: none)
      }
      plot.add(
        domain: seg,
        ..seg-args,
        lagrange-func,
      )
    }
  }
}

