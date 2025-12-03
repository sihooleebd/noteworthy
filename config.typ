//Hello user! If you are looking at this file,
//you are at the place where you can configure
//your theme. To view the full document, go and
//look at ./templates/parser.typ!
//If you have any problems writing with math, take this website for reference:
//https://tug.ctan.org/info/typstfun/typstfun.pdf
//
//=================
//document settings
//=================

#let title = "Noteworthy Framework"
#let subtitle = "Examples & Documentation"
#let authors = ("Sihoo Lee", "Lee Hojun")
#let affiliation = "Noteworthy"
#let logo = none //Write from view of /template/covers/~.typ
#let show-solution = true
#let solutions-text = "Solutions"
#let problems-text = "Problems"
#let chapter-name = "Chapter"
#let subchap-name = "Section"



//=======
//display
//=======
#let font = "IBM Plex Serif"
#let title-font = "Noto Sans Adlam"
#let display-cover = true
#let display-outline = true
#let display-chap-cover = true
#let box-margin = 5pt
#let box-inset = 15pt
#let render-sample-count = 1000
#let display-mode = "rose-pine" //lower / upper case is ignored
#import "./templates/default-schemes.typ": * //loads default schemes
#let colorschemes = (
  dark: scheme-dark,
  light: scheme-light,
  print: scheme-print,
  rose-pine: scheme-rose-pine,
  nord: scheme-nord,
  dracula: scheme-dracula,
  gruvbox: scheme-gruvbox,
  catppuccin-mocha: scheme-catppuccin-mocha,
  catppuccin-latte: scheme-catppuccin-latte,
  solarized-dark: scheme-solarized-dark,
  solarized-light: scheme-solarized-light,
  tokyo-night: scheme-tokyo-night,
  everforest: scheme-everforest,
  moonlight: scheme-moonlight,
  //define more custom schemes here!
)
#let active-theme = colorschemes.at(lower(display-mode), default: scheme-dark)


//========================================================================
//content hierarchy
//Beware that if the IDs are defined wrong, they will result in an error.
//========================================================================

#let preface-content = [
  Welcome to the *Noteworthy Framework*. This document serves as both a demonstration of the framework's capabilities and a reference for its features.

  #v(1.5em)

  = About Noteworthy

  #v(0.5em)

  Noteworthy is a modular framework for creating beautiful educational documents in Typst. It provides a comprehensive set of tools for:

  - *Structured Layouts*: Automated chapters, sections, and covers.
  - *Themed Components*: Pre-styled blocks for definitions, theorems, examples, and more.
  - *Advanced Plotting*: Integrated 2D and 3D plotting capabilities.
  - *Customizable Themes*: A robust theming engine with multiple built-in presets.

  #v(1.5em)

  = Using This Guide

  #v(0.5em)

  Each section of this document demonstrates a specific module of the framework. You can find the source code for these examples in the `content/` directory, which serves as a practical reference for your own documents.
]

#let hierarchy = (
  (
    title: "Core Components",
    summary: "This chapter demonstrates the fundamental building blocks of the Noteworthy framework, including text blocks, layouts, and basic document structure.",
    pages: (
      (id: "01.01", title: "Content Blocks"),
      (id: "01.02", title: "Layout Elements"),
    ),
  ),
  (
    title: "Plotting & Geometry",
    summary: "Explore the powerful plotting capabilities of Noteworthy, from basic 2D graphs to complex geometric constructions and vector diagrams.",
    pages: (
      (id: "02.01", title: "Basic Plots"),
      (id: "02.02", title: "Geometry (Geoplot)"),
      (id: "02.03", title: "Vectors (Vectorplot)"),
      (id: "02.04", title: "3D Space (Spaceplot)"),
    ),
  ),
  (
    title: "Data & Visualization",
    summary: "Learn how to visualize data and mathematical concepts using the Grapher, Combiplot, and Tableplot modules.",
    pages: (
      (id: "03.01", title: "Function Graphs"),
      (id: "03.02", title: "Combinatorics"),
      (id: "03.03", title: "Tables"),
    ),
  ),
)

//


//=========================
//define your snippets here
//=========================

#let st = [such that]
#let wlog = [without loss of generality]
#let qed = [$therefore$ Q.E.D.]
#let sht = [show that]
#let Sht = [Show that]

#let sr = $attach(, t: 2)$
#let cb = $attach(, t: 3)$
#let sq(k) = $sqrt(#k)$
#let rd(body) = $attach(, t: body)$
#let invs = $attach(, t: -1)$
#let comp = $attach(, t: c)$
#let xy = $x y$

#let bmat(..cols) = $mat(..cols, delim: "[")$
#let Bmat(..cols) = $mat(..cols, delim: "{")$
#let vmat(..cols) = $mat(..cols, delim: "|")$
#let Vmat(..cols) = $mat(..cols, delim: "||")$

