# Theming

Customize the visual appearance of your Noteworthy documents.

## Theme System

Noteworthy comes with **15+ built-in color schemes**. Themes are applied globally to pages, headings, blocks, plots, and all visual elements.

### Viewing Available Themes

Generate a visual catalogue of all themes:

```bash
cd images
typst compile theme_catalogue.typ --root ..
```

Or view them in Noteworthy Studio under **Settings → Theme & Display**.

### Setting a Theme

Edit `config/constants.json`:

```json
{
  "display-mode": "catppuccin-mocha"
}
```

Or in Noteworthy Studio: **Settings → Theme & Display → Theme selector**

### Available Themes

| Theme              | Style | Description                |
| ------------------ | ----- | -------------------------- |
| `default`          | Light | Clean, minimal light theme |
| `ocean`            | Dark  | Deep blue, calming         |
| `catppuccin-mocha` | Dark  | Popular warm dark theme    |
| `catppuccin-latte` | Light | Warm light variant         |
| `nord`             | Mixed | Arctic, muted colors       |
| `dracula`          | Dark  | Purple-accented dark       |
| `solarized-light`  | Light | Classic readability        |
| `solarized-dark`   | Dark  | Solarized dark variant     |
| `gruvbox`          | Dark  | Retro, warm colors         |
| `one-dark`         | Dark  | Atom-inspired              |
| `tokyo-night`      | Dark  | Vibrant accents            |
| ...                | ...   | And more!                  |

---

## Theme Structure

Each theme defines a color palette in `templates/schemes/data/<theme>.json`:

```json
{
  "page-fill": "#1e1e2e",
  "text-main": "#cdd6f4",
  "text-accent": "#89b4fa",
  "heading-fill": "#313244",
  "block-stroke": "#45475a"
}
```

### Core Color Keys

| Key            | Purpose            |
| -------------- | ------------------ |
| `page-fill`    | Background color   |
| `text-main`    | Primary text color |
| `text-accent`  | Accent/link color  |
| `heading-fill` | Heading background |
| `block-stroke` | Block border color |

---

## Creating Custom Themes

1. Copy an existing theme:
   ```bash
   cp templates/schemes/data/ocean.json templates/schemes/data/mytheme.json
   ```

2. Edit the colors in `mytheme.json`

3. Set it in `config/constants.json`:
   ```json
   {
     "display-mode": "mytheme"
   }
   ```

---

## Style Overrides

Override default styles for specific elements using the `style` parameter.

### Stroke

```typst
style: (stroke: red)
style: (stroke: (paint: blue, thickness: 2pt))
style: (stroke: (dash: "dashed", paint: gray))
```

### Fill

```typst
style: (fill: red.transparentize(50%))
style: (fill: gradient.linear(red, blue))
```

---

## Smart Labels

Labels support intelligent placeholders that are automatically calculated:

| Placeholder | Applies To          | Description      |
| ----------- | ------------------- | ---------------- |
| `{angle}`   | `angle`             | Angle in degrees |
| `{length}`  | `segment`, `vector` | Euclidean length |
| `{radius}`  | `circle`, `arc`     | Radius value     |
| `{area}`    | `circle`, `polygon` | Calculated area  |
| `{circum}`  | `circle`, `polygon` | Circumference    |

**Example:**

```typst
segment(A, B, label: "Len: {length}")  // "Len: 5.0"
angle(A, O, B, label: "{angle}")       // "45°"
```

---

## Label Positioning

Labels are positioned automatically:

| Element          | Position                    |
| ---------------- | --------------------------- |
| Points           | Above the point             |
| Vectors/Segments | Perpendicular offset        |
| Functions        | End of curve (legend-style) |
| Circles/Shapes   | Top-right corner            |

All labels have a white background to mask underlying grid lines.

---

## Next Steps

- [Modules Guide →](modules.md)
- [Config Files Reference →](../reference/config-files.md)
