#import "../../templates/templater.typ": *

= Layout Elements

This section demonstrates various layout utilities available in Noteworthy.

== Equations

#equation("Maxwell's Equations")[
  $
      nabla dot vec(E) & = rho / epsilon_0 \
      nabla dot vec(B) & = 0 \
    nabla times vec(E) & = - partial vec(B) / partial t \
    nabla times vec(B) & = mu_0 vec(J) + mu_0 epsilon_0 partial vec(E) / partial t
  $
]

== Conditional Content

Noteworthy supports conditional rendering based on the `show-solution` configuration.

#if show-solution [
  #note("Instructor's Note")[
    This content is only visible when `show-solution` is set to `true` in `config.typ`.
  ]
]

== Custom Snippets

You can define custom math snippets in `config.typ` for faster typing.

$
  st \
  wlog \
  qed
$
