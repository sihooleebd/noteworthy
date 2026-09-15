# Blocks, numbering and references

Blocks come in unqualified from `templater.typ`.

```typst
#definition("Truncated Cone", label: "tcone")[ ... ]
#note("Why Differentiate?", auto, label: "why")[ ... ]   // auto = the number slot
#theorem("Arc Length", 3, label: "arc")[ ... ]           // a hand-written number
```

`definition` `theorem` `example` `note` `notation` `analysis` `equation`
`solution` `proof`

Signature: `(title, number, label: none)[body]`. `number` is positional and
optional: `auto` counts, an integer overrides while still taking the slot, so
the next automatic block does not repeat it.

## Numbering

Counters restart on **every page**. `block-numbering` in the config chooses how
much address the printed number carries, not where counting restarts:

| scope | prints |
|---|---|
| `page` | `1` |
| `chapter` | `2.1` (page, count) |
| `document` | `8.2.1` (chapter, page, count) |

## Solutions nest

`solution` counts within the block containing it, so two examples on a page can
each have a "Solution 1". A reference to one names its parent:
`Solution 2 of Example 8.2.1`. Blocks may nest arbitrarily, and a solution
may stand alone, in which case it counts within the page.

## References

`@label` anywhere. A reference to a Noteworthy block renders as
`Definition 8.2.1`, in that block kind's colour from the scheme, and links to
it in the merged PDF. Read on the page the target sits on, it drops the address
(`Theorem 1`, not `Theorem 1 in Chapter 08.01`).

A single-page compile has no cross-page label map, so `@label` pointing
elsewhere renders as a red `?label`. **Intended, not a fault** -- the label map
is built by a first pass over the whole book, which a partial render does not
run. Leave it alone; it resolves in a full build.

`#nw-anchor(name, body)` attaches a real Typst label so tinymist can index it.
