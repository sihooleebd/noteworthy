#import "../../templates/templater.typ": *

= Layout & Config

The Layout module handles table of contents and page structure. Configuration options control project-wide settings.

== Table of Contents

#definition("outline")[
  Automatically generated table of contents based on your `hierarchy.json`.
]

The outline displays:
- Chapter numbers and titles
- Page numbers and titles
- Correct page numbering

Controlled by `display-outline` in `constants.json`.

== Heading Numbering

#notation("Numbering Format")[
  Configure in `constants.json`:
  ```json
  {
    "heading-numbering": "1.1",
    "pad-chapter-id": true,
    "pad-page-id": true
  }
  ```
]

- `heading-numbering` — Format for section headings
- `pad-chapter-id` — Zero-pad chapter numbers (01, 02...)
- `pad-page-id` — Zero-pad page numbers (01.01, 01.02...)

== Solutions Visibility

#note("Show/Hide Solutions")[
  Control solution block visibility:
  ```json
  {
    "show-solution": true,
    "solutions-text": "Solutions",
    "problems-text": "Problems"
  }
  ```
]

When `show-solution` is `false`, all `#solution[...]` blocks are hidden.

== Font Configuration

```json
{
  "font": "Linux Libertine",
  "title-font": "Inter"
}
```

== Building Your Document

Use the Noteworthy TUI:
```bash
python3 noteworthy.py
```

Select *Builder* → Choose chapters → Press *Enter* to build.

The output PDF is saved to `output.pdf`.
