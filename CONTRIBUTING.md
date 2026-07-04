# Contributing Guidelines

Thank you for your interest in contributing to **Noteworthy**!

## Quick Start

```bash
# Clone and setup
git clone https://github.com/sihooleebd/noteworthy
cd noteworthy
uv sync
source .venv/bin/activate

# Verify
noteworthy --help
uv run ruff check .
```

📖 **[Full Development Setup →](docs/contributing/development-setup.md)**

---

## Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for all contributors.

---

## Development Guides

| Guide                                                       | Description                |
| ----------------------------------------------------------- | -------------------------- |
| [Development Setup](docs/contributing/development-setup.md) | Environment setup with uv  |
| [Code Style](docs/contributing/code-style.md)               | Formatting and conventions |
| [Pull Requests](docs/contributing/pull-requests.md)         | Submission process         |

---

## Project Architecture

Understanding the codebase:

| Component              | Philosophy                                                   |
| ---------------------- | ------------------------------------------------------------ |
| **`noteworthy/core/`** | Robustness & isolation — minimal deps, defensive programming |
| **`noteworthy/tui/`**  | UX first — intuitive navigation, clear feedback              |
| **`noteworthy/gui/`**  | Modern web — FastAPI, WebSockets, real-time sync             |
| **`templates/`**       | Separation of concerns — structure vs. style                 |

📖 **[Architecture Overview →](docs/architecture/overview.md)**

---

## GUI Parity

The collaborative GUI and solo GUI intentionally mirror each other in a lot of places.

- If you change shared editor or preview UI in **`noteworthy/gui/`**, check whether the same change is needed in **`noteworthy/gui_solo/`**.
- For frontend behavior, layout, and controls, default to updating both modes together unless the feature is explicitly collaboration-only.
- When submitting a PR that touches one GUI mode but not the other, call out the reason in the PR description.

---

## Typst Conventions

We strictly separate **structure** from **style**:

- **Implementation (`impl.typ`)**: Pure logic, accepts `theme` parameter, never hardcodes colors
- **Module Interface (`mod.typ`)**: Public API, injects `active-theme`

```typst
// Implementation - pure function
#let _alert(body, theme: (:)) = {
  let color = theme.at("warning", default: yellow)
  block(fill: color, body)
}

// Public API - injects theme
#let alert(body) = _alert(body, theme: active-theme)
```

---

## Submitting Changes

1. **Fork & Branch**: `git checkout -b feature/my-feature`
2. **Test**: Run TUI, GUI, and CLI
3. **Lint**: `uv run ruff check .`
4. **Commit**: Use [conventional commits](https://www.conventionalcommits.org/)
5. **PR**: Open a pull request

---

## Security

See [SECURITY.md](SECURITY.md) for our disclosure policy.

---

**Happy Coding!** — *Sihoo & Hojun*
