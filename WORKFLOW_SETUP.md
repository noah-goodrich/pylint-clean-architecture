# Workflow Setup Instructions

## 1. CI Workflow (`ci.yml`)
(Automated on every Push/PR)
- Blocks merging if tests/lints fail.
- **Action**: Enable "Require status checks to pass" in Branch Protection for `main`.

## 2. Automated Release Workflow (`publish.yml`)
(Automated on Push to `main`)
- This workflow uses **Python Semantic Release** to automatically version and publish your package based on commit messages.

### Prerequisites (One-Time Setup)
1.  **Trusted Publishing**: Configure PyPI to trust this GitHub repository/environment (release).
2.  **Permissions**: Ensure Workflow permissions are Read & Write.

### Verifying Trusted Publishing
1. Go to your project on PyPI.org.
2. Navigate to **Settings > Publishing**.
3. Ensure an entry exists for this repository, pointing to the `release` environment.
4. Verify the workflow filename matches `.github/workflows/publish.yml`.

### How It Works (Conventional Commits)
To trigger a release, you must format your commit messages using the **Conventional Commits** standard:

- **Fix**: `fix: description` -> Patches the version (0.1.0 -> 0.1.1)
  - Example: `fix: resolve astroid import warning`
- **Feature**: `feat: description` -> Miner version bump (0.1.0 -> 0.2.0)
  - Example: `feat: add new W9201 check`
- **Breaking Change**: Add `BREAKING CHANGE:` in the footer or `feat!: description` -> Major version bump (0.1.0 -> 1.0.0)
- **Other**: `docs:`, `chore:`, `style:`, `test:`, `refactor:` -> No release triggered.
