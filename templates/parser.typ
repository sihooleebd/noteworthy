#import "templater.typ": *

#let target = sys.inputs.at("target", default: none)
#let page-offset = sys.inputs.at("page-offset", default: none)
#set heading(numbering: heading-numbering)

// Set page counter based on page offset
#if page-offset != none {
  let offset-value = int(page-offset)
  counter(page).update(offset-value)
}

#if target == none or target == "cover" {
  if display-cover or target == "cover" {
    cover(
      title: title,
      subtitle: subtitle,
      authors: authors,
      affiliation: affiliation,
    )
  }
}

#if target == none or target == "preface" {
  preface()
}

#if target == none or target == "outline" {
  if display-outline or target == "outline" {
    outline()
  }
}

// Get sorted folder names from content/
// chapter-folders is passed via sys.inputs from Python build
#let chapter-folders-str = sys.inputs.at("chapter-folders", default: none)
#let chapter-folders = if chapter-folders-str != none {
  json(bytes(chapter-folders-str))
} else {
  // Fallback: assume folders 0,1,2... based on hierarchy length
  range(hierarchy.len()).map(i => str(i))
}

// page-folders is a dict mapping chapter index to array of page file stems
#let page-folders-str = sys.inputs.at("page-folders", default: none)
#let page-folders = if page-folders-str != none {
  json(bytes(page-folders-str))
} else {
  // Fallback: assume files 0,1,2... based on pages length
  let result = (:)
  for (i, ch) in hierarchy.enumerate() {
    result.insert(str(i), range(ch.pages.len()).map(j => str(j)))
  }
  result
}

#for (i, chapter) in hierarchy.enumerate() {
  // Get folder name from sorted list
  let ch-folder = if i < chapter-folders.len() { chapter-folders.at(i) } else { str(i) }
  let total-chapters = hierarchy.len()
  let chapter-display-id = format-chapter-id(ch-folder, total-chapters)
  let total-pages = chapter.pages.len()

  // Get page files for this chapter
  let pg-files = page-folders.at(str(i), default: range(total-pages).map(j => str(j)))

  if target == none or target == "chapter-" + str(i) {
    if display-chap-cover or target != none {
      chapter-cover(
        number: chapter-name + " " + chapter-display-id,
        title: chapter.title,
        summary: chapter.summary,
      )
    }
  }

  for (j, page) in chapter.pages.enumerate() {
    // Get file name from sorted list
    let pg-file = if j < pg-files.len() { pg-files.at(j) } else { str(j) }
    let page-target = str(i) + "/" + str(j)
    let page-display-id = format-page-id(ch-folder + "." + pg-file, total-pages, total-chapters)

    if target == none or target == page-target {
      // Inject chapter metadata if missing (for single page compilation)
      if target != none and target != "chapter-" + str(i) {
        [#std.metadata((chapter-name + " " + chapter-display-id, chapter.title)) #label("chapter-" + str(i + 1))]
      }
      show: project.with(
        number: chapter-name + " " + page-display-id,
        title: page.title,
      )
      include "../content/" + ch-folder + "/" + pg-file + ".typ"
    }
  }
}

