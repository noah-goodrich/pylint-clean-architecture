import logging

from excelsior_architect.domain.config import ConfigurationLoader


def test_config_validation_penalty(caplog) -> None:
    """Providing allowed_lod_methods in config triggers deprecation warning in validate_config."""
    config_dict = {"allowed_lod_methods": ["strip"]}
    with caplog.at_level(logging.WARNING):
        ConfigurationLoader(config_dict, {})
    assert "deprecated" in caplog.text
    assert "dynamic Type Inference" in caplog.text
