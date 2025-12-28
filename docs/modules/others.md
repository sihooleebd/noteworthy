# Other Modules

This guide covers the `block`, `data`, and `combi` modules.

## Import

```typst
#import "../../templates/templater.typ": *
```

## Blocks Module

The `block` module provides pre-styled environments for educational content. All blocks automatically use the active theme colors.

### Content Blocks
-   **`#definition[Title][Content]`**: For definitions.
-   **`#theorem[Title][Content]`**: For theorems.
-   **`#example[Title][Content]`**: For examples.
-   **`#note[Title][Content]`**: For side notes or remarks.
-   **`#notation[Title][Content]`**: For notation guides.
-   **`#analysis[Title][Content]`**: For analysis or breakdowns.

### Proofs & Solutions
-   **`#proof[Content]`**: Wraps proof content, often with a Q.E.D. symbol.
-   **`#solution[Content]`**: Wraps solution content.

## Data Module

The `data` module handles tabular data and visualization.

### Tables
-   **`#table-plot(...)`**: Renders a table (often used for plotting data points).
-   **`#value-table(variable: $x$, func: $y=x^2$, values: (1, 2, 3), results: (1, 4, 9))`**: Creates a function value table.
-   **`#compact-table(...)`**: A tighter table layout.
-   **`#grid-table(...)`**: Renders data in a grid.

### Data Series
-   **`data-series(name, data)`**: Creates a data object for plotting.
-   **`smooth-curve(points)`**: Interpolates points for smooth plotting.

## Combinatorics Module

The `combi` module visualizes counting problems and combinatorial structures.

### Visualizations
-   **`#draw-balls-boxes(...)`**: Visualizes balls in boxes (stars and bars).
-   **`#draw-circular-perm(...)`**: Visualizes circular permutations.
-   **`#draw-linear-perm(...)`**: Visualizes linear arrangements.
-   **`#draw-subset-vis(...)`**: Visualizes subsets/venn-like structures.
-   **`#draw-pigeonhole(...)`**: Visualizes the pigeonhole principle.
-   **`#draw-partition-vis(...)`**: Visualizes integer partitions.
-   **`#draw-counting-tree(...)`**: Visualizes decision trees for counting.
