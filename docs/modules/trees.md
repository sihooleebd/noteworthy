# Trees Module

The `trees` module provides specific tools for visualizing hierarchical tree structures using the `tree` and `tree-node` objects.

## Import

```typst
#import "../../templates/templater.typ": *
```

## Basic Usage

### Defining a Tree
Trees are defined recursively using `tree-node`.

```typst
// Import just specific modules if needed, or everything via templater
#import "../../templates/templater.typ": tree, tree-node

#let my-tree = tree(
  tree-node("Root", children: (
    tree-node("L", children: (
      tree-node("LL"),
      tree-node("LR")
    )),
    tree-node("R")
  )),
  direction: "vertical", // "vertical" or "horizontal"
  highlight-path: ("Root", "L", "LL") // Names or auto-generated IDs
)

#draw-tree(my-tree, theme: active-theme)
```

## Configuration

### `tree` Options
-   **`root`**: The root `tree-node`.
-   **`direction`**: Layout direction. `"vertical"` (top-down) or `"horizontal"` (left-right).
-   **`highlight-items`**: List of node names to highlight.
-   **`highlight-path`**: List of node names that form a path to highlight (edges between them are also highlighted).

### `tree-node` Options
-   **`value`**: The content to display in the node circle.
-   **`children`**: Array of child nodes.
-   **`name`**: Unique identifier. If omitted, one is generated automatically, but explicit names are recommended for highlighting.
