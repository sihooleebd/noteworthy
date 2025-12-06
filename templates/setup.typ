// =====================
// CONFIGURATION LOADING
// =====================

// Load configuration from JSON
#let config = json("config/config.json")

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
#let render-implicit-count = config.render-implicit-count
#let display-mode = config.display-mode
#let hierarchy = json("config/hierarchy.json")

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
)

#let active-theme = colorschemes.at(lower(display-mode), default: scheme-dark)

// Import snippets
#import "config/snippets.typ": *
