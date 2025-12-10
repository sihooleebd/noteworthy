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
// Build all schemes from JSON dynamically
#let schemes = {
  let s = (:)
  for (name, data) in schemes-data {
    s.insert(name, build-scheme(data))
  }
  s
}
