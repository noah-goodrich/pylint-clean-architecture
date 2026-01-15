import pytest

from clean_architecture_linter.checks.structure import ModuleStructureChecker
from tests.linter_test_utils import run_checker


@pytest.mark.unit
class TestModuleStructureChecker:
    @pytest.fixture(autouse=True)
    def setup_config(self):
        # We rely on the default configuration loaded by the checker
        pass

    def test_god_file_multiple_heavy_components(self):
        code = """
class CreateUserUseCase:
    pass

class DeleteUserUseCase:
    pass
        """
        # Suffix matching: *UseCase -> UseCase layer (Heavy)
        messages = run_checker(ModuleStructureChecker, code, filename="services/user_service.py")
        assert "clean-arch-god-file" in messages

    def test_mixed_layers_god_file(self):
        code = """
class CreateUserUseCase:
    pass

class UserRepository:
    pass
        """
        # UseCase + Infrastructure (Repository) -> Mixed Layers
        messages = run_checker(ModuleStructureChecker, code, filename="services/mixed.py")
        assert "clean-arch-god-file" in messages

    def test_multiple_lightweight_components_allowed(self):
        # We simulate "Lightweight" by using suffixes that map to Domain or aren't mapped (None)
        # But we need to ensure they ARE mapped to a layer to test "same layer" logic,
        # or at least that they don't trigger "Heavy".
        # *Entity -> Domain. Domain is NOT Heavy.
        code = """
class UserEntity:
    pass

class OrderEntity:
    pass
        """
        messages = run_checker(ModuleStructureChecker, code, filename="domain/entities.py")
        assert "clean-arch-god-file" not in messages

    def test_deep_structure_violation(self):
        # Root file check
        code = "class SomeLogic: pass"
        messages = run_checker(ModuleStructureChecker, code, filename="logic.py")
        assert "clean-arch-folder-structure" in messages

    def test_deep_structure_allowed_files(self):
        code = "class SomeConfig: pass"
        messages = run_checker(ModuleStructureChecker, code, filename="conftest.py")
        assert "clean-arch-folder-structure" not in messages
