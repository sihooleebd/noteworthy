#import "../../templates/templater.typ": *


= Algorithms

The Algo module provides visualizations for graph algorithms, pathfinding, and matrix operations.

== Graphs

#definition("free-graph")[
  Visualizes a node-link diagram with support for weighted, directed, and curved edges.

  ```typst
  free-graph(
    nodes, edges,
    highlight-path: ("A", "B"),
    highlight-nodes: ("A",),
    style: (label: "My Graph")
  )
  ```
  *Parameters:*
  - `nodes`: List of `graph-node` objects.
  - `edges`: List of `graph-edge` objects.
  - `highlight-path`: List of node names (in order) to highlight edges between.
  - `highlight-nodes`: List of node names to highlight.
]

#canvas.blank-canvas(length: 10cm, height: 6cm, {
  // No positions specified - nodes will be auto-positioned on a triangle
  let nodes = (
    dsa.graph-node("A"),
    dsa.graph-node("B"),
    dsa.graph-node("C"),
  )
  let edges = (
    dsa.graph-edge("A", "B", weight: 5, directed: true),
    dsa.graph-edge("B", "C", weight: 3, directed: true),
    dsa.graph-edge("C", "A", weight: 2, directed: true),
  )
  dsa.free-graph(nodes, edges, style: (label: "Simple Graph"))
})

== Grid World

#definition("grid-world")[
  Visualizes a 2D grid for pathfinding algorithms (A\*, BFS, etc.).

  ```typst
  grid-world(
    rows, cols,
    walls: ((1,1),),
    start: (0,0),
    target: (4,4),
    path: ((0,0), (0,1)...)
  )
  ```
  *Parameters:*
  - `rows`, `cols`: Grid dimensions.
  - `walls`: List of `(c, r)` coordinates for obstacles.
  - `start`, `target`: Coordinates for start (green) and target (red).
  - `path`: List of coordinates to highlight as the path.
]

#canvas.blank-canvas(length: 6cm, height: 6cm, dsa.grid-world(
  5,
  5,
  start: (0, 0),
  target: (4, 4),
  walls: ((2, 2),),
  path: ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (4, 1), (4, 2), (4, 3), (4, 4)),
  label: "Pathfinding",
))

== Adjacency Matrix

#definition("adjacency-matrix")[
  Visualizes a matrix (2D array) representing graph weights or connections.

  ```typst
  adjacency-matrix(
    matrix,
    labels: ("A", "B"...),
    highlight-cells: ((0,1),)
  )
  ```
  *Parameters:*
  - `matrix`: 2D list of values. Use `none` for infinity/no connection.
  - `labels`: Row/Column headers.
  - `highlight-cells`: List of `(row, col)` tuples to highlight.
]

#canvas.blank-canvas(length: 6cm, height: 6cm, dsa.adjacency-matrix(
  ((0, 5), (none, 0)),
  labels: ("A", "B"),
  label: "Weights",
))
