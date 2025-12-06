// Load color schemes from JSON
#let schemes-data = json("config/schemes.json")

// Helper to convert hex string to rgb color
#let hex-to-rgb(hex) = {
  if hex == none { return none }
  rgb(hex)
}

// Helper to build a scheme from JSON data
#let build-scheme(data) = {
  let blocks = (:)
  for (name, block) in data.blocks {
    blocks.insert(name, (
      fill: hex-to-rgb(block.fill),
      stroke: hex-to-rgb(block.stroke),
      title: block.title,
    ))
  }

  (
    page-fill: hex-to-rgb(data.page-fill),
    text-main: hex-to-rgb(data.text-main),
    text-heading: hex-to-rgb(data.text-heading),
    text-muted: hex-to-rgb(data.text-muted),
    text-accent: hex-to-rgb(data.text-accent),
    blocks: blocks,
    plot: (
      stroke: hex-to-rgb(data.plot.stroke),
      highlight: hex-to-rgb(data.plot.highlight),
      grid: hex-to-rgb(data.text-main).transparentize(100% - data.plot.grid-opacity * 100%),
      bg: none,
    ),
  )
}

// Build all schemes from JSON
#let scheme-noteworthy-dark = build-scheme(schemes-data.at("noteworthy-dark"))
#let scheme-rose-pine = build-scheme(schemes-data.rose-pine)
#let scheme-noteworthy-light = build-scheme(schemes-data.at("noteworthy-light"))
#let scheme-nord = build-scheme(schemes-data.nord)
#let scheme-dracula = build-scheme(schemes-data.dracula)
#let scheme-gruvbox = build-scheme(schemes-data.gruvbox)
#let scheme-catppuccin-mocha = build-scheme(schemes-data.catppuccin-mocha)
#let scheme-catppuccin-latte = build-scheme(schemes-data.catppuccin-latte)
#let scheme-solarized-dark = build-scheme(schemes-data.solarized-dark)
#let scheme-solarized-light = build-scheme(schemes-data.solarized-light)
#let scheme-tokyo-night = build-scheme(schemes-data.tokyo-night)
#let scheme-everforest = build-scheme(schemes-data.everforest)
#let scheme-moonlight = build-scheme(schemes-data.moonlight)
