#import "../config.typ": *
#import "./default-schemes.typ": *

#import "./layouts/blocks.typ"
#import "./plots/geoplot.typ"
#import "./plots/combiplot.typ"
#import "./plots/vectorplot.typ"
#import "./plots/grapher.typ"
#import "./plots/plots.typ"
#import "./plots/spaceplot.typ"
#import "./plots/tableplot.typ"

#import "@preview/cetz:0.4.2"
#import "@preview/cetz:0.4.2": *
#import "@preview/cetz-plot:0.1.3": plot
#let add-graph(..args) = {
  let kwargs = args.named()
  if "samples" not in kwargs {
    kwargs.insert("samples", render-sample-count)
  }
  plot.add(..args.pos(), ..kwargs)
}

// Re-export cetz module for content files
#import "@preview/cetz:0.4.2" as cetz-mod
#let cetz = cetz-mod

#import "./layouts/blocks.typ": *
#import "./covers/chapter-cover.typ": *
#import "./covers/main-cover.typ": *
#import "./covers/preface.typ": *
#import "./layouts/outline.typ": *
#import "./covers/page-title.typ": *


#let active-theme = active-theme
#let project = project.with(theme: active-theme)
#let cover = cover.with(theme: active-theme)
#let preface = preface.with(theme: active-theme, content: preface-content, authors: authors)
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


#let rect-plot(..args) = { align(center)[#plots.rect-plot(..args, theme: active-theme)] }
#let polar-plot(..args) = { align(center)[#plots.polar-plot(..args, theme: active-theme)] }
#let combi-plot(..args) = { align(center)[#plots.combi-plot(..args, theme: active-theme)] }
#let blank-plot(..args) = { align(center)[#plots.blank-plot(..args, theme: active-theme)] }
#let space-plot(..args) = { align(center)[#spaceplot.space-plot(..args, theme: active-theme)] }


#let point = geoplot.point.with(theme: active-theme)
#let add-polar = geoplot.add-polar
#let add-angle = geoplot.add-angle.with(theme: active-theme)
#let add-right-angle = geoplot.add-right-angle.with(theme: active-theme)
#let add-xy-axes = geoplot.add-xy-axes
#let add-polygon = geoplot.add-polygon.with(theme: active-theme)


#let draw-boxes = combiplot.draw-boxes.with(theme: active-theme)
#let draw-linear = combiplot.draw-linear.with(theme: active-theme)
#let draw-circular = combiplot.draw-circular.with(theme: active-theme)



#let draw-vec = vectorplot.draw-vec.with(theme: active-theme)
#let draw-vec-comps = vectorplot.draw-vec-comps.with(theme: active-theme)
#let draw-vec-sum = vectorplot.draw-vec-sum.with(theme: active-theme)
#let draw-vec-proj = vectorplot.draw-vec-proj.with(theme: active-theme)

#let plot-function = grapher.plot-function.with(theme: active-theme)

// Table plotting functions
#let table-plot = tableplot.table-plot.with(theme: active-theme)
#let compact-table = tableplot.compact-table.with(theme: active-theme)
#let value-table = tableplot.value-table.with(theme: active-theme)
#let grid-table = tableplot.grid-table.with(theme: active-theme)
