// =====================================================
// LAYOUTS MODULE - Main entrypoint for layout templates
// =====================================================
// Re-exports all layout types with theme binding.

#import "../../core/setup.typ": active-theme

// Import raw implementations
#import "outline.typ": outline as outline-impl

// =====================================================
// THEMED LAYOUT WRAPPERS
// =====================================================

#let outline = outline-impl.with(theme: active-theme)
