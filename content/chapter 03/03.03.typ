#import "../../templates/templater.typ": *

= Tables

Themed tables for data presentation.

== Standard Table

#table-plot(
  headers: ("Name", "Role", "Level"),
  data: (
    ("Alice", "Engineer", "Senior"),
    ("Bob", "Designer", "Mid"),
    ("Charlie", "Manager", "Lead"),
  ),
)

== Compact Table

#compact-table(
  headers: ("ID", "Status"),
  data: (
    ("001", "OK"),
    ("002", "Fail"),
    ("003", "OK"),
  ),
)

== Value Table (Function Values)

#value-table(
  variable: $x$,
  values: ("1", "2", "3"),
  func: $f(x)$,
  results: ("2", "4", "8"),
)

== Grid Table

#grid-table(
  data: (
    ("100", "120"),
    ("110", "130"),
  ),
)
