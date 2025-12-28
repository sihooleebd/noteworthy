#import "../../templates/templater.typ": *

= Layout & Config

The Layout module manages document structure, outlining, and global configuration.

== Document Hierarchy

#definition("hierarchy.json")[
  Located in `config/hierarchy.json`, this file defines the structure of your document, including chapters, summaries, and page titles.
]

== Configuration

#definition("constants.json")[
  Located in `config/constants.json`, this file controls global display flags:
  - `display-cover`: Show the main document cover.
  - `display-outline`: Show the table of contents.
  - `display-chap-cover`: Show individual chapter covers.
  - `display-mode`: Set the active theme (e.g., "noteworthy-light").
]

== Usage

This module is primarily automated via the build system and requires little manual interaction in `.typ` files. content/ files are automatically mapped to chapters based on their directory numbering.
