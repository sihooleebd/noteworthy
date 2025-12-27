// =====================================================
// COVERS MODULE - Main entrypoint for cover templates
// =====================================================
// Re-exports all cover types with theme binding.

#import "../../core/setup.typ": active-theme, affiliation, authors, subtitle, title

// Import raw implementations
#import "main-cover.typ": cover as cover-impl
#import "chapter-cover.typ": chapter-cover as chapter-cover-impl
#import "preface.typ": preface as preface-impl
#import "page-title.typ": project as project-impl

// =====================================================
// THEMED COVER WRAPPERS
// =====================================================

#let cover = cover-impl.with(theme: active-theme)
#let chapter-cover = chapter-cover-impl.with(theme: active-theme)
#let preface = preface-impl.with(
  theme: active-theme,
  content: include "../../../config/preface.typ",
  authors: authors,
)
#let project = project-impl.with(theme: active-theme)
