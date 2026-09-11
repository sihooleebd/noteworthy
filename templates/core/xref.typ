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
// Where we are
// -----------------------------------------------------
//
// A page cannot work out which page it is: it is included, and the include
// says nothing about where from.  parser.typ sets this before each one, and
// both the numbering and the reference rule read it -- the rule to tell
// whether a reference is being read on the page its target sits on.

#let nw-location = state("nw-location", (ch: "", pg: ""))
#let nw-set-location(ch, pg) = nw-location.update((ch: ch, pg: pg))

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
      let entry = label-map.at(key)
      context {
        let here-now = nw-location.get()
        // On the page the block is on, saying which page it is on adds
        // nothing -- "Theorem 1" reads better than "Theorem 1 in Chapter
        // 08.01" three lines below the theorem itself.
        let same-page = entry.ch == here-now.ch and entry.pg == here-now.pg
        nw-ref(key, if same-page { entry.same } else { entry.full })
      }
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

// The number a block prints carries exactly what its own scope does not make
// obvious.  Restarting per page, the count alone is unambiguous on that page,
// so "Theorem 1" is right and "Theorem 8.1.1" is noise.  Restarting per
// chapter, the page has to say which page; never restarting, the chapter too.
// A reference adds the rest of the address, since it is read from elsewhere.
#let _scoped-number(n, loc) = {
  if block-numbering == "document" { loc.ch + "." + loc.pg + "." + str(n) }
  else if block-numbering == "chapter" { loc.pg + "." + str(n) }
  else { str(n) }
}

// Called once per compiled target, before any content.
#let nw-init-block-counters() = {
  for (kind, start) in block-offsets.pairs() {
    _block-counter(kind).update(int(start))
  }
}

// -----------------------------------------------------
// Which block are we inside?
// -----------------------------------------------------
//
// A solution counts within the block containing it, so something has to say
// what "containing" means.  Position alone cannot: the markers record where
// a block starts and nothing records where it ends, so a solution written
// after a block closes, or inside the outer of two nested blocks, looks
// exactly like one written inside the inner block.
//
// So a block declares its extent instead of it being inferred.  Wrapping the
// body pushes an id for the duration of that body and pops it afterwards,
// which makes the innermost open block the last entry on the stack -- the
// definition of "inside", and correct however deeply blocks nest.

#let _block-uid = counter("nw-block-uid")
#let nw-block-stack = state("nw-block-stack", ())

// Wrap the body of a block, so everything within it counts as inside.
#let nw-in-block(body) = {
  _block-uid.step()
  context {
    let id = _block-uid.get().at(0)
    nw-block-stack.update(s => s + (id,))
    body
    // Closes the block for the first pass too, which rebuilds this same
    // stack from the marks and would otherwise never learn where to pop.
    [#std.metadata((t: "block-end")) <nw-mark>]
    nw-block-stack.update(s => s.slice(0, -1))
  }
}

// The number a solution prints: its position within the block it is in, or
// within the page when it is in no block at all.
#let nw-solution-number() = context {
  let stack = nw-block-stack.get()
  let parent = if stack.len() > 0 { str(stack.last()) } else { "page" }
  counter("nw-sol-" + parent).step()
  context counter("nw-sol-" + parent).get().at(0)
}

// The number this block should print, or none when numbering is off.
// GIVEN replaces the counted part; the counter still advances, so a block
// numbered by hand occupies its slot rather than making the next one repeat.
#let nw-block-number(kind, given: auto) = {
  if not number-blocks { return none }
  _block-counter(kind).step()
  context {
    let n = if given == auto { _block-counter(kind).get().at(0) } else { given }
    _scoped-number(n, nw-location.get())
  }
}

// What a reference to this block should read: "Theorem 8.3".
#let nw-block-caption(title, number) = {
  if number == none { title } else { [#title #number] }
}
