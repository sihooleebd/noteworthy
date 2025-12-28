# DSA Module

The `dsa` module provides visualizations for common Data Structures and Algorithms.

## Import

```typst
#import "../../templates/templater.typ": *
```

## Data Structures

### Arrays
```typst
#cs-array(
  (10, 20, 30, 40), 
  highlight: (1, 2),  // Indices to highlight
  pointers: (2: "i"), // Pointers below indices
  separators: (2,),   // Visual gap after index 2
  label: "Array A"
)
```

### Stacks
```typst
#cs-stack(
  (1, 2, 3), // Bottom to top
  incoming: 4, // Item being pushed
  outgoing: none,
  limit: 5
)
```

### Queues
```typst
#cs-queue(
  (1, 2, 3), // Front to back
  incoming: 4, // Enqueueing
  outgoing: none
)
```

### Linked Lists
```typst
#cs-linked-list(
  (10, 20, 30), 
  pointers: (0: "head"),
  highlight: (1,)
)
```

## Graphs & Algorithms

### Free Graph
Visualizes arbitrary networks of nodes and edges.

**Auto-Positioning**: If node positions are not specified (or only partially specified), nodes are automatically arranged on a regular n-polygon.

```typst
// Auto-positioned triangle (no positions needed)
#free-graph(
  (
    graph-node("A"), 
    graph-node("B"),
    graph-node("C")
  ),
  (
    graph-edge("A", "B", weight: 5, directed: true),
    graph-edge("B", "C", weight: 3),
    graph-edge("C", "A", weight: 2),
  ),
  style: (label: "My Graph")
)

// Manual positioning
#free-graph(
  (
    graph-node("A", pos: (0, 0)), 
    graph-node("B", pos: (2, 0))
  ),
  (
    graph-edge("A", "B", weight: 5, directed: true),
  ),
  highlight-path: ("A", "B")
)
```

**Features**:
- Edge weights display with **pill-style labels** (centered on edge with rounded background)
- Edges drawn center-to-center; nodes render on top to keep labels clean
- Supports `curved` parameter for arc-style edges

-   **`graph-node(value, pos, ...)`**: Defines a node.
-   **`graph-edge(from, to, weight, directed, curved, ...)`**: Defines an edge.

### Adjacency Matrix
Visualizes graph connections in matrix form.
```typst
#adjacency-matrix(
  ((0, 1), (1, 0)), 
  labels: ("A", "B"), 
  highlight-cells: ((0, 1),)
)
```

### Grid World
Visualizes 2D grid algorithms (pathfinding, mazes).
```typst
#grid-world(
  rows: 5, 
  cols: 5, 
  walls: ((1,1), (1,2)), 
  path: ((0,0), (0,1), (0,2)),
  start: (0,0),
  target: (4,4)
)
```
