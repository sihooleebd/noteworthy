#import "../setup.typ": *
#import "../scanner.typ": load-content-info


#let outline(
  theme: (:),
) = {
  // Load content info from scanner (uses manifest or sys.inputs)
  let content-info = load-content-info()
  let chapter-folders = content-info.chapters
  let page-folders = content-info.pages
  // Get page map from input if available
  let page-map-str = sys.inputs.at("page-map", default: none)
  let page-map-file = sys.inputs.at("page-map-file", default: none)

  let page-map = if page-map-str != none {
    json(bytes(page-map-str))
  } else if page-map-file != none {
    json(page-map-file)
  } else {
    (:)
  }

  page(
    paper: "a4",
    fill: theme.page-fill,
    margin: (x: 2.5cm, y: 2.5cm),
  )[
    #std.metadata("outline") <outline>
    #line(length: 100%, stroke: 1pt + theme.text-muted)
    #v(0.5cm)

    #text(
      size: 24pt,
      weight: "bold",
      tracking: 1pt,
      font: font,
      fill: theme.text-heading,
    )[Table of Contents]

    #v(0.5cm)
    #line(length: 100%, stroke: 1pt + theme.text-muted)
    #v(1.5cm)

    // Read directly from hierarchy
    #for (i, chapter-entry) in hierarchy.enumerate() {
      // Get folder name from sorted list (positional mapping)
      let ch-folder = if i < chapter-folders.len() { chapter-folders.at(i) } else { str(i) }
      let chap-id = format-chapter-id(ch-folder, hierarchy.len())

      // Get page files for this chapter
      let pg-files = page-folders.at(str(i), default: range(chapter-entry.pages.len()).map(j => str(j)))
      block(breakable: false)[
        #text(
          size: 16pt,
          weight: "bold",
          font: font,
          fill: theme.text-accent,
        )[
          #chapter-name #chap-id
        ]
        #h(1fr)
        #text(
          size: 16pt,
          weight: "regular",
          style: "italic",
          font: font,
          fill: theme.text-main,
        )[
          #chapter-entry.title
        ]
        #v(0.5em)
        #line(length: 100%, stroke: 0.5pt + theme.text-muted.transparentize(50%))
      ]

      v(0.5em)

      grid(
        columns: (auto, 1fr, auto),
        row-gutter: 0.8em,
        column-gutter: 1.5em,

        ..for (j, page-entry) in chapter-entry.pages.enumerate() {
          // Use index-based keys for page-map
          let page-key = str(i) + "/" + str(j)
          let page-num = if page-map != (:) and page-key in page-map {
            str(page-map.at(page-key))
          } else {
            "—"
          }

          // Get file name from sorted list (positional mapping)
          let pg-file = if j < pg-files.len() { pg-files.at(j) } else { str(j) }
          let full-id = ch-folder + "." + pg-file
          let page-display-id = format-page-id(full-id, chapter-entry.pages.len(), hierarchy.len())

          (
            text(fill: theme.text-muted, font: font, weight: "medium")[#chapter-name #page-display-id],
            box(width: 100%)[
              #text(font: font, fill: theme.text-main)[#page-entry.title]
              #box(width: 1fr, repeat[#text(fill: theme.text-muted.transparentize(70%))[. ]])
            ],
            text(fill: theme.text-muted, font: font, weight: "medium")[#page-num],
          )
        }
      )

      v(1.5cm)
    }
  ]
}

