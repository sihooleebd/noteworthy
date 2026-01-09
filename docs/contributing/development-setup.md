# Development Setup

Set up your development environment for contributing to Noteworthy.

## Prerequisites

| Tool       | Version | Purpose         |
| ---------- | ------- | --------------- |
| **Python** | 3.10+   | Runtime         |
| **uv**     | Latest  | Package manager |
| **Typst**  | 0.12+   | Compiler        |
| **Git**    | Latest  | Version control |

---

## Clone the Repository

```bash
git clone https://github.com/sihooleebd/noteworthy
cd noteworthy
```

---

## Install Dependencies

```bash
# Install all dependencies including dev tools
uv sync

# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
# or: .venv\Scripts\activate  # Windows
```

This installs:
- Runtime: `fastapi`, `uvicorn`
- Dev: `pytest`, `ruff`

---

## Verify Setup

```bash
# Check CLI works
noteworthy --help

# Run linter
uv run ruff check .

# Run tests
uv run pytest
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

Edit files in:
- `noteworthy/` — Python code
- `templates/` — Typst templates
- `docs/` — Documentation

### 3. Test Changes

```bash
# Test TUI
noteworthy

# Test Noteworthy Studio
noteworthy -g

# Test CLI
python noteworthy_cli.py -c 0
```

### 4. Lint and Format

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### 5. Commit

```bash
git add .
git commit -m "feat: add my feature"
```

---

## Project Structure

```
noteworthy/
├── noteworthy/          # Python package
│   ├── core/            # Build engine
│   ├── tui/             # Terminal UI
│   └── gui/             # Web GUI
├── templates/           # Typst templates
├── docs/                # Documentation
├── tests/               # Test files
├── pyproject.toml       # Project config
└── uv.lock              # Lockfile
```

---

## Common Tasks

### Add a Dependency

```bash
uv add <package>
```

### Add a Dev Dependency

```bash
uv add --dev <package>
```

### Update Dependencies

```bash
uv sync --upgrade
```

### Run Specific Tests

```bash
uv run pytest tests/test_build.py -v
```

---

## IDE Setup

### VS Code

Recommended extensions:
- Python (Microsoft)
- Ruff
- Typst LSP

`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "ruff.enable": true,
  "editor.formatOnSave": true
}
```

### PyCharm

1. Open project
2. Set interpreter to `.venv/bin/python`
3. Enable Ruff plugin

---

## Troubleshooting

### "Module not found"

Ensure venv is activated:
```bash
source .venv/bin/activate
```

### Typst errors

Check Typst is in PATH:
```bash
typst --version
```

### Permission denied

Fix script permissions:
```bash
chmod +x noteworthy.py
```

---

## Next Steps

- [Code Style Guide](code-style.md)
- [Pull Request Guide](pull-requests.md)
- [Architecture Overview](../architecture/overview.md)
