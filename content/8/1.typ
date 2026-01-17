#import "../../templates/templater.typ": *

= Combinatorics Visualizations

Visual representations for counting problems.

== Linear Permutations

Arrange items in a row:

#canvas.blank-canvas(
  combi.linear-perm(combi.permutation(("A", "B", "C", "D"), labels: ("1st", "2nd", "3rd", "4th"))),
)

Highlight specific positions:

#canvas.blank-canvas(
  combi.linear-perm(combi.permutation(("1", "2", "3", "4", "5")), highlight: (0, 2, 4)),
)

== Circular Permutations

Arrange items in a circle:

#canvas.blank-canvas(
  combi.circular-perm(combi.permutation(("A", "B", "C", "D", "E")), radius: 1.5),
)

== Balls and Boxes

Distribute balls into boxes:

#definition("balls-boxes")[
  Visualize distribution problems:
  - Distinguishable balls: numbered, colored differently
  - Identical balls: same color
]

#example("Distinguishable Balls")[
  #canvas.blank-canvas(
    combi.balls-boxes(5, 3, distribution: (2, 2, 1), balls-identical: false),
  )
]

#example("Identical Balls")[
  #canvas.blank-canvas(
    combi.balls-boxes(3, 3, distribution: (3, 2, 1), balls-identical: true),
  )
]

== Subset Selection (Combinations)

Highlight a subset of elements:

#canvas.blank-canvas(
  combi.subset-vis(("a", "b", "c", "d", "e", "f"), subset: (1, 3, 5)),
)

== Counting Trees

Visualize multiplication principle:

#canvas.blank-canvas(
  combi.counting-tree((("R", "B"), ("S", "M", "L"), ("L", "R"))),
)

== Partition Diagrams

Ferrers/Young diagram for partitions:

#definition("partition-vis")[
  Shows a partition of n as a Ferrers diagram.
  ```typst
  partition-vis((4, 3, 2, 1))  // 4 + 3 + 2 + 1 = 10
  ```
]

#canvas.blank-canvas(
  combi.partition-vis((4, 3, 2, 1)),
)

#canvas.blank-canvas(
  combi.partition-vis((5, 5, 3, 1)),
)

== Pigeonhole Principle

Visualize when items must share containers:

#canvas.blank-canvas(
  combi.pigeonhole(5, 3), // 5 pigeons, 3 holes - at least one has 2+
)
