#import "setup.typ": *
#import "./default-schemes.typ": *

#import "./blocks/mod.typ": *

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
#import "./geometry/calculus.typ": *
#import "./geometry/table.typ": *

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
#import "./canvas/data.typ": *

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
// TABLE RENDERING (OO-based)
// =====================================================
// table-data, value-table-data, grid-data constructors are imported via geometry
// Convenience wrappers that auto-apply theme:

#let table-plot(headers: (), data: (), ..args) = {
  let obj = table-data(headers, data, style: args.named())
  render-table(obj, active-theme)
}

#let compact-table(headers: (), data: (), ..args) = {
  let obj = table-data(headers, data, style: args.named())
  render-table(obj, active-theme)
}

#let value-table(variable: $x$, func: $f(x)$, values: (), results: (), ..args) = {
  let obj = value-table-data(variable, func, values, results, style: args.named())
  render-table(obj, active-theme)
}

#let grid-table(data: (), show-indices: false, ..args) = {
  let obj = grid-data(data, show-indices: show-indices, style: args.named())
  render-grid(obj, active-theme)
}


// =====================================================
// LAYOUT BLOCKS (unchanged)
// =====================================================
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
#let definition = create-block.with(active-theme.blocks.definition)
#let equation = create-block.with(active-theme.blocks.equation)
#let example = create-block.with(active-theme.blocks.example)
#let note = create-block.with(active-theme.blocks.note)
#let notation = create-block.with(active-theme.blocks.notation)
#let analysis = create-block.with(active-theme.blocks.analysis)
#let solution = create-solution.with(active-theme.blocks.solution)
#let proof = create-proof.with(active-theme.blocks.proof)
#let theorem = create-block.with(active-theme.blocks.theorem)
