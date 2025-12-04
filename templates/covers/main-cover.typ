#import "../setup.typ": *

#let cover(
  theme: (:),
  title: "",
  subtitle: "",
  authors: (),
  affiliation: "",
  date: none,
) = {
  page(
    paper: "a4",
    fill: theme.page-fill,
    margin: (x: 2.5cm, y: 2.5cm),
  )[
    #line(length: 100%, stroke: 1pt + theme.text-muted)

    #v(1cm)

    // Main Title
    #text(
      size: 36pt,
      weight: "bold",
      tracking: 1pt,
      font: title-font,
      fill: theme.text-heading,
    )[
      #title
    ]

    #v(1cm)

    // Subtitle
    #if subtitle != "" {
      text(
        size: 18pt,
        fill: theme.text-accent,
        font: title-font,
        style: "italic",
      )[
        #subtitle
      ]
    }
    #if show-solution {
      text(
        size: 18pt,
        fill: theme.text-accent,
        font: title-font,
        style: "italic",
      )[
        (#solutions-text)
      ]
    } else {
      text(
        size: 18pt,
        fill: theme.text-accent,
        font: title-font,
        style: "italic",
      )[
        (#problems-text)
      ]
    }

    #v(1cm)

    #line(length: 100%, stroke: 1pt + theme.text-muted)

    #v(3cm)

    #text(fill: theme.text-main, size: 14pt, font: title-font, style: "italic")[Written by :]

    #text(fill: theme.text-main, font: title-font, style: "italic", size: 16pt)[
      #if type(authors) == array {
        authors.join("   /   ")
      } else {
        authors
      }
    ]

    #v(2cm)
    #if logo != none {
      // We use a box to ensure it doesn't break weirdly across pages (unlikely here but safe)
      box(image(logo, width: 3cm))
      v(0.5em) // Small gap between logo and affiliation text
    }
    #text(fill: theme.text-main, size: 14pt, font: title-font, style: "italic")[
      #upper(affiliation)
    ]

    #v(1fr)

    // Date Section
    #text(font: font, fill: theme.text-muted)[
      #if date == none {
        datetime.today().display()
      } else {
        date
      }
    ]
  ]
  counter(page).update(1)
}
