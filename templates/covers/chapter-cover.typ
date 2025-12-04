#import "../../config.typ": *

#let chapter-cover(
  theme: (:),
  number: "",
  title: "",
  summary: none,
) = {
  // Extract chapter ID from number (e.g., "Chapter 01" -> "01")
  let chapter-id = if number != "" and number.starts-with("Chapter ") {
    number.slice(8)
  } else {
    number
  }

  page(
    paper: "a4",
    fill: theme.page-fill,
    margin: (x: 2.5cm, y: 2.5cm),
    header: none,
    footer: none,
  )[
    #metadata((number, title)) <chapter-cover>
    #label("chapter-" + chapter-id)
    #line(length: 100%, stroke: 1pt + theme.text-muted)

    #v(2cm)

    #if number != "" {
      text(
        font: title-font,
        size: 22pt,
        fill: theme.text-accent,
        tracking: 2pt,
      )[#number]
    }

    #v(0.5em)

    #text(
      font: title-font,
      size: 40pt,
      weight: "bold",
      fill: theme.text-heading,
    )[
      #title
    ]

    #v(1cm)

    #line(length: 100%, stroke: 1pt + theme.text-muted)

    #v(2cm)

    #if summary != none {
      block(width: 100%)[
        #text(
          font: font,
          fill: theme.text-main,
          size: 14pt,
          style: "italic",
          weight: "regular",
        )[
          #summary
        ]
      ]
    }

    #v(1fr)
  ]
  counter(page).step()
}
