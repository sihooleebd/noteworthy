# Layout & Covers Module

The `layout` and `cover` modules control the high-level structure and presentation of your document, including outlines, title pages, and chapter covers.

## Import

```typst
#import "../../templates/templater.typ": *
```

## Document Structure (Covers)

### `project`
The main document entry point, typically used in `templates/parser.typ` to set up the document.
```typst
#project(
  [Content],
  config: (..), 
  pages: (..), 
  chapter-ids: (..)
)
```

### `cover`
Generates the main book/document cover.
```typst
#cover(
  title: "Book Title",
  subtitle: "Subtitle",
  authors: ("Author A", "Author B"),
  affiliation: "Institution",
  year: "2024"
)
```

### `chapter-cover`
Generates a stylized cover page for a new chapter.
```typst
#chapter-cover(
  id: "1",
  title: "Introduction",
  description: "A brief overview"
)
```

### `preface`
Creates a preface section at the start of the document.

## Layouts

### `outline`
Generates the Table of Contents (ToC).
```typst
#outline(
  title: "Contents",
  depth: 2
)
```
-   **Note**: The outline automatically picks up the styling defined in the templates.
