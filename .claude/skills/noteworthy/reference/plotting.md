# Canvases, plotting and data

## Canvases

```typst
canvas.cartesian-canvas(size: (6, 4), x-domain: (0, 6), y-domain: (-3, 3),
                        show-grid: false, axis-style: "school-book", ..objects)
canvas.graph-canvas(..)     // cartesian with school-book axes
canvas.trig-canvas(x-domain: (-2*calc.pi, 2*calc.pi), pi-divisor: 2, ..)
canvas.polar-canvas(radius: 3, show-angles: true, ..)
canvas.blank-canvas(size: auto, ..)          // no axes, no grid
canvas.space-canvas(x-domain:, y-domain:, z-domain:, size:, step:,
                    elevation: 30deg, azimuth: 30deg,
                    projection: "orthographic" | "perspective", distance: 12,
                    axis-dir: (y: -1), show-axes:, show-grid:, show-ticks:,
                    length: 1cm, ..objects)
```

Objects are positional; arrays of objects are walked, so `..intersect-lc(..)`
and the vector helpers drop in directly. Bare cetz elements pass through too
and land in **data coordinates**.

An unknown named argument is silently ignored by the flat canvases (it falls
into the `..objects` sink). `space-canvas` panics on one instead. So a
misspelled option is not an error — check the picture, not the compile.

### The camera

`azimuth` turns around the z-axis, `elevation` lifts above the ground plane.
Flipping the azimuth's sign does **not** turn one axis round: it mirrors the
whole picture, x included. To point one axis the other way and leave everything
else alone, use `axis-dir: (y: -1)`.

`projection: "perspective"` needs `distance`; cetz's own transform stack cannot
do perspective (it drops the fourth matrix row), so the camera here is ours.

## Functions

```typst
graph.graph(f, domain: (-5, 5), samples: 200, adaptive: true, hole: (), label:, style:)
graph.parametric(t => (x, y), domain: (0, 2*calc.pi), samples: 200)
graph.parametric(t => (x, y, z), ..)          // three components -> a space curve
graph.polar-func(theta => r, ..)
graph.lagrangian-interpolation(..points)       // the polynomial through them
graph.surface(f, u-domain:, v-domain:, u-steps: 24, v-steps: 8,
              color:, shade: true, light: (0.4, -0.6, 0.7), stroke: none)
```

`adaptive` resamples around singularities and steep turns. `hole` and
`filled-hole` mark removable discontinuities.

`surface` is a parametric surface `(u, v) => (x, y, z)`, painted back to front
with flat Lambert shading. A **translucent** colour is left unstroked on
purpose: stroking each facet in its own translucent fill doubles the alpha
along shared edges and the mesh appears as a grid of lines.

## Calculus helpers

```typst
graph.tangent(f, x, length: 2)      graph.normal(f, x, length: 2)
graph.derivative-at(f, x)
graph.riemann-sum(f, domain, n, method: "left" | "right" | "midpoint" | "trapezoid")
```

## Vectors

```typst
graph.vec((3, 4), label: $v$)        graph.vector(x, y, z: none, origin:)
graph.vector-3d(x, y, z)            graph.vec-components(v, helplines: true)
graph.vec-add(v1, v2)   vec-sub   vec-scale   vec-neg
graph.vec-project(v1, onto: v2)     graph.vec-dot / -cross / -magnitude / -normalize
graph.vec-angle-between(v1, v2)     graph.vec-parallel(v1, v2)
```

`vec-add`, `vec-components` and `vec-project` return arrays including their
help lines. Vectors in one canvas are labelled together, so labels avoid each
other rather than each solving its own placement.

## Data

```typst
data.data-series(points, plot-type: "scatter" | "line" | "both", label:, style:)
data.csv-series(csv-text, has-header: true, x-col: 0, y-col: 1, ..)
data.polar-data-series(points, ..)
data.curve-through(..points)        // Catmull-Rom through the points
data.smooth-curve(..points)
data.table-plot(headers: (..), data: (..))   data.compact-table(..)
data.value-table(variable: $x$, func: $f(x)$, values: (..), results: (..))
data.grid-table(data: (..), show-indices: false)
```

A `data-series` point may carry three components, in which case a space canvas
plots it where it belongs.

## Styling

`style: (stroke: ..)` merges one level deep: naming `dash` alone keeps the
theme's paint and thickness. A bare colour (`stroke: red`) or a stroke value
(`2pt + red`) replaces outright.

Theme colours: `active-theme.text-main`, `.text-accent`, `.text-muted`,
`.plot.stroke`, `.plot.highlight`, `.plot.grid`, `.page-fill`, and
`.blocks.<kind>.{fill,stroke,title}`. Prefer these to literal colours — a
scheme change should not need the figure rewritten. Note that a scheme may give
two roles the same colour (aether's `plot.highlight` equals `text-accent`), so
distinguish by density or shape when it matters.
