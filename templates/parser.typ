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

#for (i, chapter) in hierarchy.enumerate() {
  let chapter-idx = str(i)
  let ch-num = str(chapter.at("number", default: i + 1))
  let total-chapters = hierarchy.len()
  let chapter-display-id = format-chapter-id(ch-num, total-chapters)
  let total-pages = chapter.pages.len()

  if target == none or target == "chapter-" + chapter-idx {
    if display-chap-cover or target != none {
      chapter-cover(
        number: chapter-name + " " + chapter-display-id,
        title: chapter.title,
        summary: chapter.summary,
      )
    }
  }

  for (j, page) in chapter.pages.enumerate() {
    let page-idx = str(j)
    let pg-num = str(page.at("number", default: j + 1))
    let page-target = chapter-idx + "/" + page-idx
    let page-display-id = format-page-id(ch-num + "." + pg-num, total-pages, total-chapters)

    if target == none or target == page-target {
      // Inject chapter metadata if missing (for single page compilation)
      if target != none and target != "chapter-" + chapter-idx {
        [#metadata((chapter-name + " " + chapter-display-id, chapter.title)) #label("chapter-" + str(i + 1))]
      }
      show: project.with(
        number: chapter-name + " " + page-display-id,
        title: page.title,
      )
      include "../content/" + chapter-idx + "/" + page-idx + ".typ"
    }
  }
}

