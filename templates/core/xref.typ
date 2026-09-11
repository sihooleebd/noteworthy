// =====================================================
// CROSS-REFERENCES AND BLOCK NUMBERING
// =====================================================
//
// The book is compiled one page at a time and the PDFs are merged, so a
// label defined on another page is simply not in the document Typst is
// looking at.  Referencing it is a hard error, which is why `@label' across
// pages broke the build rather than rendering oddly.
//
// Two things fix that, and both are driven by data the build computes in a
// first pass over the whole document:
//
//   * a `show ref:' rule that falls back to a `label-map' when the target is
//     not in this compilation, so `@label' keeps its plain meaning and works
//     either way;
//   * `nw-ref:' / `nw-anchor:' link markers, which the post-merge pass turns
//     into real internal PDF links -- the merged file is the first place
//     where "which page did that land on" is even answerable.

#import "setup.typ": *

// -----------------------------------------------------
// Inputs
// -----------------------------------------------------

#let _input-json(key) = {
  let raw = sys.inputs.at(key, default: none)
  if raw == none { (:) } else { json(bytes(raw)) }
}

// label -> what a reference to it should read, e.g. "Theorem 8.3"
#let label-map = _input-json("label-map")

// kind -> where this target's counter starts, so numbering can run past the
// end of a page without the page being able to see its neighbours.  Empty
// for `page' scope, which is why that one needs no first pass.
#let block-offsets = _input-json("block-offsets")

// -----------------------------------------------------
// Link markers
// -----------------------------------------------------
//
// A URI link is the only annotation that survives `pdfunite`/pypdf with its
// text intact, so the marker rides in the URI and is rewritten afterwards.
// An anchor is drawn as ordinary content: it has to occupy a real position
// on the page, because that position is the link destination.

#let nw-anchor(name, body) = if name == none { body } else {
  link("nw-anchor:" + name, body)
}

#let nw-ref(name, body) = link("nw-ref:" + name, body)

// -----------------------------------------------------
// The reference rule
// -----------------------------------------------------

#let xref-rule = it => {
  let found = query(it.target)
  if found.len() > 0 {
    // In this compilation: let Typst number and link it as it always has.
    it
  } else {
    let key = str(it.target)
    if key in label-map {
      nw-ref(key, label-map.at(key))
    } else {
      // Neither here nor in the map.  Show it rather than failing the build:
      // a typo should be findable in the PDF, not fatal three pages earlier.
      text(fill: red)[?#key]
    }
  }
}

// -----------------------------------------------------
// Block numbering
// -----------------------------------------------------

#let _block-counter(kind) = counter("nw-block-" + kind)

// Which page is being rendered.  Blocks cannot work it out themselves -- a
// page is included, it does not know where from -- and the number has to say,
// or every page's "Theorem 1" refers to a different theorem.
#let nw-location = state("nw-location", (ch: "", pg: ""))
#let nw-set-location(ch, pg) = nw-location.update((ch: ch, pg: pg))

// A number is only useful to a reader if it identifies one block in the whole
// book.  Under `page' numbering that takes chapter and page as well, under
// `chapter' the chapter, and under `document' the count already does.
#let _qualified(n, loc) = {
  if block-numbering == "document" { str(n) }
  else if block-numbering == "chapter" { loc.ch + "." + str(n) }
  else { loc.ch + "." + loc.pg + "." + str(n) }
}

// Called once per compiled target, before any content.
#let nw-init-block-counters() = {
  for (kind, start) in block-offsets.pairs() {
    _block-counter(kind).update(int(start))
  }
}

// The number this block should print, or none when numbering is off.
#let nw-block-number(kind) = {
  if not number-blocks { return none }
  _block-counter(kind).step()
  context _qualified(_block-counter(kind).get().at(0), nw-location.get())
}

// What a reference to this block should read: "Theorem 8.3".
#let nw-block-caption(title, number) = {
  if number == none { title } else { [#title #number] }
}
