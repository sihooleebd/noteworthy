# Content Creation Guide

This guide explains how to add and structure content in your Noteworthy project.

## Directory Structure

Content is organized hierarchy in the `content/` directory:

```text
content/
├── 0/               # Chapter 0 (e.g., Introduction)
│   ├── 0.typ        # Page 0 of Chapter 0
│   ├── 1.typ        # Page 1 of Chapter 0
│   └── ...
├── 1/               # Chapter 1
│   ├── 0.typ
│   └── ...
```

-   **Chapters** are folders with integer names (`0`, `1`, `2`...).
-   **Pages** are `.typ` files with integer names (`0.typ`, `1.typ`...).
-   **Ordering**: The build system sorts chapters and pages numerically. Thus, you don't need to start with 0. 

## Writing Content

Each page file (e.g., `content/1/0.typ`) should start by importing the templater:

```typst
#import "../../templates/templater.typ": *

= Page Title

Your content goes here.
```

### Headings
Use standard Typst headings:
-   `= Title` (Level 1 - Page Title)
-   `== Section` (Level 2)
-   `=== Subsection` (Level 3)

### Using Blocks
Use the blocks provided by the `block` module to structure your educational content:

```typst
#definition("Term")[
  Definition text...
]

#example("Example")[
  Example text...
  #solution[
    Solution text...
  ]
]
```

See [Modules: Others](modules/others.md) for a full list of available blocks.

### Images
Place images in `content/images/` or a local `images/` folder and link them:
```typst
#image("../images/diagram.png", width: 80%)
```
