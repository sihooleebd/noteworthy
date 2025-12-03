#import "../config.typ": * //edit this file to configure
#import "./templater.typ": *

#let target = sys.inputs.at("target", default: none)

#if target == none or target == "cover" {
  if display-cover {
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
  if display-outline {
    outline()
  }
}

#for chapter in hierarchy {
  let first-page = chapter.pages.at(0)
  let chapter-id = first-page.id.slice(0, 2)

  if target == none or target == "chapter-" + chapter-id {
    if display-chap-cover {
      chapter-cover(
        number: "Chapter " + chapter-id,
        title: chapter.title,
        summary: chapter.summary,
      )
    }
  }

  for page in chapter.pages {
    if target == none or target == page.id {
      // Inject chapter metadata if missing (for single page compilation)
      if target != none and target != "chapter-" + chapter-id {
        [#metadata(("Chapter " + chapter-id, chapter.title)) <chapter-cover>]
      }
      show: project.with(
        number: subchap-name + " " + page.id,
        title: page.title,
      )
      include "../content/" + lower(chapter-name) + " " + chapter-id + "/" + page.id + ".typ"
    }
  }
}
