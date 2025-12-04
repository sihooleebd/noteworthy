// Load configuration from JSON
#let config = json("../config.json")

// Export configuration variables
#let title = config.title
#let subtitle = config.subtitle
#let authors = config.authors
#let affiliation = config.affiliation
#let logo = config.logo
#let show-solution = config.show-solution
#let solutions-text = config.solutions-text
#let problems-text = config.problems-text
#let chapter-name = config.chapter-name
#let subchap-name = config.subchap-name
#let font = config.font
#let title-font = config.title-font
#let display-cover = config.display-cover
#let display-outline = config.display-outline
#let display-chap-cover = config.display-chap-cover
#let box-margin = eval(config.box-margin)
#let box-inset = eval(config.box-inset)
#let render-sample-count = config.render-sample-count
#let display-mode = config.display-mode
#let hierarchy = config.hierarchy

// Load schemes
#import "./default-schemes.typ": *

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

// Content hierarchy preface
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

// Snippets
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
