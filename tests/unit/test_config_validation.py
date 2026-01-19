import tempfile
from pathlib import Path

import pytest

from clean_architecture_linter.config import ConfigurationLoader


def test_config_validation_penalty():
    """Providing a bare name in pyproject.toml triggers a configuration error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject = Path(tmpdir) / "pyproject.toml"
        pyproject.write_text("""
[tool.clean-arch]
allowed_lod_methods = ["strip"]
""")

        # We need to force ConfigurationLoader to reload from this directory
        import os

        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            # Singleton reset
            ConfigurationLoader._instance = None
            with pytest.raises(ValueError, match="must use a Fully Qualified Name with at least two dots"):
                ConfigurationLoader()
        finally:
            os.chdir(old_cwd)
            ConfigurationLoader._instance = None
