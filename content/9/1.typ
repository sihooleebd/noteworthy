#import "../../templates/templater.typ": *

= Trees and Hierarchies

Visualizing hierarchical data structures.


#definition("Structuring Trees")[
  Use `trees.tree-node(value, children: (...))` to define the hierarchy recursively.
  ```typst
  let root = trees.tree-node("Root", children: (
    trees.tree-node("Child 1"),
    trees.tree-node("Child 2"),
  ))
  ```
]

== Vertical Trees

Standard top-down tree visualization, commonly used for binary trees or organizational charts.

#definition("Vertical Tree")[
  Set `direction: "vertical"` to arrange nodes from top to bottom.
  ```typst
  trees.tree(root, direction: "vertical")
  ```
]

#let my-tree-node = trees.tree-node("Root", children: (
  trees.tree-node("A", children: (
    trees.tree-node("A1"),
    trees.tree-node("A2"),
  )),
  trees.tree-node("B", children: (
    trees.tree-node("B1"),
  )),
  trees.tree-node("C"),
))

#canvas.blank-canvas(
  trees.tree(
    my-tree-node,
    direction: "vertical",
    highlight-items: ("A",),
    highlight-path: ("Root", "B", "B1"),
  ),
)

== Horizontal Trees

Left-to-right tree visualization, useful for file systems or taxonomies.

#definition("Horizontal Tree")[
  Set `direction: "horizontal"` to arrange nodes from left to right.
  ```typst
  trees.tree(root, direction: "horizontal")
  ```
]

#let fs-tree = trees.tree-node("/", children: (
  trees.tree-node("bin", children: (
    trees.tree-node("ls"),
    trees.tree-node("pwd"),
  )),
  trees.tree-node("usr", children: (
    trees.tree-node("local"),
    trees.tree-node("lib"),
  )),
  trees.tree-node("home"),
))

#canvas.blank-canvas(
  trees.tree(
    fs-tree,
    direction: "horizontal",
    highlight-path: ("/", "usr", "local"),
  ),
)

== Path Highlighting

You can highlight specific paths to emphasize a traversal or a lineage.

#definition("Path Highlighting")[
  Provide a list of node names to `highlight-path`. The visualizer will highlight the nodes and the edges connecting them.
  ```typst
  trees.tree(
    root,
    highlight-path: ("Root", "Child", "Grandchild")
  )
  ```
]

#let path-tree = trees.tree-node("Start", children: (
  trees.tree-node("Step 1", children: (
    trees.tree-node("Option A"),
    trees.tree-node("Option B", children: (
      trees.tree-node("Goal"),
    )),
  )),
  trees.tree-node("Step 2"),
))

#canvas.blank-canvas(
  trees.tree(
    path-tree,
    direction: "vertical",
    highlight-path: ("Start", "Step 1", "Option B", "Goal"),
  ),
)
