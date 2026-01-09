# Code Style

Coding conventions and style guidelines for Noteworthy.

## Python

### Formatter and Linter

We use **Ruff** for both linting and formatting.

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Configuration

See `pyproject.toml`:

```toml
[tool.ruff]
line-length = 120
target-version = "py310"
```

### Style Guidelines

| Rule        | Example            |
| ----------- | ------------------ |
| Line length | 120 characters max |
| Indentation | 4 spaces           |
| Quotes      | Double quotes `"`  |
| Imports     | Sorted, grouped    |
| Docstrings  | Google style       |

### Example

```python
"""
Module docstring.
"""
import json
from pathlib import Path

from fastapi import FastAPI


def load_config(path: Path) -> dict:
    """Load configuration from JSON file.
    
    Args:
        path: Path to the config file.
        
    Returns:
        Configuration dictionary.
        
    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    
    return json.loads(path.read_text())
```

---

## Typst

### General Guidelines

| Rule        | Example                        |
| ----------- | ------------------------------ |
| Indentation | 2 spaces                       |
| Line length | No strict limit, be reasonable |
| Comments    | Use `//` for single line       |
| Functions   | Snake case: `my-function`      |

### Theme Awareness

**Never hardcode colors:**

```typst
// ❌ Bad
#let my-block(body) = block(fill: blue, body)

// ✅ Good
#let my-block(body, theme: (:)) = {
  let fill = theme.at("block-fill", default: blue)
  block(fill: fill, body)
}
```

### Module Pattern

**Implementation (impl.typ):**

```typst
// Pure function with theme parameter
#let _my-function(content, style: (:), theme: (:)) = {
  let color = theme.at("accent", default: blue)
  // Implementation
}
```

**Public API (mod.typ):**

```typst
#import "src/impl.typ": _my-function
#import "../core/setup.typ": active-theme

// Inject theme automatically
#let my-function(content, style: (:)) = {
  _my-function(content, style: style, theme: active-theme)
}
```

---

## JavaScript

### Style Guidelines

| Rule        | Example            |
| ----------- | ------------------ |
| Indentation | 2 spaces           |
| Quotes      | Single quotes `'`  |
| Semicolons  | Required           |
| Variables   | `const` by default |

### Example

```javascript
const WebSocketClient = {
  socket: null,
  
  connect(url) {
    this.socket = new WebSocket(url);
    this.socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
  },
  
  handleMessage(data) {
    switch (data.type) {
      case 'update':
        this.onUpdate(data);
        break;
      case 'cursor':
        this.onCursor(data);
        break;
    }
  }
};
```

---

## CSS

### Style Guidelines

| Rule              | Example                        |
| ----------------- | ------------------------------ |
| Indentation       | 2 spaces                       |
| Class naming      | BEM-like: `.component-element` |
| Custom properties | For theming                    |

### Example

```css
:root {
  --bg-primary: #1e1e2e;
  --text-primary: #cdd6f4;
  --accent: #89b4fa;
}

.editor-container {
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.editor-container-header {
  padding: 8px 16px;
  border-bottom: 1px solid var(--accent);
}
```

---

## Documentation

### Markdown Guidelines

| Rule        | Description        |
| ----------- | ------------------ |
| Headings    | Use `#` hierarchy  |
| Code blocks | Specify language   |
| Links       | Use relative paths |
| Tables      | Align columns      |

### Example

```markdown
# Feature Name

Brief description.

## Usage

\`\`\`python
example_code()
\`\`\`

## Parameters

| Param | Type | Description |
| ----- | ---- | ----------- |
| `foo` | str  | Does X      |
```

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type       | Purpose          |
| ---------- | ---------------- |
| `feat`     | New feature      |
| `fix`      | Bug fix          |
| `docs`     | Documentation    |
| `style`    | Formatting       |
| `refactor` | Code restructure |
| `test`     | Add tests        |
| `chore`    | Maintenance      |

### Examples

```bash
feat(gui): add dark mode toggle
fix(build): handle missing pdftk gracefully
docs: update installation guide
refactor(tui): extract menu component
```

---

## See Also

- [Development Setup](development-setup.md)
- [Pull Requests](pull-requests.md)
