# Workflow Setup Instructions

## 1. CI Workflow (`ci.yml`)
(Automated on every Push/PR)
- Blocks merging if tests/lints fail.
- **Action**: Enable "Require status checks to pass" in Branch Protection for `main`.

## 2. Automated Release Workflow (`publish.yml`)
(Automated on Push to `main`)
- This workflow uses **Python Semantic Release** to automatically version and publish your package based on commit messages.

### Prerequisites (One-Time Setup)
1.  **PyPI Token**: Add `PYPI_API_TOKEN` to Repository Secrets.
2.  **Permissions**: Ensure Workflow permissions are Read & Write.

### How It Works (Conventional Commits)
To trigger a release, you must format your commit messages using the **Conventional Commits** standard:

- **Fix**: `fix: description` -> Patches the version (0.1.0 -> 0.1.1)
  - Example: `fix: resolve astroid import warning`
- **Feature**: `feat: description` -> Miner version bump (0.1.0 -> 0.2.0)
  - Example: `feat: add new W9201 check`
- **Breaking Change**: Add `BREAKING CHANGE:` in the footer or `feat!: description` -> Major version bump (0.1.0 -> 1.0.0)
- **Other**: `docs:`, `chore:`, `style:`, `test:`, `refactor:` -> No release triggered.

**Workflow process:**
1.  You merge a PR with a `feat: ...` commit into `main`.
2.  The `release` workflow starts.
3.  It analyzes commits since the last tag.
4.  It calculates the next version.
5.  It updates `pyproject.toml`, commits, tags, and pushes back to GitHub.
6.  It builds and upload to PyPI automatically.
