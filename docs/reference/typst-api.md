# Typst API Reference

Reference for Typst functions exported by Noteworthy.

## Importing

All functions are available after importing the templater:

```typst
#import "../../templates/templater.typ": *
```

---

## Blocks

Educational content containers.

### definition

```typst
#definition(title)[body]
```

| Parameter | Type    | Description        |
| --------- | ------- | ------------------ |
| `title`   | string  | Term being defined |
| `body`    | content | Definition content |

### theorem

```typst
#theorem(title)[body]
```

### lemma

```typst
#lemma(title)[body]
```

### corollary

```typst
#corollary(title)[body]
```

### proof

```typst
#proof[body]
```

### example

```typst
#example(title)[body]
```

### solution

```typst
#solution[body]
```

> [!TIP]
> Nest `#solution` inside `#example` for problem/solution pairs.

### exercise

```typst
#exercise(title)[body]
```

### remark

```typst
#remark[body]
```

### note

```typst
#note[body]
```

### warning

```typst
#warning[body]
```

---

## Canvas

Drawing functions. Require the canvas module.

### canvas

```typst
#canvas(body, ..args)
```

Creates a drawing canvas.

| Parameter | Type    | Description            |
| --------- | ------- | ---------------------- |
| `body`    | content | Drawing commands       |
| `width`   | length  | Canvas width           |
| `height`  | length  | Canvas height          |
| `padding` | length  | Padding around content |

### point

```typst
point(pos, label: none, style: (:))
```

| Parameter | Type    | Description          |
| --------- | ------- | -------------------- |
| `pos`     | tuple   | `(x, y)` coordinates |
| `label`   | content | Label text           |
| `style`   | dict    | Style overrides      |

### vector

```typst
vector(from, to, label: none, style: (:))
```

### segment

```typst
segment(from, to, label: none, style: (:))
```

### line-infinite

```typst
line-infinite(p1, p2, label: none, style: (:))
```

### circle-obj

```typst
circle-obj(center, radius, label: none, style: (:))
```

### polygon-obj

```typst
polygon-obj(..points, label: none, style: (:))
```

### arc-obj

```typst
arc-obj(center, radius, start, end, label: none, style: (:))
```

### angle

```typst
angle(p1, vertex, p2, label: none, style: (:))
```

---

## Graph

Function plotting. Requires the graph module.

### plot-graph

```typst
#plot-graph(body, domain: (-5, 5), ..args)
```

| Parameter  | Type    | Description          |
| ---------- | ------- | -------------------- |
| `body`     | content | Plot commands        |
| `domain`   | tuple   | `(min, max)` x-range |
| `y-domain` | tuple   | `(min, max)` y-range |
| `width`    | length  | Plot width           |
| `height`   | length  | Plot height          |

### plot-func

```typst
plot-func(f, domain: auto, label: none, style: (:))
```

| Parameter | Type     | Description       |
| --------- | -------- | ----------------- |
| `f`       | function | `x => y` function |
| `domain`  | tuple    | Override domain   |
| `label`   | content  | Legend label      |

### plot-parametric

```typst
plot-parametric(fx, fy, domain: (0, 1), label: none, style: (:))
```

### plot-polar

```typst
plot-polar(r, domain: (0, 2*pi), label: none, style: (:))
```

### plot-implicit

```typst
plot-implicit(f, domain: auto, label: none, style: (:))
```

Plots `f(x, y) = 0` implicitly.

---

## Geometry

Geometric constructions. Requires the geometry module.

### midpoint

```typst
midpoint(p1, p2, label: none)
```

### perpendicular

```typst
perpendicular(line, point, label: none)
```

### parallel

```typst
parallel(line, point, label: none)
```

### intersection

```typst
intersection(obj1, obj2, label: none)
```

### tangent

```typst
tangent(circle, point, label: none)
```

---

## DSA

Data structure visualizations. Requires the DSA module.

### stack-viz

```typst
#stack-viz(items, highlight: none)
```

### queue-viz

```typst
#queue-viz(items, highlight: none)
```

### array-viz

```typst
#array-viz(items, indices: true, highlight: none)
```

### linked-list

```typst
#linked-list(items, circular: false)
```

---

## Trees

Tree visualizations. Requires the trees module.

### tree

```typst
#tree(root)
```

### tree-node

```typst
#tree-node(value, children: ())
```

---

## See Also

- [Canvas Module](../modules/canvas.md)
- [Graph Module](../modules/graph.md)
- [DSA Module](../modules/dsa.md)
