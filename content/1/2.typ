#import "../../templates/templater.typ": *

= All Block Types

A complete reference of every block type in the Block module.

== Primary Blocks

#definition("Definition Block")[
  Use `#definition("Title")[...]` to define concepts.
]

#theorem("Theorem Block")[
  Use `#theorem("Title")[...]` to state theorems.
]

#equation("Equation Block")[
  Use `#equation("Title")[...]` for named equations:
  $ E = m c^2 $
]

== Supporting Blocks

#note("Note Block")[
  Use `#note("Title")[...]` for important notes and tips.
]

#notation("Notation Block")[
  Use `#notation("Title")[...]` to explain mathematical notation and symbols.
]

#analysis("Analysis Block")[
  Use `#analysis("Title")[...]` for analysis, discussion, and elaboration.
]

== Proofs and Examples

#proof("Simple Proof")[
  Use `#proof[...]` or `#proof("Title")[...]` for mathematical proofs.

  The proof block has a special QED marker at the end.
]

#example("Example with Solution")[
  Use `#example("Title")[...]` for worked examples.

  Solutions can be nested inside examples:

  #solution[
    Use `#solution[...]` for solutions.

    Visibility is controlled by `show-solution` in `config/constants.json`.
  ]
]

== Nesting Blocks

Blocks can be nested for complex content:

#theorem("Fundamental Theorem")[
  A theorem statement here.

  #proof[
    The proof of the theorem.
  ]

  #example("Application")[
    An example applying the theorem.

    #solution[
      The worked solution.
    ]
  ]
]

== Styling

Block colors are determined by your active theme. See `config/schemes/` to customize.
