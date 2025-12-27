// =====================================================
// TEMPLATER - Main entry point for all templates
// =====================================================
// This file re-exports everything from each module's mod.typ.
// Each mod.typ handles its own theming internally.

#import "core/setup.typ": *
#import "core/scheme.typ": *

// =====================================================
// MODULE IMPORTS
// =====================================================

// Shape module (points, lines, circles, polygons, angles)
#import "./module/shape/mod.typ": *

// Graph module (vectors, functions, calculus)
#import "./module/graph/mod.typ": *

// Data module (data series, tables, curves)
#import "./module/data/mod.typ": *

// Canvas module (cartesian, polar, space, blank canvases + vector/combi helpers)
#import "./module/canvas/mod.typ": *

// Block module (definition, theorem, example, solution, etc.)
#import "./module/block/mod.typ": *

// Cover module (cover, chapter-cover, preface, project)
#import "./module/cover/mod.typ": *

// Layout module (outline)
#import "./module/layout/mod.typ": *

// Combinatorics module (permutations, combinations, balls-and-boxes)
#import "./module/combi/mod.typ": *
