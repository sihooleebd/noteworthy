---
name: noteworthy
description: Write and edit Noteworthy documents — a Typst framework for textbooks, with blocks (definition/theorem/example/solution), 2D and 3D canvases, geometry, plotting, and live Yjs collaboration. Use when editing .typ files in a Noteworthy project, drawing a figure with shape/graph/canvas, adding a block or cross-reference, changing templates/module, or deploying to a running Noteworthy server. Covers the one rule that is not guessable: a live document is a CRDT room and the file is only its export.
---

# Noteworthy

A Typst framework for educational documents. `templates/templater.typ` re-exports
everything; a content file imports that one path and nothing else.

```
config/     hierarchy.json, metadata.json, constants.json, schemes/
content/    <chapter>/<page>.typ          the document itself
templates/  templater.typ, core/, module/
```

Blocks, covers and layouts come in unqualified; everything else is a namespace:
`canvas`, `shape`, `graph`, `data`, `combi`, `dsa`, `timeline`, `trees`.

```typst
#import "../../templates/templater.typ": *
```

## The room is the document; the file is its export

A Noteworthy server holds each open file as a Yjs CRDT **room**. While a room is
live it is authoritative, and it rewrites the file within a debounce of every
edit.

**So writing the file behind a live room's back does not edit the document.** The
room's next save puts the old text back over what was written, and nobody
connected ever sees the change. This is the single most expensive mistake to make
here — it looks like it worked, and reverts a few seconds later.

Edit through the room instead. When the `noteworthy` MCP server is connected:

| tool | for |
|---|---|
| `list_documents` | what exists, and which files someone has open right now |
| `read_document` | the live text when a room holds it, the file otherwise |
| `edit_document` | replace old→new; a delta through the room, so an open editor keeps its cursor, scroll and undo |
| `append_document` | add at the end, same way |
| `render_document` | render the book, a chapter or a page and hand back the pages as images (`format: "pdf"` also leaves the PDF on the server) |
| `check_document` | compile the book and return typst's diagnostics |

`edit_document` refuses an `old_string` that appears zero times, or more than
once without `replace_all` — same rule whether it goes through a room or to a
file nobody has open.

Without the MCP server, editing files directly is only safe when no server is
running against that project.

## Deploying templates and modules

`templates/` is not a document, so it is deployed rather than edited through a
room. `templates/module` is a git submodule (`noteworthy-modules`).

```bash
# commit in the submodule, then bump the pin in the parent repo
cd templates/module && git commit && git push
cd ../..        && git commit -am "Bump modules: ..." && git push

# --delay-updates: every file is staged and renamed at the end, so the project
# never sits half-updated.  Without it a watching tinymist compiles a tree where
# one file has landed and another has not, and reports unresolved imports.
rsync -a --delay-updates --exclude='.git' templates/module/ host:project/templates/module/

# reconcile ONLY the paths deployed.  An empty body means *every* live room,
# which reloads documents nobody asked you to touch.
curl -X POST http://host:8010/api/rooms/reload -H 'Content-Type: application/json' \
  -d '{"paths": ["templates/module/canvas/space.typ"]}'
```

## Rendering a page to look at it

`render_document` is the short way, and it takes names: `"8/2"`,
`"content/8/2.typ"`, `"8"` for a chapter, nothing for the book. Without the MCP
server, compile through the parser yourself -- and either way **look at the
image** before saying a figure works.

```bash
typst compile templates/core/parser.typ out-{n}.png --root . --ppi 110 \
  --input 'chapter-folders=["8", "9"]' \
  --input 'page-folders={"8": ["1", "2"], "9": ["1"]}' \
  --input target=0/1        # index into chapter-folders / page-folders, not names
```

A single-page compile has no cross-page label map, so `@label` pointing at
another page renders as a red `?label`. That is expected; it resolves in a full
build.

## Blocks

`definition`, `theorem`, `example`, `note`, `notation`, `analysis`, `equation`,
`solution`, `proof`. Signature: `#block-kind(title, number, label: "name")[body]`.

```typst
#definition("Truncated Cone", label: "tcone")[ ... ]     // auto-numbered
#note("Why", auto, label: "why")[ ... ]                  // auto is the number slot
@tcone                                                    // renders "Definition 8.2.1"
```

Blocks nest, and a `solution` counts within the block containing it. A reference
is drawn in that block kind's scheme colour.

## Figures

Canvases take objects as positional arguments; arrays of objects are fine.

```typst
canvas.cartesian-canvas(size: (6, 4), x-domain: (0, 6), y-domain: (-3, 3), ..objects)
canvas.polar-canvas / trig-canvas / graph-canvas / blank-canvas   // blank: no axes
canvas.space-canvas(x-domain:, y-domain:, z-domain:, size:, elevation:, azimuth:,
                    projection: "orthographic" | "perspective", axis-dir: (y: -1))
```

| module | what is in it | detail |
|---|---|---|
| unqualified | blocks, covers, layout, `@ref` | `reference/blocks.md` |
| `shape` | points, lines, circles, arcs, polygons, angles, braces, text, constructions, intersections | `reference/geometry.md` |
| `graph` | functions, parametric and polar curves, surfaces, vectors, tangents, Riemann sums | `reference/plotting.md` |
| `data` | series, CSV, tables, smooth curves | `reference/plotting.md` |
| `canvas` | the six canvases and the 3D camera | `reference/plotting.md` |
| `combi` `trees` `dsa` `timeline` | permutations, trees, arrays/stacks/graphs/grids, timelines | `reference/structures.md` |

Read the reference file for the module you are using: the signatures there are
taken from `templates/module`, which is ahead of the feature document in
`content/`.

### The 2D/3D rule

Every point-built shape takes `(x, y)` **or** `(x, y, z)`. In a space canvas a
two-component point lies on the ground plane and a three-component one is in
space — so a parametric function is 3D exactly when it returns three numbers.

```typst
shape.circle((0, 0, 1.5), radius: 1)                      // a ring at height 1.5
graph.parametric(t => (calc.cos(t), calc.sin(t), t / 2))  // a helix
graph.parametric(x => (x, 0, f(x)), domain: (a, b))       // a profile in the xz-plane
```

A circle is always flat on the ground plane. A ring perpendicular to an axis is a
`polyline` or a parametric curve, not a `circle`.

### Styling

`style: (stroke: (dash: "dashed"))` keeps the theme's paint and thickness —
naming one part of a stroke keeps the rest. A bare colour (`stroke: red`)
replaces outright.

A `surface` with a translucent colour is not stroked: stroking a facet in its own
translucent fill doubles the alpha along every shared edge and the mesh shows up
as a grid of lines. Opaque surfaces are stroked, to close antialiasing seams.

`brace` takes `angle:` — a direction on the page (0deg right, 90deg up) — and
goes to whichever of its two sides points that way, measured after projection.
Through a camera that is the only way to say which side you meant.

## Checks worth making

- Render and look at it. Overlapping labels and a figure that silently drew
  nothing both survive a clean compile.
- An unknown named argument to a canvas is silently ignored, not an error
  (`space-canvas` panics on them; the flat ones do not).
- `check_document`, or a compile, before leaving an edit behind.
