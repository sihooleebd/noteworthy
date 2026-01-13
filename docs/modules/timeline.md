# Timeline Module

The `timeline` module provides tools for creating vertical or horizontal timelines, commonly used for history, project management, or sequence visualization.

## Import

```typst
#import "../../templates/templater.typ": *
```

## Data Types

### Event Object

Create an event using the `event` constructor.

```typst
event(
  date,             // Date/Time label (string or content)
  title,            // Event title
  description: none,// Optional detailed description
  highlight: false, // Whether to visually highlight this event
)
```

### Timeline Object

Wrap events in a `timeline` object.

```typst
timeline(
  events,               // Array of event objects
  direction: "vertical",// "vertical" or "horizontal"
  style: (:),           // Style dictionary overrides
)
```

## Functions

### `draw-timeline`

Renders a timeline on a canvas.

```typst
#draw-timeline(my-timeline)
```

### `timeline-figure`

A high-level wrapper that renders the timeline as a self-contained figure with a caption.

```typst
#timeline-figure(
  events, 
  caption: "Project Milestones", 
  direction: "vertical"
)
```

## Example

```typst
#let events = (
  event("2020", "Inception", description: "Project started"),
  event("2021", "Alpha", highlight: true),
  event("2022", "Beta", description: "Public testing"),
  event("2023", "Release", description: "v1.0 Launch"),
)

#timeline-figure(events, caption: "Development History")
```
