// =====================================================
// BLOCKS MODULE - Main entrypoint for block templates
// =====================================================
// Re-exports all block types with theme binding.

#import "../../core/setup.typ": active-theme

// Import raw implementations
#import "block.typ": create-block, create-proof, create-solution

// =====================================================
// THEMED BLOCK WRAPPERS
// =====================================================

#let definition = create-block.with(active-theme.blocks.definition)
#let equation = create-block.with(active-theme.blocks.equation)
#let example = create-block.with(active-theme.blocks.example)
#let note = create-block.with(active-theme.blocks.note)
#let notation = create-block.with(active-theme.blocks.notation)
#let analysis = create-block.with(active-theme.blocks.analysis)
#let theorem = create-block.with(active-theme.blocks.theorem)
#let solution = create-solution.with(active-theme.blocks.solution)
#let proof = create-proof.with(active-theme.blocks.proof)
