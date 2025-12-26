#import "../../templates/templater.typ": *

= Proofs & Solutions

Special blocks for mathematical reasoning and worked examples.

== Proof Block

The `#proof` block automatically adds a QED symbol at the end.

#theorem("Sum of First n Integers")[
  $ sum_(k=1)^n k = (n(n+1))/2 $

  #proof[
    *Base case:* When $n = 1$: $sum_(k=1)^1 k = 1 = (1 dot 2)/2$. ✓

    *Inductive step:* Assume true for $n$. Then:
    $ sum_(k=1)^(n+1) k = sum_(k=1)^n k + (n+1) = (n(n+1))/2 + (n+1) $
    $ = (n+1)(n/2 + 1) = (n+1)(n+2)/2 $

    Thus true for $n+1$. $therefore$ By induction, the formula holds for all $n >= 1$.
  ]
]

== Example & Solution Blocks

#example("Derivative of $x^3$")[
  Find $d/(d x) x^3$ using the power rule.
  #solution[
    Using the power rule $d/(d x) x^n = n x^(n-1)$:
    $ d/(d x) x^3 = 3x^2 $
  ]
]


#example("Integration")[
  Evaluate $integral_0^2 x^2 dif x$.

  #solution[
    $ integral_0^2 x^2 dif x = [x^3/3]_0^2 = 8/3 - 0 = 8/3 $
  ]
]

