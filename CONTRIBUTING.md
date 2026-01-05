# Contributing Guidelines

Thank you for your interest in contributing to **Noteworthy**! This project is a complex ecosystem spanning Python tooling, Typst templating, and user interfaces. 

## Code of Conduct

We are committed to providing a friendly, safe and welcoming environment for all, regardless of level of experience, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, nationality, or other similar characteristic.

## Development Philosophies

Different parts of the Noteworthy codebase follow different design philosophies. Understanding these is crucial for your contribution to be accepted.

### 1. The Core Infrastructure (`noteworthy/core/`)
**Philosophy: Robustness & Isolation**

The core Python logic handles the heavy lifting of build automation, PDF processing, and file management.
- **Dependency Isolation**: Core modules should have minimal external dependencies.
- **Defensive Programming**: Assume user input is messy. Use robust error handling.
- **Performance**: Builds should be fast. Optimize large file operations.

### 2. The TUI & CLI (`noteworthy/tui/`, `noteworthy_cli.py`)
**Philosophy: UX First & Accessibility**

These are the primary touchpoints for the user.
- **Intuitive Navigation**: Keybindings should follow standard patterns (Arrow keys + Vim bindings).
- **Clear Feedback**: Every action must have immediate visual feedback.
- **Aesthetics**: The TUI should look polished. Use color and spacing intentionally.
- **Parity**: The CLI should mirror TUI capabilities where possible (e.g., using shared `noteworthy/utils.py`).

### 3. Typst Templates (`templates/`)
**Philosophy: Separation of Concerns**

We strictly separate **structure** from **style**.
- **Implementation (`impl.typ`)**: Pure logic and default styling. Accepts a `theme` parameter but never hardcodes color values (e.g., use `theme.primary` not `red`). 
- **Module Interface (`mod.typ`)**: The public-facing API. It injects the `active-theme` into the implementation functions.
- **Setup (`examples.typ`)**: Clear, minimal examples of usage.

**Example Flow:**
1. Write logic in `impl.typ`: `#let alert(body, theme: (:)) = block(fill: theme.at("warning", default: yellow), body)`
2. Export in `mod.typ`: `#import "impl.typ": alert as _alert` -> `#let alert(body) = _alert(body, theme: active-theme)`

### 4. Themes (`templates/themes/`)
**Philosophy: Coherence & Flexibility**

Themes define the visual soul of a document.
- **Standard Keys**: All themes must implement the core color keys (`primary`, `secondary`, `accent`, `background`, `text`).
- **Scalability**: Designs should look good on both 100-page textbooks and 5-page notes.

## Submitting Pull Requests

1. **Fork & Branch**: Create a descriptive feature branch (e.g., `feature/inverted-grid`).
2. **Test Locally**: 
   - Run the TUI: `python3 noteworthy.py`
   - Run the CLI: `python3 noteworthy_cli.py -c 0`
   - Test builds: `python3 noteworthy.py -u -f` (if testing updater logic)
3. **Draft PR**: Open a draft PR early if you need feedback.
4. **Documentation**: Update `docs/` and `README.md` if you changed user-facing features.

## Security

Please see existing [SECURITY.md](SECURITY.md) for our disclosure policy.

---
**Happy Coding!** - *Sihoo & Hojun*
