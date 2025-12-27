#import "../../templates/templater.typ": *

= Block Fundamentals

The Block module provides semantic content containers for educational documents.

== What is a Block?

#definition("Block")[
  A styled container that gives semantic meaning to content. Blocks help readers identify the type of information they're reading.
]

== Block Syntax

All blocks follow the same pattern:

```typst
#blockname("Optional Title")[
  Content goes here...
]
```

Some blocks (like `proof` and `solution`) don't require a title:

```typst
#proof[
  Content without a title...
]
```

== Block Categories

Blocks are organized into three categories:

#note("Primary Blocks")[
  - `definition` — Define concepts
  - `theorem` — State theorems
  - `equation` — Named equations
]

#note("Supporting Blocks")[
  - `note` — Important information
  - `notation` — Explain symbols
  - `analysis` — Discussion and analysis
]

#note("Proofs & Examples")[
  - `proof` — Mathematical proofs
  - `example` — Worked examples
  - `solution` — Solutions (visibility controlled by config)
]

== Your First Block

#example("Creating a Definition")[
  ```typst
  #definition("Velocity")[
    The rate of change of position with respect to time:
    $ v = dif x / dif t $
  ]
  ```

  Renders as:

  #definition("Velocity")[
    The rate of change of position with respect to time:
    $ v = dif x / dif t $
  ]
]
