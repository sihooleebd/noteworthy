// =====================
// CONFIGURATION LOADING
// =====================

// Load configuration from split JSON files
#let metadata = json("../../config/metadata.json")
#let constants = json("../../config/constants.json")

// Export metadata variables
#let title = metadata.title
#let subtitle = metadata.subtitle
#let authors = metadata.authors
#let affiliation = metadata.affiliation
#let logo = metadata.logo

// Export constants variables
#let show-solution = constants.show-solution
#let solutions-text = constants.solutions-text
#let problems-text = constants.problems-text
#let chapter-name = constants.chapter-name
#let subchap-name = constants.subchap-name
#let font = constants.font
#let title-font = constants.title-font
#let display-cover = constants.display-cover
#let display-outline = constants.display-outline
#let display-chap-cover = constants.display-chap-cover
#let box-margin = eval(constants.box-margin)
#let box-inset = eval(constants.box-inset)
#let display-mode = constants.display-mode
#let pad-chapter-id = constants.pad-chapter-id
#let pad-page-id = constants.pad-page-id
#let heading-numbering = constants.heading-numbering
#let block-design = constants.at("block-design", default: "simple")
#let hierarchy = json("../../config/hierarchy.json")

// Load schemes
#import "./scheme.typ": *

#import "./scheme.typ": schemes
#let colorschemes = schemes

#let active-theme = colorschemes.at(lower(display-mode), default: schemes.at("noteworthy-dark"))

// Import snippets
#import "../../config/snippets.typ": *

// =====================
// GLOBAL STYLING
// =====================

#show raw: it => {
  let theme = active-theme
  let bg = if "page-fill" in theme { eval(theme.page-fill) } else { white }
  let text-col = if "text-main" in theme { eval(theme.text-main) } else { black }
  let accent = if "text-accent" in theme { eval(theme.text-accent) } else { blue }
  let highlight = if "plot" in theme and "highlight" in theme.plot { eval(theme.plot.highlight) } else { rgb("eeeeee") }

  if it.block {
    block(
      width: 100%,
      fill: bg.lighten(5%), // Slight contrast from page background
      stroke: 0.5pt + text-col.lighten(60%),
      inset: 8pt,
      radius: 4pt,
      text(fill: text-col, size: 9pt, it),
    )
  } else {
    box(
      fill: accent.transparentize(90%),
      inset: (x: 2pt, y: 0pt),
      outset: (y: 2pt),
      radius: 2pt,
      text(fill: accent.darken(10%), it),
    )
  }
}

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

