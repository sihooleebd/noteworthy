#import "../../templates/templater.typ": *

= Layout & Equations

Named equations and layout helpers.

== Named Equations

Use `#equation` for important equations that deserve highlighting:

#equation("Quadratic Formula")[
  $ x = (-b plus.minus sqrt(b^2 - 4a c)) / (2a) $
]

#equation("Maxwell's Equations")[
  $
      nabla dot bold(E) & = rho / epsilon_0 \
      nabla dot bold(B) & = 0 \
    nabla times bold(E) & = -partial bold(B) / partial t \
    nabla times bold(B) & = mu_0 bold(J) + mu_0 epsilon_0 partial bold(E) / partial t
  $
]

#equation("Schrödinger Equation")[
  $ i planck partial / (partial t) Psi = hat(H) Psi $
]

== Combining Blocks

Blocks work naturally together:

#definition("Eigenvalue")[
  A scalar $lambda$ is an eigenvalue of matrix $bold(A)$ if $bold(A) bold(v) = lambda bold(v)$ for some non-zero vector $bold(v)$.
]

#equation("Characteristic Equation")[
  $ det(bold(A) - lambda bold(I)) = 0 $
]

#example("2×2 Eigenvalues")[
  Find eigenvalues of $mat(3, 1; 0, 2)$.

  #solution[
    $ det mat(3-lambda, 1; 0, 2-lambda) = (3-lambda)(2-lambda) = 0 $
    Thus $lambda = 3$ or $lambda = 2$.
  ]

]
