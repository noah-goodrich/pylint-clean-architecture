# Stellar Pre-Flight Checklist
You MUST complete this checklist for EVERY file changed before proceeding.

1.  **Handshake**: `make handshake` (Confirming compliance).
2.  **Audit**: `excelsior check` or `make verify-file FILE=<file_path>`.
3.  **Complexity**: Ruff C901 score must be <= 11.
4.  **Coverage**: Minimum 85% coverage on new logic.
5.  **Integrity**: Mypy --strict must return 0 errors.
6.  **Self-Audit**: Pylint score MUST be 10.0/10.
