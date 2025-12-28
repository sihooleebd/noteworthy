#import "../../templates/templater.typ": *

= Trees and Hierarchies

Visualizing hierarchical data structures.


#definition("Structuring Trees")[
  Use `tree-node(value, children: (...))` to define the hierarchy recursively.
  ```typst
  let root = tree-node("Root", children: (
    tree-node("Child 1"),
    tree-node("Child 2"),
  ))
  ```
]

== Vertical Trees

Standard top-down tree visualization, commonly used for binary trees or organizational charts.

#definition("Vertical Tree")[
  Set `direction: "vertical"` to arrange nodes from top to bottom.
  ```typst
  tree(root, direction: "vertical")
  ```
]

#let my-tree-node = tree-node("Root", children: (
  tree-node("A", children: (
    tree-node("A1"),
    tree-node("A2"),
  )),
  tree-node("B", children: (
    tree-node("B1"),
  )),
  tree-node("C"),
))

#blank-canvas(
  tree(
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
  tree(root, direction: "horizontal")
  ```
]

#let fs-tree = tree-node("/", children: (
  tree-node("bin", children: (
    tree-node("ls"),
    tree-node("pwd"),
  )),
  tree-node("usr", children: (
    tree-node("local"),
    tree-node("lib"),
  )),
  tree-node("home"),
))

#blank-canvas(
  tree(
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
  tree(
    root,
    highlight-path: ("Root", "Child", "Grandchild")
  )
  ```
]

#let path-tree = tree-node("Start", children: (
  tree-node("Step 1", children: (
    tree-node("Option A"),
    tree-node("Option B", children: (
      tree-node("Goal"),
    )),
  )),
  tree-node("Step 2"),
))

#blank-canvas(
  tree(
    path-tree,
    direction: "vertical",
    highlight-path: ("Start", "Step 1", "Option B", "Goal"),
  ),
)
