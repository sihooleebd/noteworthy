// =====================
// CONFIGURATION LOADING
// =====================

// Load configuration from JSON
#let config = json("config/config.json")

// Export configuration variables
#let title = config.title
#let subtitle = config.subtitle
#let authors = config.authors
#let affiliation = config.affiliation
#let logo = config.logo
#let show-solution = config.show-solution
#let solutions-text = config.solutions-text
#let problems-text = config.problems-text
#let chapter-name = config.chapter-name
#let subchap-name = config.subchap-name
#let font = config.font
#let title-font = config.title-font
#let display-cover = config.display-cover
#let display-outline = config.display-outline
#let display-chap-cover = config.display-chap-cover
#let box-margin = eval(config.box-margin)
#let box-inset = eval(config.box-inset)
#let display-mode = config.display-mode
#let pad-chapter-id = config.pad-chapter-id
#let pad-page-id = config.pad-page-id
#let heading-numbering = config.heading-numbering
#let hierarchy = json("config/hierarchy.json")

// Load schemes
#import "./default-schemes.typ": *

#import "./default-schemes.typ": schemes
#let colorschemes = schemes

#let active-theme = colorschemes.at(lower(display-mode), default: schemes.at("noteworthy-dark"))

// Import snippets
#import "config/snippets.typ": *

// =====================
// HELPER FUNCTIONS
// =====================

// Helper: Convert any ID (int or string) to string
#let to-str(id) = if type(id) == int { str(id) } else { id }

// Helper: Zero-pad a number string to a given width
#let zero-pad(s, width) = {
  let s = to-str(s)
  let padding = width - s.len()
  if padding > 0 { "0" * padding + s } else { s }
}

// Helper: Calculate required width for a count (1-9 -> 2, 10-99 -> 2, 100-999 -> 3)
#let calc-width(count) = {
  if count >= 100 { 3 } else { 2 } // Always at least 2 digits for cleaner look
}

// Helper: Format chapter ID for display with dynamic padding
#let format-chapter-id(id, total-chapters) = {
  if not pad-chapter-id { return to-str(id) }
  let width = calc-width(total-chapters)
  zero-pad(to-str(id), width)
}

// Helper: Format page ID for display with dynamic padding
#let format-page-id(id, total-pages-in-chapter, total-chapters) = {
  let s = to-str(id)
  if not pad-page-id { return s }

  let ch-width = calc-width(total-chapters)
  let pg-width = calc-width(total-pages-in-chapter)

  if "." in s {
    let parts = s.split(".")
    zero-pad(parts.at(0), ch-width) + "." + zero-pad(parts.at(1), pg-width)
  } else {
    // Single ID like "1" -> "01.01" (chapter.first-page)
    zero-pad(s, ch-width) + "." + zero-pad("1", pg-width)
  }
}

// Helper: Extract chapter ID from page ID (supports int or string, with or without dot)
#let get-chapter-id(id) = {
  let s = to-str(id)
  if "." in s { s.split(".").at(0) } else { s }
}

