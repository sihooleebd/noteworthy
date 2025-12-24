// =====================================================
// VECTOR CANVAS - Vector visualization helpers
// =====================================================

#import "@preview/cetz:0.4.2"
#import "../geometry/vector.typ": *

/// Draw a vector as an arrow from origin to (x, y)
///
/// Parameters:
/// - theme: Theme dictionary
/// - start: Starting point (default: origin)
/// - vec: The vector object
/// - label-pos: Label position along vector (0-1) (default: 0.5)
/// - label-dist: Label offset distance (default: 0.3)
#let draw-vector(
  theme: (:),
  start: (0, 0),
  vec,
  label-pos: 0.5,
  label-dist: 0.3,
) = {
  import cetz.draw: *

  let stroke-col = if vec.style != auto and vec.style != none and "stroke" in vec.style {
    vec.style.stroke
  } else {
    theme.at("plot", default: (:)).at("stroke", default: black)
  }

  let sx = if type(start) == dictionary { start.x } else { start.at(0) }
  let sy = if type(start) == dictionary { start.y } else { start.at(1) }

  let ex = sx + vec.x
  let ey = sy + vec.y

  line(
    (sx, sy),
    (ex, ey),
    stroke: (paint: stroke-col, thickness: 1.5pt),
    mark: (end: "stealth", fill: stroke-col),
  )

  if vec.label != none {
    let mx = sx + (ex - sx) * label-pos
    let my = sy + (ey - sy) * label-pos

    let dx = ex - sx
    let dy = ey - sy
    let len = calc.sqrt(dx * dx + dy * dy)

    if len > 0 {
      // Perpendicular offset
      let ox = -dy / len * label-dist
      let oy = dx / len * label-dist
      content((mx + ox, my + oy), text(fill: stroke-col, vec.label))
    } else {
      content((mx, my), text(fill: stroke-col, vec.label))
    }
  }
}

/// Draw vector components (dashed projections)
#let draw-vector-components(
  theme: (:),
  start: (0, 0),
  vec,
  label-x: none,
  label-y: none,
  color: gray,
) = {
  import cetz.draw: *

  let sx = if type(start) == dictionary { start.x } else { start.at(0) }
  let sy = if type(start) == dictionary { start.y } else { start.at(1) }

  let ex = sx + vec.x
  let ey = sy + vec.y

  // X component (horizontal)
  line((sx, sy), (ex, sy), stroke: (paint: color, dash: "dashed", thickness: 0.8pt))
  // Y component (vertical)
  line((ex, sy), (ex, ey), stroke: (paint: color, dash: "dotted", thickness: 0.8pt))

  if label-x != none {
    content(((sx + ex) / 2, sy - 0.2), text(fill: color, size: 8pt, label-x), anchor: "north")
  }
  if label-y != none {
    content((ex + 0.2, (sy + ey) / 2), text(fill: color, size: 8pt, label-y), anchor: "west")
  }
}

/// Draw vector addition (parallelogram method)
#let draw-vector-addition(
  theme: (:),
  start: (0, 0),
  v1,
  v2,
  label-sum: none,
  mode: "parallelogram",
) = {
  import cetz.draw: *

  let stroke-col = theme.at("plot", default: (:)).at("stroke", default: black)
  let hl-col = theme.at("plot", default: (:)).at("highlight", default: blue)

  let sx = if type(start) == dictionary { start.x } else { start.at(0) }
  let sy = if type(start) == dictionary { start.y } else { start.at(1) }

  let v1-end = (sx + v1.x, sy + v1.y)
  let v2-end = (sx + v2.x, sy + v2.y)
  let sum-end = (sx + v1.x + v2.x, sy + v1.y + v2.y)

  // Draw original vectors
  draw-vector(theme: theme, start: (sx, sy), v1)
  draw-vector(theme: theme, start: (sx, sy), v2)

  if mode == "parallelogram" {
    // Parallelogram sides
    line(v1-end, sum-end, stroke: (paint: gray, thickness: 0.5pt))
    line(v2-end, sum-end, stroke: (paint: gray, thickness: 0.5pt))
  } else {
    // Tip-to-tail: draw v2 from end of v1
    draw-vector(theme: theme, start: v1-end, v2)
  }

  // Resultant
  let sum-vec = vector(v1.x + v2.x, v1.y + v2.y, label: label-sum, style: (stroke: hl-col))
  draw-vector(theme: theme, start: (sx, sy), sum-vec)
}

/// Draw vector projection
#let draw-vector-projection(
  theme: (:),
  start: (0, 0),
  vec-a,
  vec-b,
  label-proj: none,
) = {
  import cetz.draw: *

  let hl-col = theme.at("plot", default: (:)).at("highlight", default: blue)
  let accent-col = theme.at("text-accent", default: purple)

  let sx = if type(start) == dictionary { start.x } else { start.at(0) }
  let sy = if type(start) == dictionary { start.y } else { start.at(1) }

  // Calculate projection
  let proj = vec-project(vec-a, vec-b)

  let a-end = (sx + vec-a.x, sy + vec-a.y)
  let proj-end = (sx + proj.x, sy + proj.y)

  // Extended b axis
  let b-scale = 1.3
  line(
    (sx - vec-b.x * 0.2, sy - vec-b.y * 0.2),
    (sx + vec-b.x * b-scale, sy + vec-b.y * b-scale),
    stroke: (paint: gray, dash: "dashed"),
  )

  // Original vectors
  draw-vector(theme: theme, start: (sx, sy), vec-a)
  draw-vector(theme: theme, start: (sx, sy), vec-b)

  // Perpendicular from a to projection
  line(a-end, proj-end, stroke: (paint: accent-col, dash: "dotted"))

  // Projection vector
  let proj-labeled = vector(proj.x, proj.y, label: label-proj, style: (stroke: hl-col))
  draw-vector(theme: theme, start: (sx, sy), proj-labeled)
}
