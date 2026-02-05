"""Stub Creator: Generate .pyi stubs via mypy stubgen and wire into project config. No top-level functions (W9018)."""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from clean_architecture_linter.domain.protocols import StubCreatorProtocol

W9019_MODULE_RE = re.compile(
    r"Dependency\s+([^\s]+)\s+is\s+uninferable", re.IGNORECASE)


class StubCreatorService(StubCreatorProtocol):
    """Implements StubCreatorProtocol. No top-level functions (W9018)."""

    def extract_w9019_modules(self, linter_results: list) -> set[str]:
        """Extract unique module names from W9019 (clean-arch-unstable-dep) results."""
        modules: set[str] = set()
        for r in linter_results:
            code = getattr(r, "code", None)
            message = getattr(r, "message", "") or ""
            if code == "W9019" and message:
                m = W9019_MODULE_RE.search(message)
                if m:
                    modules.add(m.group(1).strip())
        return modules

    def create_stub(
        self,
        module: str,
        project_root: str,
        *,
        use_stubgen: bool = True,
        overwrite: bool = False,
    ) -> tuple[bool, str]:
        """Create a .pyi stub for the given module under project_root/stubs/. Returns (success, message)."""
        root = Path(project_root).resolve()
        stubs_dir = root / "stubs"
        rel_path = module.replace(".", "/") + ".pyi"
        stub_path = stubs_dir / rel_path

        if stub_path.exists() and not overwrite:
            return (False, "exists")

        stub_path.parent.mkdir(parents=True, exist_ok=True)

        if use_stubgen:
            ok, msg = self._run_stubgen(module, stubs_dir, stub_path)
            if ok:
                return (True, msg)

        content = (
            f"# Stub for {module}. Add types as needed.\n"
            "# Consider: pip install types-<pkg> or typeshed.\n\n"
            "def __getattr__(name: str): ...\n"
        )
        stub_path.write_text(content, encoding="utf-8")
        self._ensure_mypy_path_includes_stubs(root)
        return (True, "minimal")

    def _run_stubgen(
        self, module: str, stubs_dir: Path, final_stub_path: Path
    ) -> tuple[bool, str]:
        """Run mypy stubgen for module; write output into stubs_dir."""
        with tempfile.TemporaryDirectory(prefix="excelsior_stubgen_") as tmp:
            out_dir = Path(tmp)
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "mypy.stubgen",
                        "-m",
                        module,
                        "-o",
                        str(out_dir),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                return (False, str(e))
            if result.returncode != 0:
                return (False, result.stderr or result.stdout or "stubgen failed")
            parts = module.split(".")
            generated = out_dir
            for part in parts:
                generated = generated / part
            generated_pyi = generated.with_suffix(".pyi")
            if not generated_pyi.exists():
                return (False, "stubgen produced no .pyi")
            content = generated_pyi.read_text(encoding="utf-8")
            final_stub_path.parent.mkdir(parents=True, exist_ok=True)
            final_stub_path.write_text(content, encoding="utf-8")
        self._ensure_mypy_path_includes_stubs(stubs_dir.parent)
        return (True, "stubgen")

    def _ensure_mypy_path_includes_stubs(self, project_root: Path) -> None:
        """Ensure [tool.mypy] mypy_path in pyproject.toml includes 'stubs'."""
        pyproject = project_root / "pyproject.toml"
        if not pyproject.exists():
            return
        text = pyproject.read_text(encoding="utf-8")
        if "[tool.mypy]" not in text:
            pyproject.write_text(
                text.rstrip() + '\n[tool.mypy]\nmypy_path = "stubs"\n',
                encoding="utf-8",
            )
            return
        if "mypy_path" not in text:
            text = text.replace(
                "[tool.mypy]", '[tool.mypy]\nmypy_path = "stubs"', 1)
            pyproject.write_text(text, encoding="utf-8")
            return
        # Append stubs to existing mypy_path (mypy pathsep-separated string)
        match = re.search(r'mypy_path\s*=\s*["\']([^"\']*)["\']', text)
        if not match:
            return
        current = match.group(1).strip()
        if "stubs" in current.split(os.pathsep):
            return
        new_value = current + os.pathsep + "stubs"
        new_text = text[: match.start(1)] + new_value + text[match.end(1):]
        pyproject.write_text(new_text, encoding="utf-8")
