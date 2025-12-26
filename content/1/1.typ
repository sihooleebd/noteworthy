#import "../../templates/templater.typ": *

= Content Blocks Overview

Noteworthy provides 9 semantic block types for structuring educational content.

== The Block Types

=== Definition & Theorem

#definition("Limit")[
  The limit of $f(x)$ as $x$ approaches $a$ is $L$ if for every $epsilon > 0$ there exists $delta > 0$ such that $|f(x) - L| < epsilon$ whenever $0 < |x - a| < delta$.
]

#theorem("Squeeze Theorem")[
  If $g(x) <= f(x) <= h(x)$ for all $x$ near $a$, and $lim_(x -> a) g(x) = lim_(x -> a) h(x) = L$, then $lim_(x -> a) f(x) = L$.
]

=== Equation & Notation

#equation("Euler's Identity")[
  $ e^(i pi) + 1 = 0 $
]

#notation("Big-O Notation")[
  $O(n)$ denotes an upper bound on the growth rate of an algorithm.
]

=== Note & Analysis

#note("Remember")[
  Limits describe behavior as we approach a point, not necessarily at the point itself.
]

#analysis("Convergence")[
  The sequence $a_n = 1/n$ converges to 0 because for any $epsilon > 0$, choosing $N > 1/epsilon$ ensures $|a_n| < epsilon$ for all $n > N$.
]
