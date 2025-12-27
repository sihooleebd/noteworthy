#import "../../templates/templater.typ": *

= Module Overview

A quick reference for all seven Noteworthy modules.

== The Seven Modules

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,

  definition("block")[
    Semantic content containers.

    *Key exports:*
    - `definition`, `theorem`, `proof`
    - `example`, `solution`
    - `note`, `notation`, `equation`
  ],

  definition("shape")[
    2D geometric primitives.

    *Key exports:*
    - `point`, `line`, `circle`
    - `polygon`, `angle`
    - `midpoint`, `intersect-ll`
  ],

  definition("graph")[
    Functions and vectors.

    *Key exports:*
    - `graph`, `func`, `parametric`
    - `vec`, `vec-add`, `vec-project`
    - `polar-func`
  ],

  definition("canvas")[
    Rendering canvases.

    *Key exports:*
    - `cartesian-canvas`
    - `polar-canvas`, `trig-canvas`
    - `space-canvas`, `graph-canvas`
  ],

  definition("data")[
    Data visualization and tables.

    *Key exports:*
    - `table-plot`, `value-table`
    - `data-series`, `csv-series`
    - `curve-through`, `smooth-curve`
  ],

  definition("cover")[
    Document covers and title pages.

    *Key exports:*
    - `cover`, `chapter-cover`
    - `preface`, `project`
  ],

  definition("layout")[
    Page layouts and table of contents.

    *Key exports:*
    - `outline`
  ],
)

== How Modules Work Together

#note("Typical Workflow")[
  1. Use *block* module to structure your content
  2. Use *shape* module to create geometric objects
  3. Use *graph* module for functions and vectors
  4. Use *canvas* module to render shapes and graphs
  5. Use *data* module for tables and data plots
  6. *Cover* and *Layout* modules handle document structure
]
