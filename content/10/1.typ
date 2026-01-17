#import "../../templates/templater.typ": *


= CS Data Structures

The CS module provides visualizations for fundamental data structures like Arrays, Stacks, Queues, and Linked Lists.

== Arrays

#definition("cs-array")[
  Visualizes a contiguous array of elements with support for highlighting, pointers, and separators.

  ```typst
  cs-array(
    items: (10, 20, 30),
    highlight: (1,),
    pointers: ("0": "head"),
    separators: (1,),
    show-index: true
  )
  ```
  *Parameters:*
  - `items`: Content to display.
  - `highlight`: Indices to highlight.
  - `pointers`: Dictionary of `{index: label}`.
  - `separators`: List of indices to insert a gap after.
  - `show-index`: Toggle index visibility (default: true).
]



#canvas.blank-canvas(length: 10cm, height: 4cm, dsa.cs-array(
  (38, 27, 43, 3),
  separators: (1,),
  label: "Split Step",
))

== Stacks

#definition("cs-stack")[
  Visualizes a LIFO stack with optional push/pop animations.

  ```typst
  cs-stack(
    items: (10, 20),
    incoming: 30, // Push animation
    outgoing: 5,  // Pop animation
    show-index: false
  )
  ```
  *Parameters:*
  - `items`: Stack content (bottom to top).
  - `incoming`: Item to visualize being pushed.
  - `outgoing`: Item to visualize being popped (with arc arrow).
  - `show-index`: Show indices on the left (default: false).
]

#canvas.blank-canvas(length: 10cm, height: 6cm, dsa.cs-stack(
  (10, 20),
  outgoing: 30,
  label: "Pop Operation",
))

== Queues

#definition("cs-queue")[
  Visualizes a FIFO queue with symmetric enqueue/dequeue indicators.

  ```typst
  cs-queue(
    items: (1, 2, 3),
    incoming: 4, // Enqueue
    outgoing: 0, // Dequeue
    show-index: false
  )
  ```
  *Parameters:*
  - `items`: Queue content (front to back).
  - `incoming`: Item being enqueued (right).
  - `outgoing`: Item being dequeued (left).
  - `show-index`: Show indices below items (default: false).
]

#canvas.blank-canvas(length: 10cm, height: 4cm, dsa.cs-queue(
  (1, 2, 3),
  incoming: 4,
  label: "Enqueue",
))

== Linked Lists

#definition("cs-linked-list")[
  Visualizes a singly linked list with nodes and pointers.

  ```typst
  cs-linked-list(
    items: (12, 99),
    pointers: ("0": "head"),
    show-index: false
  )
  ```
  *Parameters:*
  - `items`: List content.
  - `pointers`: External pointers pointing to nodes.
  - `show-index`: Show indices below nodes (default: false).
]

#canvas.blank-canvas(length: 10cm, height: 4cm, dsa.cs-linked-list(
  (12, 99, 37),
  pointers: ("0": "head"),
  label: "Singly Linked List",
))
