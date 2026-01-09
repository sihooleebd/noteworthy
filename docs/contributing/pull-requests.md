# Pull Requests

Guide to submitting pull requests to Noteworthy.

## Before You Start

1. **Check existing issues** — Is there an open issue for this?
2. **Discuss major changes** — Open an issue first for big features
3. **Read the code style guide** — [Code Style](code-style.md)

---

## Workflow

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR-USERNAME/noteworthy
cd noteworthy
git remote add upstream https://github.com/sihooleebd/noteworthy
```

### 2. Create a Branch

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/bug-description
```

**Branch naming:**
- `feature/` — New functionality
- `fix/` — Bug fixes
- `docs/` — Documentation
- `refactor/` — Code improvements

### 3. Make Changes

Follow the [code style guide](code-style.md).

### 4. Test Your Changes

```bash
# Lint
uv run ruff check .

# Test TUI
noteworthy

# Test Noteworthy Studio
noteworthy -g

# Test CLI
python noteworthy_cli.py
```

### 5. Commit

Use [conventional commits](https://www.conventionalcommits.org/):

```bash
git add .
git commit -m "feat(gui): add theme preview"
```

### 6. Push

```bash
git push origin feature/my-feature
```

### 7. Create Pull Request

1. Go to your fork on GitHub
2. Click **Compare & pull request**
3. Fill out the PR template
4. Submit!

---

## PR Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactor

## Testing

How did you test this?

## Checklist

- [ ] My code follows the style guidelines
- [ ] I have tested my changes
- [ ] I have updated documentation (if needed)
- [ ] My changes don't break existing functionality
```

---

## Review Process

1. **Maintainer review** — We'll review within a few days
2. **Feedback** — We may request changes
3. **Approval** — Once approved, we'll merge
4. **Release** — Changes go into next release

---

## Tips for Good PRs

### Keep It Focused

One feature/fix per PR. Don't mix unrelated changes.

### Small Is Beautiful

Smaller PRs are:
- Easier to review
- Faster to merge
- Less likely to conflict

### Include Context

Explain **why** you made changes, not just what.

### Update Docs

If you changed user-facing behavior, update:
- `README.md`
- Relevant docs in `docs/`
- Docstrings

### Add Tests

If possible, add tests for new functionality.

---

## After Merge

### Stay Updated

```bash
git checkout master
git fetch upstream
git merge upstream/master
git push origin master
```

### Delete Branch

```bash
git branch -d feature/my-feature
git push origin --delete feature/my-feature
```

---

## Getting Help

- **Discord**: [Join our community](https://discord.gg/W3S2UQCJzM)
- **Issues**: Open a GitHub issue
- **Discussions**: Use GitHub Discussions

---

## See Also

- [Development Setup](development-setup.md)
- [Code Style](code-style.md)
- [Architecture Overview](../architecture/overview.md)
