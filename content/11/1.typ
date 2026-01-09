#import "../../templates/templater.typ": *
#import "../../templates/module/timeline/mod.typ": *

= Timeline Module

The timeline module creates visual timelines for chronological events, processes, and milestones.

== Basic Usage

Create events with `event()` and display with `timeline-figure()`:

#timeline-figure((
  event("1969", "Moon Landing"),
  event("1989", "Fall of Berlin Wall"),
  event("2000", "Y2K"),
))

== With Descriptions

Add descriptions for more context:

#timeline-figure((
  event("1776", "Declaration of Independence", description: "13 colonies declare freedom"),
  event("1789", "Constitution Ratified", description: "Bill of Rights added 1791"),
  event("1861", "Civil War Begins", description: "Lasted until 1865"),
))

== Highlighting Events

Mark important events with `highlight: true`:

#timeline-figure((
  event("Phase 1", "Research"),
  event("Phase 2", "Development", highlight: true),
  event("Phase 3", "Testing"),
  event("Phase 4", "Launch"),
))

== Horizontal Layout

Use `direction: "horizontal"` for compact display:

#timeline-figure(
  (
    event("Jan", "Start"),
    event("Mar", "Milestone 1"),
    event("Jun", "Milestone 2"),
    event("Dec", "Complete"),
  ),
  direction: "horizontal",
)
