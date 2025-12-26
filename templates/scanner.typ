// Content Scanner for Typst
// Provides content discovery from sys.inputs or fallback to hierarchy-based defaults

// Import hierarchy for fallback calculation
#import "setup.typ": hierarchy

// Try to load content info from sys.inputs, fall back to hierarchy-based defaults
#let load-content-info() = {
  // First try sys.inputs (from Python build)
  let chapter-folders-str = sys.inputs.at("chapter-folders", default: none)
  let page-folders-str = sys.inputs.at("page-folders", default: none)

  if chapter-folders-str != none and page-folders-str != none {
    // Use data from Python build
    (
      chapters: json(bytes(chapter-folders-str)),
      pages: json(bytes(page-folders-str)),
    )
  } else {
    // Fallback: generate 1-indexed page arrays based on hierarchy structure
    // Pages are 1-indexed: ["1", "2", "3"...] not ["0", "1", "2"...]
    let fallback-chapters = range(hierarchy.len()).map(i => str(i))
    let fallback-pages = {
      let result = (:)
      for (i, ch) in hierarchy.enumerate() {
        // Use 0-based range to match file array indexing behavior
        result.insert(str(i), range(ch.pages.len()).map(j => str(j)))
      }
      result
    }

    (
      chapters: fallback-chapters,
      pages: fallback-pages,
    )
  }
}

// Convenience functions
#let get-chapter-folders() = {
  load-content-info().chapters
}

#let get-page-files(chapter-index) = {
  load-content-info().pages.at(str(chapter-index), default: ())
}
