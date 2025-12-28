# Components & Blocks

Noteworthy includes a suite of semantic blocks for educational content.

## Mathematical Blocks

These blocks are automatically numbered and styled based on the theme.

### Definitions & Theorems

```typst
#definition("Prime Number")[
  A natural number greater than 1 that has no positive divisors other than 1 and itself.
]

#theorem("Fermat's Little Theorem")[
  If $p$ is a prime number, then for any integer $a$, the number $a^p - a$ is an integer multiple of $p$.
]
```

### Examples & Solutions

Designed for problem sets and worked examples.

```typst
#example("Solving Quadratics")[
  Solve for $x$: $x^2 - 4 = 0$

  #solution[
    Factor as $(x-2)(x+2)=0$.
    Thus, $x = 2$ or $x = -2$.
  ]
]
```

**Note**: Solutions can be hidden globally via `config.json` ("show_solutions": false).

### Proofs

Automatically appended with a QED symbol ($\square$).

```typst
#proof[
  The proof is left as an exercise to the reader.
]
```

---

## Callouts & Notes

Use these for non-mathematical emphasis.

```typst
#note[
  This is a general note sidebar.
]

#tip[
  Pro tip: Use `typst compile` to build faster.
]

#important[
  Do not delete the `templates/` directory!
]
```

---

## Layout

### Two-Column Sections

Switch to two-column layout for a section:

```typst
#show: columns.with(2)

This text will flow into two columns.
```

### Headings

Standard Typst headings are automatically styled:

```typst
= Chapter
== Section
=== Subsection
```

---

## Code Blocks

Syntax highlighting is built-in.

```typst
#code(lang: "python")[
def hello():
    print("Hello World")
]
```
