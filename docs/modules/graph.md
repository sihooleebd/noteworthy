# Graph Module

The `graph` module provides powerful tools for plotting mathematical functions and visualizing calculus concepts. It is designed to handle complex functions with singularities and high-frequency oscillations robustly.

## Import

```typst
#import "../../templates/templater.typ": *
```

## Function Plotting

### `graph` / `func`
The primary function for plotting $y = f(x)$.
```typst
#graph(
  x => calc.sin(x) / x, 
  domain: (-10, 10),
  label: "sinc(x)",
  adaptive: true // Enable robust sampling
)
```

- **`adaptive` (default: true)**: Uses a recursive adaptive sampling algorithm to detect curvature and singularities. It can render difficult functions like $\sin(1/x)$ without aliasing artifacts.
- **`hole` / `filled-hole`**: (Experimental) Options to mark specific points as open or closed holes.

### `parametric`
Plots parametric curves defined as $t \mapsto (x(t), y(t))$.
```typst
#parametric(
  t => (calc.cos(t), calc.sin(t)),
  domain: (0, 2*calc.pi),
  label: "Circle"
)
```

### `polar-func`
Plots polar curves defined as $\theta \mapsto r(\theta)$.
```typst
#polar-func(
  t => 1 + calc.cos(t), // Cardioid
  domain: (0, 2*calc.pi)
)
```

## Calculus Visualizations

The module includes helpers to visualize derivatives and integrals.

### `draw-tangent`
Draws a tangent line to a function $f(x)$ at point $x_0$.
```typst
#draw-tangent(
  f, 
  x: 1.5, 
  length: 2, 
  style: (stroke: red)
)
```

### `draw-area-under-curve`
Highlights the area under $f(x)$ between $a$ and $b$.
```typst
#draw-area-under-curve(
  f, 
  start: 0, 
  end: calc.pi, 
  fill: blue.transparentize(80%)
)
```

### `draw-riemann-sums`
Visualizes Riemann sums (rectangles) for approximating integrals.
```typst
#draw-riemann-sums(
  f, 
  start: 0, 
  end: 2, 
  n: 5, 
  mode: "left" // "left", "right", "mid", "lower", "upper"
)
```
- **`mode`**: Controls how the rect height is determined.

## Advanced Features

### Robust Adaptive Sampling
The plotting engine uses a custom adaptive sampling algorithm:
1.  **Curvature Detection**: Recursively subdivides segments where the function curves sharply.
2.  **Singularity Handling**: Detects steep slopes near asymptotes and "bleeds" the edges to show vertical asymptotes or dense oscillations (like $\sin(\pi/x)$) correctly without connecting disjoint branches.
