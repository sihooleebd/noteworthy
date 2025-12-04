#import "../setup.typ": *
#let project(theme: (:), number: "", title: "", author: "", affiliation: "", date: none, body) = {
  counter(heading).update(0)

  // Extract page ID from number (e.g., "Section 01.01" -> "01.01")
  let page-id = if number != "" and number.contains(" ") {
    number.split(" ").last()
  } else {
    number
  }

  set document(title: title, author: author)

  set page(
    paper: "a4",
    margin: (x: 1in, y: 1in),
    numbering: "1",
    fill: theme.page-fill, // Dynamic
  )

  // Optional stylin
  set text(font: font, size: 11pt, fill: theme.text-main)
  context {
    let chapter = query(selector(metadata).before(here()))
      .filter(el => {
        el.label != none and str(el.label).starts-with("chapter-") and str(el.label).len() == 10
      })
      .last()

    [#metadata((number, title, chapter)) #label(page-id)]

    let display_date = if date == none {
      datetime.today().display("[Month]/[day], [year]")
    } else {
      date
    }

    set heading(numbering: "1.1.")
    show heading: it => block(below: 1em)[
      #text(weight: "bold", fill: theme.text-heading, font: font, it)
    ]

    // Title Block
    align(left)[
      #if number != "" [
        #block(below: 1em)[
          #text(size: 22pt, fill: theme.text-accent, font: title-font, number)
        ]
      ]
      #block(below: 1em)[
        #text(weight: "bold", style: "italic", size: 40pt, font: title-font, title)
      ]

      #if author != "" [
        #block(below: 0.5em)[
          #text(size: 16pt, font: font, author)
        ]
      ]

      #if affiliation != "" [
        #block(below: 0.5em)[
          #text(size: 13pt, font: font, fill: theme.text-muted, affiliation)
        ]
      ]
    ]
  }

  line(length: 100%, stroke: 1pt + theme.text-muted)

  body
}
