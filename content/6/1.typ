#import "../../templates/templater.typ": *

= Cover Templates

The Cover module provides document covers and title pages.

== Main Cover

#definition("cover")[
  The main document cover, shown at the beginning. Configured automatically via `config/metadata.json`.
]

#note("Configuration")[
  Cover content is set in `config/metadata.json`:
  ```json
  {
    "title": "Your Document Title",
    "subtitle": "Optional Subtitle",
    "authors": ["Author 1", "Author 2"],
    "affiliation": "Your Institution"
  }
  ```
]

== Chapter Cover

#definition("chapter-cover")[
  Shown at the start of each chapter. Configured via `hierarchy.json`:
  ```json
  {
    "title": "Chapter Title",
    "summary": "Brief chapter description."
  }
  ```
]

Controlled by `display-chap-cover` in `constants.json`.

== Preface

#definition("preface")[
  Introduction page shown after the cover. Content is in `config/preface.typ`.
]

Edit `config/preface.typ` to add your preface content.

== Project (Page Title)

#definition("project")[
  Individual page headers. Each page displays its title from `hierarchy.json`.
]

== Display Controls

In `config/constants.json`:

#notation("Display Flags")[
  - `display-cover` — Show main cover
  - `display-outline` — Show table of contents
  - `display-chap-cover` — Show chapter covers
  - `display-mode` — Theme name (e.g., "noteworthy-dark")
]
