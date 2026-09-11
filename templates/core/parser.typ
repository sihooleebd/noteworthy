#import "../templater.typ": *
#import "scanner.typ": load-content-info
#import "xref.typ": xref-rule, nw-init-block-counters, nw-anchor, nw-set-location, nw-page-start

// `@label' resolves normally when the target is in this compilation and
// falls back to the injected map when it is not -- which, compiling one page
// at a time, is every reference to another page.
#show ref: xref-rule

// Counter starts for this page, when the numbering scope runs past it.  A
// page compiled on its own begins at nothing otherwise, so `chapter' and
// `document' numbering would silently restart on every page.
#nw-init-block-counters()

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

// Load content info from scanner (uses manifest or sys.inputs)
#let content-info = load-content-info()
#let chapter-folders = content-info.chapters
#let page-folders = content-info.pages


#for (i, chapter) in hierarchy.enumerate() {
  // Get folder name from sorted list
  let ch-folder = if i < chapter-folders.len() { chapter-folders.at(i) } else { str(i) }
  let total-chapters = hierarchy.len()
  let chapter-display-id = format-chapter-id(ch-folder, total-chapters)
  let total-pages = chapter.pages.len()

  // Get page files for this chapter (using folder name, not index)
  // Page files are numbered from 1, so the fallback has to be too.  Numbering
  // it from 0 did not merely miss -- `str(j)' for the third page is "2", the
  // name the second page really has, so a page map that had not caught up with
  // a new file silently rendered the wrong page's content instead of failing.
  let pg-files = page-folders.at(ch-folder, default: range(total-pages).map(j => str(j + 1)))

  if target == none or target == "chapter-" + str(i) {
    if display-chap-cover or target != none {
      nw-anchor("chapter-" + ch-folder, chapter-cover(
        number: chapter-name + " " + chapter-display-id,
        title: chapter.title,
        summary: chapter.summary,
      ))
    }
  }

  for (j, page) in chapter.pages.enumerate() {
    // Get file name from sorted list
    let pg-file = if j < pg-files.len() { pg-files.at(j) } else { str(j + 1) }
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
      // Which page the blocks that follow belong to.  A whole-document query
      // returns everything in order but says nothing about source files, and
      // attributing a block to its page is the whole job of the first pass.
      // The formatted ids travel with the marker: a reference says "in
      // Chapter 08.01", and the padding that produces is the template's
      // business, not something the build should try to reproduce.
      [#std.metadata((t: "page", ch: ch-folder, pg: pg-file,
                      cid: chapter-display-id, pid: page-display-id)) <nw-mark>]
      nw-set-location(ch-folder, pg-file, chapter-display-id, page-display-id)
      nw-page-start(j == 0)
      // A destination has to be somewhere, so the anchor is real content at
      // the top of the page rather than metadata, which has no position.
      [#nw-anchor("page-" + ch-folder + "-" + pg-file, box(width: 1pt, height: 1pt))]
      include "../../content/" + ch-folder + "/" + pg-file + ".typ"
    }
  }
}

