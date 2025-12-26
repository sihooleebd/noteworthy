#import "../../templates/templater.typ": *

= Quick Start Guide

Get started with Noteworthy in minutes.

== Block Syntax Overview

All blocks follow the pattern: `#blockname("Title")[content]`

#definition("Definition Block")[
  Use `#definition("Title")[...]` for definitions.
]

#theorem("Theorem Block")[
  Use `#theorem("Title")[...]` for theorems.
]

#equation("Equation Block")[
  Use `#equation("Title")[...]` for named equations:
  $ E = m c^2 $
]

#note("Note Block")[
  Use `#note("Title")[...]` for important notes.
]

#notation("Notation Block")[
  Use `#notation("Title")[...]` to explain notation.
]

#analysis("Analysis Block")[
  Use `#analysis("Title")[...]` for analysis and discussion.
]

#proof[
  Use `#proof[...]` for proofs.
]

== Proof & Solution Blocks

These blocks have special formatting:

#example("Example Block")[
  Use `#example("Title")[...]` for examples.
  #solution[
    Use `#solution[...]` for solutions. Visibility controlled by `show-solution` config.
    #note("")[
      Although not mandatory, solutions are suggested to be used inside of example blocks for clarity.
    ]
  ]
]

