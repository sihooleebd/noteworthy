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

// -----------------------------------------------------
// Link markers
// -----------------------------------------------------
//
// A URI link is the only annotation that survives `pdfunite`/pypdf with its
// text intact, so the marker rides in the URI and is rewritten afterwards.
// An anchor is drawn as ordinary content: it has to occupy a real position
// on the page, because that position is the link destination.

#let nw-anchor(name, body) = if name == none { body } else {
  // The real Typst label is what the language server sees: tinymist builds
  // its label index from the compiled document, not from `<...>' spelled out
  // in the source, so one attached here gives the block completion and
  // go-to-definition exactly as a hand-written label would.
  [#link("nw-anchor:" + name, body)#label(name)]
}

#let nw-ref(name, body) = link("nw-ref:" + name, body)

// The colour the scheme gives a block, so a reference to one reads in the
// same colour its heading does.  Blocks are keyed by name in the scheme and
// by `lower(title)' everywhere else -- the same thing for every block that
// ships, but looked up both ways so a renamed title does not silently lose
// its colour.
#let _kind-color(kind) = {
  if kind == none { return none }
  let blocks = active-theme.at("blocks", default: (:))
  if kind in blocks { return blocks.at(kind).at("stroke", default: none) }
  let hit = none
  for (name, cfg) in blocks {
    if hit == none and lower(cfg.at("title", default: "")) == kind {
      hit = cfg.at("stroke", default: none)
    }
  }
  hit
}

// -----------------------------------------------------
// Where we are
// -----------------------------------------------------
//
// A page cannot work out which page it is: it is included, and the include
// says nothing about where from.  parser.typ sets this before each one, and
// both the numbering and the reference rule read it -- the rule to tell
// whether a reference is being read on the page its target sits on.

// The formatted ids travel too, because a reference read from another page
// has to name this one -- "in Chapter 08.01" -- and the padding that produces
// is the template's business.
#let nw-location = state("nw-location", (ch: "", pg: "", cid: "", pid: ""))
#let nw-set-location(ch, pg, cid, pid) = nw-location.update(
  (ch: ch, pg: pg, cid: cid, pid: pid))

// -----------------------------------------------------
// The reference rule
// -----------------------------------------------------

// One context for the whole rule, opened once at the top.  Reading the page
// from a context nested deeper inside made `nw-location' see the document's
// last page for several introspection runs before settling, which in a
// whole-document compile -- the live preview -- is a different page from the
// one the reference is on, and the document stopped converging.
#let xref-rule = it => context {
  let key = str(it.target)
  let here-now = nw-location.get()
  let reads(entry) = {
    // On the page its target is on, naming that page again adds nothing:
    // "Theorem 1" reads better than "Theorem 1 in Chapter 08.01" three lines
    // below the theorem itself.
    let same-page = entry.ch == here-now.ch and entry.pg == here-now.pg
    let body = if same-page { entry.same } else { entry.full }
    let col = _kind-color(entry.at("kind", default: none))
    nw-ref(key, if col == none { body } else { text(fill: col, body) })
  }
  let mine = query(<nw-caption>).filter(m => m.value.label == key)
  if mine.len() > 0 {
    // A block in this very compilation.  It reads itself, so this is right
    // with no first pass having run -- which is what makes a reference
    // resolve in the live preview, where there is no first pass and never
    // will be.  The preview compiles the whole book at once, so this covers
    // references to other pages there too, and has to choose between the two
    // readings the way the injected map does, or the preview and the built
    // PDF would word the same reference differently.
    reads(mine.first().value)
  } else if key in label-map {
    reads(label-map.at(key))
  } else if query(it.target).len() > 0 {
    // Not one of ours: an equation, a heading, a figure.  Typst numbers and
    // links those perfectly well on its own.
    it
  } else {
    // Neither here nor in the map.  Show it rather than failing the build: a
    // typo should be findable in the PDF, not fatal three pages earlier.
    text(fill: red)[?#key]
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

// The address a reference carries when it is read from another page, exactly
// as `_caption' in xref.py builds it.  Under document numbering the number is
// already the whole address; under chapter numbering the page has to be named;
// a block-local number -- a solution outside any block -- says nothing about
// where to look, so it always names the page.
#let _address(loc, scoped, numbered) = {
  if ref-format == "number-only" { "" }
  else if scoped and block-numbering == "document" and numbered { "" }
  else if scoped and block-numbering == "chapter" {
    if loc.cid != "" { " in " + chapter-name + " " + loc.cid } else { "" }
  } else if loc.pid != "" { " in " + chapter-name + " " + loc.pid } else { "" }
}

// Both readings of a reference to this block, as `_caption' in xref.py builds
// them: `same' for a reference on the same page, `full' with the address for
// anywhere else.  Derived from counters and the current location only -- never
// from another piece of state -- because a state whose value is computed from
// state the first then feeds is a loop the introspection pass cannot settle.
#let _entry(kind, title, given, numbered, loc) = {
  let num = if not numbered or not number-blocks { none } else {
    let n = if given == auto { _block-counter(kind).get().at(0) } else { given }
    _scoped-number(n, loc)
  }
  let head = upper(kind.at(0)) + kind.slice(1)
  let base = if num != none { head + " " + num } else if title != "" {
    head + " \"" + title + "\""
  } else { head }
  // The kind rides along so a reference can be drawn in the colour the
  // scheme gives that block, the same one its own heading uses.
  (same: base, full: base + _address(loc, true, num != none),
   ch: loc.ch, pg: loc.pg, kind: kind)
}

// Counters restart on every page, whatever the numbering scope.
//
// The scope chooses how much of the address the number carries, not where
// counting restarts: "8.2.1" already says chapter 8, page 2, and continuing
// the count across pages on top of that produced "Definition 8.2.3" for the
// first definition on the page.  A build compiles one page per target so it
// gets this for free; a single compilation of the whole book -- which is what
// the live preview is -- has no page boundary of its own and needs telling.
#let nw-page-start(first-of-chapter) = {
  for kind in active-theme.blocks.keys() {
    _block-counter(lower(kind)).update(0)
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
#let nw-in-block(body, kind: none, title: "", given: auto, numbered: true) = {
  _block-uid.step()
  context {
    let id = _block-uid.get().at(0)
    // Carries how this block reads, so a solution inside can name it.  Built
    // from the same ingredients the heading used rather than handed across in
    // a state, which is what keeps this out of a cycle.
    let cap = if kind == none { none } else {
      _entry(kind, title, given, numbered, nw-location.get())
    }
    nw-block-stack.update(s => s + ((id: id, caption: cap),))
    body
    // Closes the block for the first pass too, which rebuilds this same
    // stack from the marks and would otherwise never learn where to pop.
    [#std.metadata((t: "block-end")) <nw-mark>]
    nw-block-stack.update(s => s.slice(0, -1))
  }
}

// The number a solution prints: its position within the block it is in, or
// within the page when it is in no block at all.
#let nw-solution-number(name: none, given: auto) = context {
  let stack = nw-block-stack.get()
  let parent = if stack.len() > 0 { stack.last() } else { none }
  let c = counter("nw-sol-" + if parent != none { str(parent.id) } else { "page" })
  // Steps even for a hand-numbered solution, exactly as a block's counter
  // does: the number takes a slot rather than stepping aside from one, so
  // the next automatic solution does not repeat what was just written.
  c.step()
  context {
    let n = if given == auto { c.get().at(0) } else { given }
    let loc = nw-location.get()
    let base = "Solution " + str(n)
    // "Solution 2" counts within its block, so on its own it picks out
    // nothing: a page can hold several blocks that each have a second
    // solution.  Naming the block is what makes it an address, and that
    // block's own caption already carries as much of the chapter and page
    // as the numbering scope leaves ambiguous.
    let entry = if parent != none and parent.caption != none {
      (same: base + " of " + parent.caption.same,
       full: base + " of " + parent.caption.full)
    } else {
      (same: base, full: base + _address(loc, false, true))
    }
    let entry = (..entry, ch: loc.ch, pg: loc.pg, kind: "solution")
    if name != none { [#std.metadata((label: name, ..entry)) <nw-caption>] }
    [#n]
  }
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

// What a reference to this block reads when the reference sits in the same
// compilation -- which, building a page at a time, means the same page.
//
// The block publishes this itself rather than the build computing it, so it
// is available with no first pass: the live preview compiles one page and
// nothing else, and a reference to a block on that page used to fall through
// to the injected map, find nothing, and print `?label' in red while the
// block it named sat three lines above.
//
// Reads the counter rather than stepping it -- `nw-block-number' has already
// stepped it for this block, and the value stands until the next one steps.
#let nw-caption(name, kind, title, given, numbered: true) = {
  if name == none { return none }
  context {
    let entry = _entry(kind, title, given, numbered, nw-location.get())
    [#std.metadata((label: name, ..entry)) <nw-caption>]
  }
}

// What a reference to this block should read: "Theorem 8.3".
#let nw-block-caption(title, number) = {
  if number == none { title } else { [#title #number] }
}
