# CHANGELOG

<!-- version list -->
## v1.6.0 (2026-01-22)

### Features
- **Typeshed Integration**: Replaced manual allow-lists with automated `typeshed-client` inference for standard library types.
- **Excelsior Auto-Fix Suite**: Implemented `excelsior fix` command to automatically resolve structural and stylistic violations (W9011, W9015, W9601).
- **Coverage Hardening**: Increased unit test coverage to 80.4%.
- **Enhanced LoD Checker**: Improved Law of Demeter (W9006) with trusted authority tracing (e.g., `re.Match`, `subprocess.CompletedProcess`).
- **Configuration Optimization**: Consolidated pytest directives into `pyproject.toml`.

### Bug Fixes
- **Fixer**: Fixed regex bug in return type hint detection.
- **Stability**: Refactored brittle unit tests to use robust mocking.

## v1.5.2 (2026-01-18)

### Bug Fixes

- I honestly don't remember
  ([`90e213c`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/90e213c4686fbdf0c77828cfb7b3f7f5b2338bf8))

### Chores

- Add MIT license
  ([`c2e5870`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/c2e5870f3b1e17da8b8bd563fac277b093059696))


## v1.5.1 (2026-01-16)

### Bug Fixes

- Broken stuff
  ([`20c8aea`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/20c8aeaa1ec2f763ba3cf51a870ea5aa309d63aa))

- **readme**: Use absolute paths for hero images
  ([`b14d78c`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/b14d78c868241ce7d6070fe7946471ebecb30e9b))


## v1.5.0 (2026-01-15)

### Bug Fixes

- **ci**: Ruff keeps breaking
  ([`2e8091b`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/2e8091b2942c503d79e01ae688d4e292445a1840))

- **ci**: Ruff keeps breaking v666
  ([`757fed9`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/757fed94b2c26934c50a7b809a956b1974bbcc27))

- **deps**: Add missing tomli-w for tests
  ([`6fe3b33`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/6fe3b33e3f3a43f727dcfc3a3d7605c61dae7eb4))

- **tests**: Remove tomli-w dependency from tests
  ([`dd8361b`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/dd8361be96ccf188f69b7fc95f3ac03b61580356))

### Chores

- Bump version to 1.4.2
  ([`a69ce7e`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/a69ce7ea750ca8e86d2462b99650414cb90e4dc8))

### Features

- **ci**: Enforce tests pass before release
  ([`c31c363`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/c31c3633715a4d0d16ecdd8cace3bcf37bf1f918))


## v1.4.1 (2026-01-15)


## v1.4.0 (2026-01-15)

### Bug Fixes

- Ci dependencies and pytest plugins
  ([`e4ee251`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/e4ee25184720ccf79dd72a75d03db3e5a1c0095b))

### Features

- Add workflow_dispatch to actions
  ([`a5ce8af`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/a5ce8af9857d3a4b2e9018ca6631f8200f4b93ef))

- Unified ui handling with shared kernel support
  ([`26dc92b`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/26dc92b43df38b066ce7f92c774e96f81288110f))


## v1.3.0 (2026-01-15)

### Features

- Branding; badges
  ([`3396103`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/33961031b37b5987139f046d6e416836ccb2c6bb))

- Implement W9012, standardize package name, and add badges
  ([`5415086`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/54150868378b4e4d0ca9c169bf9d321636394323))


## v1.2.2 (2026-01-12)

### Bug Fixes

- Final polish
  ([`7ef4f3d`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/7ef4f3de3b289721227cf6c307b890854f49e1b7))


## v1.2.1 (2026-01-12)

### Bug Fixes

- Fixing linter issues
  ([`4ed71e9`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/4ed71e9e272882fb7551f52b999db260f0fb0627))


## v1.2.0 (2026-01-11)

### Documentation

- Add project logo and update branding in README.
  ([`1ec5537`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/1ec5537867d628e39b3922aa05fbf90433bd90d2))

### Features

- Ruff; linter & test errors fixed
  ([`f9bff7f`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/f9bff7f9a9fd5e49a543669d9531e3e2f8a1e5f6))


## v1.1.2 (2026-01-10)


## v1.1.1 (2026-01-10)


## v1.1.0 (2026-01-10)

### Features

- Initial publish
  ([`ce67486`](https://github.com/noah-goodrich/pylint-clean-architecture/commit/ce6748695ad28cd76ba2e1637d9dfeed59066eb4))


## v1.0.0 (2026-01-08)

- Initial Release
