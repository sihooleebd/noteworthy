# Content Authoring

Learn how to write effective Typst content for Noteworthy documents.

## Content Organization

Content lives in the `content/` directory, organized by chapters and pages:

```
content/
├── 1/              # Chapter 1
│   ├── 1.typ       # Page 1.1
│   ├── 2.typ       # Page 1.2
│   └── 3.typ       # Page 1.3
├── 2/              # Chapter 2
│   └── 1.typ       # Page 2.1
└── 3/              # Chapter 3
    ├── 1.typ
    └── 2.typ
```

### Naming Conventions

| Type            | Format         | Examples                    |
| --------------- | -------------- | --------------------------- |
| Chapter folders | Integer        | `1/`, `2/`, `10/`           |
| Page files      | Integer `.typ` | `1.typ`, `2.typ`            |
| Insert pages    | Decimal        | `1.5.typ` (between 1 and 2) |

> [!TIP]
> Use decimal names like `2.5.typ` to insert new pages without renumbering existing ones.

---

## Page Structure

Every page starts with the templater import and a title:

```typst
#import "../../templates/templater.typ": *

= Page Title

Your content starts here.

== Section Heading

More content...

=== Subsection

Even more content...
```

### Heading Levels

| Syntax           | Level | Usage                     |
| ---------------- | ----- | ------------------------- |
| `= Title`        | H1    | Page title (one per page) |
| `== Section`     | H2    | Major sections            |
| `=== Subsection` | H3    | Subsections               |
| `==== Detail`    | H4    | Fine detail               |

---

## Using Blocks

Blocks are semantic containers for educational content:

### Definitions

```typst
#definition("Vector Space")[
  A *vector space* over a field $F$ is a set $V$ together with 
  two operations: vector addition and scalar multiplication.
]
```

### Theorems & Proofs

```typst
#theorem("Pythagorean Theorem")[
  In a right triangle, $a^2 + b^2 = c^2$.
]

#proof[
  Consider a square with side length $(a + b)$...
]
```

### Examples & Solutions

```typst
#example("Finding Eigenvalues")[
  Find the eigenvalues of $A = mat(2, 1; 1, 2)$.
  
  #solution[
    The characteristic polynomial is $det(A - lambda I) = 0$...
  ]
]
```

### Other Blocks

| Block            | Purpose           |
| ---------------- | ----------------- |
| `#remark[...]`   | Side notes        |
| `#warning[...]`  | Cautions          |
| `#note[...]`     | General notes     |
| `#exercise[...]` | Practice problems |

---

## Mathematics

Typst has powerful math typesetting:

### Inline Math

```typst
The equation $x^2 + y^2 = r^2$ defines a circle.
```

### Display Math

```typst
$ integral_0^infinity e^(-x^2) dif x = sqrt(pi)/2 $
```

### Matrices

```typst
$ A = mat(
  1, 2, 3;
  4, 5, 6;
  7, 8, 9
) $
```

### Aligned Equations

```typst
$ f(x) &= x^2 + 2x + 1 \
       &= (x + 1)^2 $
```

---

## Images

Place images in your content folder or a shared `images/` directory:

```typst
#figure(
  image("images/diagram.png", width: 80%),
  caption: [Architecture diagram]
)
```

### Image Paths

| Location       | Path                             |
| -------------- | -------------------------------- |
| Same folder    | `image("diagram.png")`           |
| Content images | `image("../images/diagram.png")` |
| Project root   | `image("../../images/logo.png")` |

---

## Drawing & Plotting

Use the canvas and graph modules for visual content:

### Simple Drawing

```typst
#canvas({
  point((0, 0), label: "O")
  vector((0, 0), (3, 2), label: $arrow(v)$)
  circle-obj((0, 0), 1, label: "Unit circle")
})
```

### Function Plots

```typst
#plot-graph(
  domain: (-5, 5),
  {
    plot-func(x => x*x, label: $x^2$)
    plot-func(x => 2*x, label: $2x$)
  }
)
```

See the [Canvas](../modules/canvas.md) and [Graph](../modules/graph.md) module docs for more.

---

## Code Blocks

Typst syntax highlighting:

````typst
```python
def hello():
    print("Hello, World!")
```
````

Inline code: `` `variable` ``

---

## Tables

```typst
#table(
  columns: 3,
  [Header 1], [Header 2], [Header 3],
  [Cell 1], [Cell 2], [Cell 3],
  [Cell 4], [Cell 5], [Cell 6],
)
```

---

## Best Practices

1. **One topic per page** — Keep pages focused
2. **Use blocks** — Semantic structure helps readers
3. **Consistent headings** — Start each page with `=`
4. **Relative paths** — Use `../` for cross-directory links
5. **Preview often** — Use Noteworthy Studio for instant feedback

---

## Next Steps

- [Building Guide →](building.md)
- [Theming Guide →](theming.md)
- [Canvas Module →](../modules/canvas.md)
