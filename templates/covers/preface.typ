#import "../setup.typ": *

#let preface(
  theme: (:),
  content: [],
  authors: (),
) = {
  page(
    paper: "a4",
    fill: theme.page-fill,
    margin: (x: 2.5cm, y: 2.5cm),
    header: none,
    footer: none,
  )[
    #line(length: 100%, stroke: 1pt + theme.text-muted)

    #v(2cm)

    #text(
      font: title-font,
      size: 36pt,
      weight: "bold",
      tracking: 1pt,
      fill: theme.text-heading,
    )[Preface]

    #v(1.5cm)

    #line(length: 100%, stroke: 1pt + theme.text-muted)

    #v(2cm)

    #text(font: font, fill: theme.text-main, size: 11pt)[
      #content
    ]

    #v(2em)

    #line(length: 100%, stroke: 0.5pt + theme.text-muted)

    #v(1em)

    #align(right)[
      #text(
        font: title-font,
        fill: theme.text-main,
        size: 12pt,
        style: "italic",
      )[
        #if type(authors) == array {
          authors.join(" & ")
        } else {
          authors
        }\
        #text(size: 10pt, fill: theme.text-muted)[
          #affiliation
        ]
      ]
    ]
  ]
  counter(page).step()
}
