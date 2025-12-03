#import "@preview/cetz:0.4.2"

/// Draws a vector arrow from start to end point with optional label.
/// Supports both 2D (x, y) and 3D (x, y, z) coordinates.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - start: Starting point coordinates
/// - end: Ending point coordinates
/// - label: Optional label content to display
/// - label-pos: Position along vector for label (0 to 1, default: 0.5)
/// - label-dist: Distance offset from vector line (default: 0.3)
/// - label-anchor: Text anchor position (default: auto)
/// - color: Vector color (default: theme.plot.stroke)
/// - thickness: Line thickness (default: 1.5pt)
/// - arrow-scale: Arrow head scale factor (default: 1)
#let draw-vec(
  theme: (:),
  start,
  end,
  label: none,
  label-pos: 0.5,
  label-dist: 0.3,
  label-anchor: auto,
  color: auto,
  thickness: 1.5pt,
  arrow-scale: 1,
) = {
  import cetz.draw: *

  let stroke-col = if color == auto { theme.plot.stroke } else { color }
  let fill-col = if color == auto { theme.plot.stroke } else { color }

  group({
    line(
      start,
      end,
      stroke: (paint: stroke-col, thickness: thickness),
      mark: (end: "stealth", scale: arrow-scale, fill: stroke-col),
    )
    if label != none {
      let dx = end.at(0) - start.at(0)
      let dy = end.at(1) - start.at(1)
      let dz = if start.len() > 2 { end.at(2) - start.at(2) } else { 0 }

      let mx = start.at(0) + dx * label-pos
      let my = start.at(1) + dy * label-pos
      let mz = if start.len() > 2 { start.at(2) + dz * label-pos } else { 0 }

      let len-sq = dx * dx + dy * dy + dz * dz
      let len = calc.sqrt(len-sq)

      let ox = 0
      let oy = 0
      let oz = 0

      if len != 0 {
        // Calculate perpendicular offset for label positioning
        if start.len() == 2 {
          // 2D: Use perpendicular direction
          ox = (-dy / len) * label-dist
          oy = (dx / len) * label-dist
        } else {
          // 3D: Use small Z offset for visibility
          oz = label-dist
        }
      }

      let label-x = mx + ox
      let label-y = my + oy
      let label-z = mz + oz

      let txt-anchor = if label-anchor != auto { label-anchor } else {
        "center"
      }

      let pos = if start.len() > 2 { (label-x, label-y, label-z) } else { (label-x, label-y) }

      content(
        pos,
        text(fill: stroke-col, label),
        anchor: txt-anchor,
      )
    }
  })
}


/// Draws dashed lines showing the component breakdown of a vector.
/// Displays X and Y components (and Z in 3D) of a vector from an origin.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - origin: Starting point (default: (0, 0))
/// - vec: Vector components (x, y) or (x, y, z)
/// - label-x: Optional label for X component
/// - label-y: Optional label for Y component
/// - color: Component line color (default: gray)
#let draw-vec-comps(
  theme: (:),
  origin: (0, 0),
  vec,
  label-x: none,
  label-y: none,
  color: gray,
) = {
  import cetz.draw: *

  let is-3d = vec.len() > 2
  let vx = vec.at(0)
  let vy = vec.at(1)
  let vz = if is-3d { vec.at(2) } else { 0 }

  let ox = origin.at(0)
  let oy = origin.at(1)
  let oz = if origin.len() > 2 { origin.at(2) } else { 0 }

  let end-pt = if is-3d { (ox + vx, oy + vy, oz + vz) } else { (ox + vx, oy + vy) }

  group({
    if is-3d {
      // Draw 3D projection box
      let xy-proj = (ox + vx, oy + vy, oz)
      line(origin, (ox + vx, oy, oz), stroke: (paint: color, dash: "dashed", thickness: 0.5pt))
      line((ox + vx, oy, oz), xy-proj, stroke: (paint: color, dash: "dashed", thickness: 0.5pt))
      line(origin, (ox, oy + vy, oz), stroke: (paint: color, dash: "dashed", thickness: 0.5pt))
      line((ox, oy + vy, oz), xy-proj, stroke: (paint: color, dash: "dashed", thickness: 0.5pt))

      // Vertical line to final point
      line(xy-proj, end-pt, stroke: (paint: color, dash: "dotted", thickness: 0.8pt))
    } else {
      // 2D projection
      let x-proj = (end-pt.at(0), origin.at(1))
      let y-proj = (origin.at(0), end-pt.at(1))

      line(origin, x-proj, stroke: (paint: color, dash: "dashed", thickness: 0.8pt))
      line(x-proj, end-pt, stroke: (paint: color, dash: "dotted", thickness: 0.8pt))
      line(origin, y-proj, stroke: (paint: color, dash: "dashed", thickness: 0.8pt))
      line(y-proj, end-pt, stroke: (paint: color, dash: "dotted", thickness: 0.8pt))
    }

    if label-x != none {
      content((ox + vx / 2, oy, oz), text(fill: color, size: 8pt, label-x), anchor: "north", padding: 0.2)
    }
    if label-y != none {
      content((ox, oy + vy / 2, oz), text(fill: color, size: 8pt, label-y), anchor: "east", padding: 0.2)
    }
  })
}

/// Draws vector addition visualization using parallelogram or tip-to-tail method.
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - origin: Starting point (default: (0, 0))
/// - u: First vector components
/// - v: Second vector components
/// - label-u: Label for vector u (default: $vec(u)$)
/// - label-v: Label for vector v (default: $vec(v)$)
/// - label-sum: Label for sum vector (default: $vec(u) + vec(v)$)
/// - mode: Visualization mode: "parallelogram" or "tip-to-tail" (default: "parallelogram")
#let draw-vec-sum(
  theme: (:),
  origin: (0, 0),
  u,
  v,
  label-u: $vec(u)$,
  label-v: $vec(v)$,
  label-sum: $vec(u) + vec(v)$,
  mode: "parallelogram",
) = {
  import cetz.draw: *
  let main-col = theme.plot.stroke
  let hl-col = theme.plot.highlight
  let sec-col = gray

  let ox = origin.at(0)
  let oy = origin.at(1)
  let oz = if origin.len() > 2 { origin.at(2) } else { 0 }

  let ux = u.at(0)
  let uy = u.at(1)
  let uz = if u.len() > 2 { u.at(2) } else { 0 }

  let vx = v.at(0)
  let vy = v.at(1)
  let vz = if v.len() > 2 { v.at(2) } else { 0 }

  let u-end = (ox + ux, oy + uy, oz + uz)
  let v-end = (ox + vx, oy + vy, oz + vz)
  let sum-end = (ox + ux + vx, oy + uy + vy, oz + uz + vz)

  draw-vec(theme: theme, origin, u-end, label: label-u, color: main-col)
  draw-vec(theme: theme, origin, v-end, label: label-v, color: main-col)

  if mode == "parallelogram" {
    draw-vec(theme: theme, u-end, sum-end, color: sec-col, thickness: 0.5pt, arrow-scale: 0)
    draw-vec(theme: theme, v-end, sum-end, color: sec-col, thickness: 0.5pt, arrow-scale: 0)
    draw-vec(theme: theme, origin, sum-end, label: label-sum, color: hl-col)
  } else {
    // Tip-to-tail
    draw-vec(theme: theme, u-end, sum-end, label: label-v, color: main-col)
    draw-vec(theme: theme, origin, sum-end, label: label-sum, color: hl-col)
  }
}

/// Draws vector projection visualization showing proj_b(a).
///
/// Parameters:
/// - theme: Theme dictionary containing plot styling
/// - origin: Starting point (default: (0, 0))
/// - vec-a: Vector to be projected
/// - vec-b: Vector to project onto
/// - label-a: Label for vector a (default: $vec(a)$)
/// - label-b: Label for vector b (default: $vec(b)$)
/// - label-proj: Label for projection (default: $text("proj")_b a$)
#let draw-vec-proj(
  theme: (:),
  origin: (0, 0),
  vec-a,
  vec-b,
  label-a: $vec(a)$,
  label-b: $vec(b)$,
  label-proj: $text("proj")_b a$,
) = {
  import cetz.draw: *

  let ox = origin.at(0)
  let oy = origin.at(1)
  let oz = if origin.len() > 2 { origin.at(2) } else { 0 }

  let ax = vec-a.at(0)
  let ay = vec-a.at(1)
  let az = if vec-a.len() > 2 { vec-a.at(2) } else { 0 }

  let bx = vec-b.at(0)
  let by = vec-b.at(1)
  let bz = if vec-b.len() > 2 { vec-b.at(2) } else { 0 }

  // Calculate projection: proj_b(a) = (a · b / |b|²) * b
  let dot = ax * bx + ay * by + az * bz
  let mag-b-sq = bx * bx + by * by + bz * bz
  let scale = if mag-b-sq != 0 { dot / mag-b-sq } else { 0 }

  let proj-x = bx * scale
  let proj-y = by * scale
  let proj-z = bz * scale

  let a-end = (ox + ax, oy + ay, oz + az)
  let b-end = (ox + bx, oy + by, oz + bz)
  let proj-end = (ox + proj-x, oy + proj-y, oz + proj-z)

  // Draw extended b axis
  line(
    (ox - bx * 0.2, oy - by * 0.2, oz - bz * 0.2),
    (ox + bx * 1.2, oy + by * 1.2, oz + bz * 1.2),
    stroke: (paint: gray, dash: "dashed"),
  )

  draw-vec(theme: theme, origin, a-end, label: label-a, color: theme.plot.stroke)

  // Draw perpendicular from a to projection
  line(
    a-end,
    proj-end,
    stroke: (paint: theme.text-accent, dash: "dotted"),
  )

  draw-vec(
    theme: theme,
    origin,
    proj-end,
    label: label-proj,
    color: theme.plot.highlight,
    thickness: 2pt,
  )

  draw-vec(theme: theme, origin, b-end, label: label-b, color: theme.plot.stroke)
}
