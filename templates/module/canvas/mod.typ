// =====================================================
// CANVAS MODULE - Main entrypoint for canvas system
// =====================================================
// Re-exports all canvas types with theme binding.

#import "../../core/setup.typ": active-theme

// Drawing utilities (no theme binding needed)
#import "draw.typ": draw-geo

// Import raw implementations
#import "cartesian.typ": (
  cartesian-canvas as cartesian-canvas-impl, graph-canvas as graph-canvas-impl, trig-canvas as trig-canvas-impl,
)
#import "polar.typ": polar-canvas as polar-canvas-impl
#import "space.typ": (
  draw-point-3d as draw-point-3d-impl, draw-vec-3d as draw-vec-3d-impl, space-canvas as space-canvas-impl,
)
#import "blank.typ": blank-canvas as blank-canvas-impl, simple-canvas as simple-canvas-impl
#import "vector.typ": (
  draw-vector as draw-vector-impl, draw-vector-addition as draw-vector-addition-impl,
  draw-vector-components as draw-vector-components-impl, draw-vector-projection as draw-vector-projection-impl,
)
#import "combi.typ": draw-boxes as draw-boxes-impl, draw-circular as draw-circular-impl, draw-linear as draw-linear-impl

// Note: Data series functionality has moved to ../data/mod.typ

// =====================================================
// THEMED CANVAS WRAPPERS
// =====================================================

// Canvas types (theme-bound and centered)
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
