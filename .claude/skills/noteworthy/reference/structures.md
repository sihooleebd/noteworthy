# combi, trees, dsa, timeline

Visualisations that take a description and lay themselves out. All take
`origin: (0, 0)` and `style: auto`, and go in a `blank-canvas` unless the
figure wants axes.

## combi — counting

```typst
combi.permutation(names, labels: none)              // the object the others take
combi.linear-perm(perm, highlight: ())
combi.circular-perm(perm, radius: 1.5, show-arrows: false)
combi.balls-boxes(n-balls, n-boxes, distribution: none,
                  balls-identical: false, boxes-identical: false,
                  ball-labels: auto, box-labels: auto)
combi.subset-vis(elements, subset: (), set-label:, subset-label:)
combi.counting-tree(levels)                         // levels: a list of branch counts
combi.partition-vis(partition)                      // e.g. (3, 2, 2, 1)
combi.pigeonhole(n-pigeons, n-holes)
```

## trees

```typst
combi.counting-tree  // for counting arguments
trees.tree-node(value, children: (), name: auto, style: (:))
trees.tree(root, direction: "vertical" | "horizontal",
           highlight-items: (), highlight-path: ())
```

`tree-node` nests to build the tree; `tree` lays it out. `highlight-path`
takes node names, so a traversal can be drawn on the same tree.

## dsa — data structures

```typst
dsa.cs-array(items, highlight: (), pointers: (i: "lo"), separators: (), show-index: true)
dsa.cs-stack(items, limit:, incoming:, outgoing:, label: "Stack")
dsa.cs-queue(items, limit:, incoming:, outgoing:, label: "Queue")
dsa.cs-linked-list(items, highlight: (), pointers: (:))
dsa.graph-node(value, pos: (x, y), name: auto)
dsa.graph-edge(from, to, weight: none, directed: false, curved: 0, label-pos: 0.5)
dsa.free-graph(nodes, edges, highlight-path: (), highlight-nodes: (), highlight-edges: ())
dsa.grid-world(rows, cols, walls: (), path: (), visited: (), start:, target:)
dsa.adjacency-matrix(matrix, labels: (), highlight-cells: ())
```

`incoming`/`outgoing` draw the element entering or leaving, which is what makes
a stack diagram show an operation rather than a state.

## timeline

```typst
timeline.event(date, title, description: none, highlight: false)
timeline.timeline(events, direction: "vertical" | "horizontal")
timeline.timeline-figure(events, direction:, width: auto)
```

## Covers and layout

Unqualified, from `core/`: the chapter cover, main cover, page title and
preface templates, and the outline. These are driven by `config/metadata.json`
and `config/hierarchy.json` rather than called by hand in a page.
