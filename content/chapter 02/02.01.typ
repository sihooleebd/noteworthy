#import "../../templates/templater.typ": *

= Basic Plots

Noteworthy includes a powerful plotting engine based on CeTZ.

== Rectangular Plots

#rect-plot(
  x-domain: (-2, 2),
  y-domain: (-2, 2),
  {
    point((0, 0), "Origin")
    point((1, 1), "A", color: red)
    point((-1, 1), "B", color: blue)
  },
)

== Polar Plots

#polar-plot(
  radius: 3,
  {
    add-polar(t => 2 * calc.sin(3 * t))
  },
)

== Blank Plots (Combi-plot)

Useful for diagrams without axes.

#combi-plot({
  draw-circular(("A", "B", "C"), radius: 1.5)
})
