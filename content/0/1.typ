#import "../../templates/templater.typ": *

= Welcome to Noteworthy

Noteworthy is a powerful Typst framework for creating beautiful educational documents with rich content blocks and visualization tools.

== What is Noteworthy?

#definition("Noteworthy")[
  A modular Typst template system designed for creating professional educational materials, textbooks, and technical documentation.
]

== Key Features

#note("Modular Architecture")[
  Noteworthy is organized into *6 modules*, each handling a specific aspect of document creation:

  - *Block* — Semantic content containers (definitions, theorems, proofs)
  - *Geometry* — 2D geometric primitives (points, lines, circles)
  - *Canvas* — Rendering canvases for plots and visualizations
  - *Data* — Tables, data series, and curve interpolation
  - *Cover* — Document covers and title pages
  - *Layout* — Page layouts and table of contents
]

== How to Use This Guide

This documentation is organized by module. Each chapter covers one module:

+ *Chapter 0* — Architecture & file structure (you are here)
+ *Chapter 1* — Block module for content containers
+ *Chapter 2* — Geometry module for 2D shapes
+ *Chapter 3* — Canvas module for plotting
+ *Chapter 4* — Data module for tables and series
+ *Chapter 5* — Cover & Layout for document structure

#theorem("Getting Started")[
  Every content file starts with one import:
  ```typst
  #import "../../templates/templater.typ": *
  ```
  This single import gives you access to all modules.
]
