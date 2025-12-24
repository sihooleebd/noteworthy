#import "setup.typ": *
#import "./default-schemes.typ": *

#import "./layouts/blocks.typ"

// =====================================================
// NEW GEOMETRY SYSTEM (OO-based)
// =====================================================
// Import all geometry types directly
#import "./geometry/point.typ": *
#import "./geometry/line.typ": *
#import "./geometry/circle.typ": *
#import "./geometry/angle.typ": *
#import "./geometry/polygon.typ": *
#import "./geometry/vector.typ": *
#import "./geometry/func.typ": *
#import "./geometry/construct.typ": *
#import "./geometry/intersect.typ": *
#import "./geometry/core.typ": *

// Import canvas types
#import "./canvas/draw.typ": draw-geo
#import "./canvas/cartesian.typ": (
  cartesian-canvas as cartesian-canvas-impl, graph-canvas as graph-canvas-impl, trig-canvas as trig-canvas-impl,
)
#import "./canvas/polar.typ": polar-canvas as polar-canvas-impl
#import "./canvas/space.typ": (
  draw-point-3d as draw-point-3d-impl, draw-vec-3d as draw-vec-3d-impl, space-canvas as space-canvas-impl,
)
#import "./canvas/blank.typ": blank-canvas as blank-canvas-impl, simple-canvas as simple-canvas-impl
#import "./canvas/vector.typ": (
  draw-vector as draw-vector-impl, draw-vector-addition as draw-vector-addition-impl,
  draw-vector-components as draw-vector-components-impl, draw-vector-projection as draw-vector-projection-impl,
)
#import "./canvas/combi.typ": (
  draw-boxes as draw-boxes-impl, draw-circular as draw-circular-impl, draw-linear as draw-linear-impl,
)

// Canvas types (theme-bound)
#let active-theme = active-theme

#let cartesian-canvas(..args) = {
  align(center)[#cartesian-canvas-impl(..args, theme: active-theme)]
}
#let graph-canvas(..args) = {
  align(center)[#graph-canvas-impl(..args, theme: active-theme)]
}
#let trig-canvas(..args) = {
  align(center)[#trig-canvas-impl(..args, theme: active-theme)]
}
#let polar-canvas(..args) = {
  align(center)[#polar-canvas-impl(..args, theme: active-theme)]
}
#let space-canvas(..args) = {
  align(center)[#space-canvas-impl(..args, theme: active-theme)]
}
#let blank-canvas(..args) = {
  align(center)[#blank-canvas-impl(..args, theme: active-theme)]
}
#let simple-canvas(..args) = simple-canvas-impl(theme: active-theme, ..args)

// Vector drawing helpers
#let draw-vector(..args) = draw-vector-impl(..args, theme: active-theme)
#let draw-vector-components(..args) = draw-vector-components-impl(..args, theme: active-theme)
#let draw-vector-addition(..args) = draw-vector-addition-impl(..args, theme: active-theme)
#let draw-vector-projection(..args) = draw-vector-projection-impl(..args, theme: active-theme)

// Combinatorics helpers
#let draw-boxes(..args) = draw-boxes-impl(..args, theme: active-theme)
#let draw-linear(..args) = draw-linear-impl(..args, theme: active-theme)
#let draw-circular(..args) = draw-circular-impl(..args, theme: active-theme)

// 3D helpers
#let draw-vec-3d(..args) = draw-vec-3d-impl(..args, theme: active-theme)
#let draw-point-3d(..args) = draw-point-3d-impl(..args, theme: active-theme)

// =====================================================
// BACKWARD COMPATIBILITY LAYER
// =====================================================
// These aliases allow old content to work with minimal changes

// Old plot names -> new canvas names
#let rect-plot = cartesian-canvas
#let polar-plot = polar-canvas
#let combi-plot = blank-canvas
#let space-plot = space-canvas
#let blank-plot = blank-canvas

// Old function -> new function (with theme)
#import "@preview/cetz:0.4.2"
#let cetz = cetz

#let plot-function(f, type: "y=x", domain: auto, samples: render-sample-count, label: none, style: (:)) = {
  let stroke-col = if "stroke" in style { style.stroke } else { active-theme.plot.highlight }

  if type == "y=x" {
    let x-dom = if domain == auto { (-5, 5) } else { domain }
    func(f, domain: x-dom, label: label, style: (stroke: stroke-col))
  } else if type == "parametric" {
    let t-dom = if domain == auto { (0, 2 * calc.pi) } else { domain }
    parametric(f, domain: t-dom, label: label, style: (stroke: stroke-col))
  } else if type == "polar" {
    let t-dom = if domain == auto { (0, 2 * calc.pi) } else { domain }
    polar-func(f, domain: t-dom, label: label, style: (stroke: stroke-col))
  }
}

// Old geometry functions (keeping for compatibility)
#let add-polar(func-r, domain: (0, 2 * calc.pi), style: (:)) = {
  polar-func(func-r, domain: domain, style: style)
}

#let add-angle(origin, start-ang, delta, label, radius: 0.5, col: green) = {
  // Convert to new angle object
  let p1 = point(
    origin.at(0) + calc.cos(start-ang),
    origin.at(1) + calc.sin(start-ang),
  )
  let p2 = point(
    origin.at(0) + calc.cos(start-ang + delta),
    origin.at(1) + calc.sin(start-ang + delta),
  )
  angle(p1, point(origin.at(0), origin.at(1)), p2, label: label, radius: radius, fill: col.transparentize(70%))
}

#let add-right-angle(origin, start-ang, radius: 0.5) = {
  let p1 = point(
    origin.at(0) + calc.cos(start-ang),
    origin.at(1) + calc.sin(start-ang),
  )
  let p2 = point(
    origin.at(0) + calc.cos(start-ang + 90deg),
    origin.at(1) + calc.sin(start-ang + 90deg),
  )
  right-angle(p1, point(origin.at(0), origin.at(1)), p2, radius: radius)
}

#let add-polygon(points, label: none, fill: none, stroke: auto) = {
  polygon(
    ..points.map(p => {
      if type(p) == array { point(p.at(0), p.at(1)) } else { p }
    }),
    label: label,
    fill: fill,
  )
}

// Old vector functions -> new
#let draw-vec(start, end, label: none, color: auto, thickness: 1.5pt) = {
  let stroke-col = if color == auto { active-theme.plot.stroke } else { color }
  let v = vector(end.at(0) - start.at(0), end.at(1) - start.at(1), label: label, style: (stroke: stroke-col))
  // This returns the vector object - caller needs to draw it in canvas context
  // For direct usage, wrap in simple-canvas
  draw-vector(start: start, v)
}

#let draw-vec-comps(vec, label-x: none, label-y: none, color: gray) = {
  let v = vector(vec.at(0), vec.at(1))
  draw-vector-components(start: (0, 0), v, label-x: label-x, label-y: label-y, color: color)
}

#let draw-vec-sum(u, v, label-u: $arrow(u)$, label-v: $arrow(v)$, label-sum: auto, mode: "parallelogram") = {
  let v1 = vector(u.at(0), u.at(1), label: label-u)
  let v2 = vector(v.at(0), v.at(1), label: label-v)
  let sum-label = if label-sum == auto { $arrow(u) + arrow(v)$ } else { label-sum }
  draw-vector-addition(start: (0, 0), v1, v2, label-sum: sum-label, mode: mode)
}

#let draw-vec-proj(vec-a, vec-b, label-a: $arrow(a)$, label-b: $arrow(b)$, label-proj: auto) = {
  let v1 = vector(vec-a.at(0), vec-a.at(1), label: label-a)
  let v2 = vector(vec-b.at(0), vec-b.at(1), label: label-b)
  let proj-label = if label-proj == auto { $"proj"_b a$ } else { label-proj }
  draw-vector-projection(start: (0, 0), v1, v2, label-proj: proj-label)
}

// =====================================================
// TABLE PLOTTING (unchanged from original)
// =====================================================
#import "./plots/tableplot.typ"

#let table-plot = tableplot.table-plot.with(theme: active-theme)
#let compact-table = tableplot.compact-table.with(theme: active-theme)
#let value-table = tableplot.value-table.with(theme: active-theme)
#let grid-table = tableplot.grid-table.with(theme: active-theme)

// =====================================================
// LAYOUT BLOCKS (unchanged)
// =====================================================
#import "./layouts/blocks.typ": *
#import "./covers/chapter-cover.typ": *
#import "./covers/main-cover.typ": *
#import "./covers/preface.typ": *
#import "./layouts/outline.typ": *
#import "./covers/page-title.typ": *

#let project = project.with(theme: active-theme)
#let cover = cover.with(theme: active-theme)
#let preface = preface.with(theme: active-theme, content: include "config/preface.typ", authors: authors)
#let outline = outline.with(theme: active-theme)
#let chapter-cover = chapter-cover.with(theme: active-theme)
#let definition = blocks.create-block.with(active-theme.blocks.definition)
#let equation = blocks.create-block.with(active-theme.blocks.equation)
#let example = blocks.create-block.with(active-theme.blocks.example)
#let note = blocks.create-block.with(active-theme.blocks.note)
#let notation = blocks.create-block.with(active-theme.blocks.notation)
#let analysis = blocks.create-block.with(active-theme.blocks.analysis)
#let solution = blocks.create-solution.with(active-theme.blocks.solution)
#let proof = blocks.create-proof.with(active-theme.blocks.proof)
#let theorem = blocks.create-block.with(active-theme.blocks.theorem)
