#import "../../templates/templater.typ": *

= Combinatorics Visualizations

Visual representations for counting problems.

== Linear Permutations

Arrange items in a row:

#blank-canvas(
  linear-perm(("A", "B", "C", "D"), labels: ("1st", "2nd", "3rd", "4th")),
)

Highlight specific positions:

#blank-canvas(
  linear-perm(("1", "2", "3", "4", "5"), highlight: (0, 2, 4)),
)

== Circular Permutations

Arrange items in a circle:

#blank-canvas(
  circular-perm(("A", "B", "C", "D", "E"), radius: 1.5),
)

== Balls and Boxes

Distribute balls into boxes:

#definition("balls-boxes")[
  Visualize distribution problems:
  - Distinguishable balls: numbered, colored differently
  - Identical balls: same color
]

#example("Distinguishable Balls")[
  #blank-canvas(
    balls-boxes(5, 3, distribution: (2, 2, 1), balls-identical: false),
  )
]

#example("Identical Balls")[
  #blank-canvas(
    balls-boxes(6, 3, distribution: (3, 2, 1), balls-identical: true),
  )
]

== Subset Selection (Combinations)

Highlight a subset of elements:

#blank-canvas(
  subset-vis(("a", "b", "c", "d", "e", "f"), subset: (1, 3, 5)),
)

== Counting Trees

Visualize multiplication principle:

#blank-canvas(
  counting-tree((("R", "B"), ("S", "M", "L"))),
)

== Partition Diagrams

Ferrers/Young diagram for partitions:

#definition("partition-vis")[
  Shows a partition of n as a Ferrers diagram.
  ```typst
  partition-vis((4, 3, 2, 1))  // 4 + 3 + 2 + 1 = 10
  ```
]

#blank-canvas(
  partition-vis((4, 3, 2, 1)),
)

#blank-canvas(
  partition-vis((5, 5, 3, 1)),
)

== Pigeonhole Principle

Visualize when items must share containers:

#blank-canvas(
  pigeonhole(5, 3), // 5 pigeons, 3 holes - at least one has 2+
)
