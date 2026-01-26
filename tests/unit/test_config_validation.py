import tempfile
from pathlib import Path

from clean_architecture_linter.domain.config import ConfigurationLoader


def test_config_validation_penalty(caplog) -> None:
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
            import logging
            with caplog.at_level(logging.WARNING):
                ConfigurationLoader()
            assert "deprecated" in caplog.text
            assert "dynamic Type Inference" in caplog.text
        finally:
            os.chdir(old_cwd)
            ConfigurationLoader._instance = None
