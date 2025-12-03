#import "../../templates/templater.typ": *

= Function Graphs

Plot mathematical functions easily.

== Cartesian Functions

#rect-plot({
  plot-function(x => x * x - 2, type: "y=x", label: $y = x^2 - 2$)
})

== Parametric Functions

#rect-plot({
  plot-function(t => (calc.cos(t), calc.sin(t)), type: "parametric", label: "Circle")
})

== Polar Functions

#rect-plot({
  plot-function(t => 1 + calc.cos(t), type: "polar", label: "Cardioid")
})
