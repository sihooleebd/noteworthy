#import "../../config.typ": *

#let outline(
  theme: (:),
) = {
  page(
    paper: "a4",
    fill: theme.page-fill,
    margin: (x: 2.5cm, y: 2.5cm),
  )[
    #metadata("outline") <outline>
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

    // Read directly from hierarchy in config.typ
    #for chapter-entry in hierarchy {
      let first-page = chapter-entry.pages.at(0)
      let chap-id = first-page.id.slice(0, 2)

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
        columns: (auto, 1fr),
        row-gutter: 0.8em,
        column-gutter: 1.5em,

        ..for page-entry in chapter-entry.pages {
          (
            text(fill: theme.text-muted, font: font, weight: "medium")[#subchap-name #page-entry.id],
            box(width: 100%)[
              #text(font: font, fill: theme.text-main)[#page-entry.title]
              #box(width: 1fr, repeat[#text(fill: theme.text-muted.transparentize(70%))[. ]])
            ],
          )
        }
      )

      v(1.5cm)
    }
  ]
}
