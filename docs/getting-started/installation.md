# Installation

This guide covers installing Noteworthy and its dependencies.

## Prerequisites

Before installing Noteworthy, ensure you have:

### Required

| Dependency | Version | Purpose                |
| ---------- | ------- | ---------------------- |
| **Python** | 3.10+   | Build system runtime   |
| **Typst**  | 0.12+   | Document compiler      |
| **uv**     | Latest  | Python package manager |

### PDF Tools (for merging & metadata)

| Tool        | macOS                     | Linux                       | Windows                                                                |
| ----------- | ------------------------- | --------------------------- | ---------------------------------------------------------------------- |
| **Poppler** | `brew install poppler`    | `apt install poppler-utils` | [Download](https://github.com/oschwartz10612/poppler-windows/releases) |
| **pdftk**   | `brew install pdftk-java` | `apt install pdftk`         | [Download](https://www.pdflabs.com/tools/pdftk-the-pdf-toolkit/)       |

> [!NOTE]
> `pdftk` is required for PDF bookmarks and metadata. Ghostscript is used as a fallback for merging only.

---

## Install uv

uv is a fast Python package manager. Install it first:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify installation:

```bash
uv --version
```

---

## Install Typst

```bash
# macOS
brew install typst

# Linux (Cargo)
cargo install typst-cli

# Or download from https://github.com/typst/typst/releases
```

Verify:

```bash
typst --version
```

---

## Install Noteworthy

### Option 1: Bootstrap Script (Recommended)

```bash
mkdir myproject && cd myproject
mkdir content
curl -O https://raw.githubusercontent.com/sihooleebd/noteworthy/master/noteworthy.py
python3 noteworthy.py
```

This downloads the full framework on first run.

### Option 2: Clone Repository (For Development)

```bash
# Clone the repository
git clone https://github.com/sihooleebd/noteworthy myproject
cd myproject

# Install dependencies
uv sync

# Activate the environment
source .venv/bin/activate  # macOS/Linux
# or: .venv\Scripts\activate  # Windows

# Verify
noteworthy --help
```

---

## Verify Installation

Run the help command to confirm everything works:

```bash
noteworthy --help
```

You should see:

```
usage: noteworthy [-h] [--print-inputs] [-g] [-p PORT] [-u] [-n] [-f] ...

Noteworthy Launcher

options:
  -g, --gui       Launch Noteworthy Studio
  -u, --update    Update noteworthy
  ...
```

---

## Next Steps

- [Quickstart Guide →](quickstart.md)
- [Project Structure →](project-structure.md)
