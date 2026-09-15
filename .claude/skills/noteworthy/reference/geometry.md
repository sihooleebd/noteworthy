# shape — geometry

Every point-built shape takes `(x, y)` or `(x, y, z)`; in a space canvas two
components lie on the ground plane and three are in space.

## Primitives

```typst
point(x, y, z: none, label:, label-anchor:, style:, label-padding: 0.2)
point-3d(x, y, z, ...)   point-polar(r, theta, ...)
segment(p1, p2, label:, style:)      line(p1, p2)      ray(origin, through)
line-through-direction(p, dx, dy)    line-point-slope(p, m)
polyline(..points, close: false, label:, style:)
polygon(..points, fill:, label:, style:)   triangle(p1, p2, p3)
rectangle(corner, width, height)   square(center, side)
regular-polygon(center, first-vertex, n)
circle(center, radius: r)   circle-through(p1, p2, p3)
arc(center, p1, p2)         arc(center, start-angle, stop-angle, radius: r)
semicircle(center, start-point)
brace(from, to, label:, amplitude: 0.4, angle: auto, label-offset: 0.35)
text-at(pos, body, anchor: "center", color:, angle: 0deg, padding:, fill:, frame:)
```

`arc` and `angle` take **either** points **or** angles. Angles are literal: the
sweep runs counterclockwise from the first to the second, so `0deg` to `300deg`
is the 300° one.

```typst
angle(p1, vertex, p2, radius: 0.5, fill:, label:, reflex: "auto")
angle(0deg, vertex, 60deg, radius: 2.5, fill: ..)      // same thing, by angle
right-angle(p1, vertex, p2, radius: 0.3)
angle-between-lines(l1, l2)
```

`label: "{angle}"` substitutes the measured angle in degrees; `"{length}"` does
the same for a segment or vector.

## Measuring and constructing

```typst
distance(p1, p2)   midpoint(..)   divide-segment(seg, n)   point-on-segment(seg, t)
angle-measure(ang) angle-start(ang) angle-end(ang)         // radians, from +x
perpendicular(line, through)   parallel(line, through)   perpendicular-bisector(seg)
bisector(p1, vertex, p2)       tangent-at(circ, at)       tangent-from(circ, external)
reflect-point / rotate-point / translate-point / scale-point
circumference(circ)  circle-area(circ)  polygon-area / -perimeter / -centroid
point-at-angle(center, angle, radius, from: none)   circle-point-at(circ, angle)
polar-to-cartesian(r, theta)   cartesian-to-polar(x, y)
```

`calc.atan2` in Typst takes **x first**. Every angle helper here already accounts
for it; new code must too.

## Intersections

```typst
intersect(obj1, obj2)                    // dispatches on kind
intersect-ll(l1, l2, label:)             // -> a point
intersect-lc(line, circ, labels:)        // -> an array of points
intersect-cc(c1, c2, labels:)
```

Array results drop straight into a canvas; the canvases walk arrays.

## Braces

A brace stands beside what it measures, offset by `amplitude`. `angle:` is a
direction on the page — `0deg` right, `90deg` up — and the brace goes to
whichever of its two sides points that way, **measured after projection**. That
is the only way to say which side you meant when a camera is involved.
