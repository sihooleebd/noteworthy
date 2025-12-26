# Theming & Styling

Customize the visual appearance of your documents.

## Theme System

Noteworthy comes with 13+ built-in color schemes. The current theme is applied globally to pages, headings, blocks, and plots.

### Available Themes
To view all available themes visually, check the **Theme Library**:
[**View Theme Library (PDF)**](../content/images/theme-library.pdf)

To change the theme, edit `config/config.json`:
```json
{
  "theme": "catppuccin-mocha"
}
```

---

## Smart Labels

Labels support intelligent substitution using placeholders. Values are automatically calculated.

| Placeholder | Applies To          | Description      |
| :---------- | :------------------ | :--------------- |
| `{angle}`   | `angle`             | Angle in degrees |
| `{length}`  | `segment`, `vector` | Euclidean length |
| `{radius}`  | `circle`, `arc`     | Radius value     |
| `{area}`    | `circle`, `polygon` | Calculated area  |
| `{circum}`  | `circle`, `polygon` | Circumference    |

**Example:**
```typst
segment(A, B, label: "Len: {length}") // "Len: 5.0"
angle(A, O, B, label: "{angle}")      // "45°"
```

---

## Label Positioning

Labels are positioned automatically to avoid overlaps and ensure clarity.

- **Points**: Placed slightly **above** the point.
- **Vectors/Segments**: Offset **perpendicular** to the line (0.3 units).
- **Functions**: Placed at the **end of the curve** (right side) to act as a clear legend.
- **Circles/Shapes**: Placed at the **top-right** corner of the bounding box (anchor: south-west).

All labels have a white background to mask underlying grid lines.

---

## Style Reference

You can override the default theme styles for any object using the `style` parameter.

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

**Note**: Most plotting functions accept `...style` arguments, but object constructors (`point`, `vector`) take a dedicated `style:` named argument.
