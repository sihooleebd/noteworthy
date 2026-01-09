# Quickstart

Create your first Noteworthy document in 5 minutes.

## 1. Create a Project

```bash
git clone https://github.com/sihooleebd/noteworthy myproject
cd myproject
uv sync
source .venv/bin/activate
```

## 2. Add Content

Create your first chapter and page:

```bash
mkdir -p content/1
```

Create `content/1/1.typ`:

```typst
= Introduction

Welcome to my first Noteworthy document!

== Getting Started

This is a section within the introduction chapter.

#lorem(50)
```

## 3. Configure Metadata

Edit `config/metadata.json`:

```json
{
  "title": "My First Document",
  "subtitle": "A Noteworthy Tutorial",
  "authors": ["Your Name"],
  "affiliation": "Your Organization"
}
```

## 4. Build with Noteworthy Studio

Launch the web interface:

```bash
noteworthy -g
```

Open http://localhost:8000 in your browser.

1. Navigate to the **Build** tab
2. Select your chapter in the grid
3. Click **Build**
4. Download `output.pdf`

## 5. Build with TUI

Or use the terminal interface:

```bash
noteworthy
```

- Use arrow keys to navigate
- Press `b` for build menu
- Press `Space` to select pages
- Press `Enter` to build

## 6. Build with CLI

For scripted builds:

```bash
python noteworthy_cli.py
```

Or build specific chapters:

```bash
python noteworthy_cli.py -c 0  # First chapter only
```

---

## What's Next?

| Guide                                               | Description                |
| --------------------------------------------------- | -------------------------- |
| [Project Structure](project-structure.md)           | Understand the file layout |
| [Content Authoring](../guides/content-authoring.md) | Write better Typst content |
| [Theming](../guides/theming.md)                     | Customize the look         |
| [Building](../guides/building.md)                   | Advanced build options     |
