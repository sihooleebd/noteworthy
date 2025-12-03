#import "../../templates/templater.typ": *

= Content Blocks

Noteworthy provides a variety of semantic blocks to structure your educational content.

== Definitions & Theorems

#definition("Vector")[
  A *vector* is a quantity that has both magnitude and direction. It is often represented by an arrow.
]

#theorem("Pythagorean Theorem")[
  In a right-angled triangle, the square of the hypotenuse is equal to the sum of the squares of the other two sides:
  $ a^2 + b^2 = c^2 $
]

== Proofs & Solutions

#proof[
  Let $a, b$ be the lengths of the legs and $c$ be the length of the hypotenuse.
  Construct a square of side $a+b$...
  $therefore$ The area relationships confirm the theorem.
]

#example("Finding the Hypotenuse")[
  Given a right triangle with legs of length 3 and 4, find the length of the hypotenuse.
]

#solution[
  Using the Pythagorean theorem:
  $ c = sqrt(3^2 + 4^2) = sqrt(9 + 16) = sqrt(25) = 5 $
]

== Notes & Remarks

#note("Important")[
  Always remember to check the units when solving physics problems using vectors.
]

#notation("Vector Notation")[
  Vectors are typically denoted by boldface letters ($bold(v)$) or arrows ($arrow(v)$).
]

#analysis("Geometric Interpretation")[
  Geometrically, vectors can be added using the parallelogram rule or the triangle rule.
]
