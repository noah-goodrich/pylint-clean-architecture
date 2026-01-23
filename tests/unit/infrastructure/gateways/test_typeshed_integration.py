import unittest
from unittest.mock import MagicMock, patch
from clean_architecture_linter.infrastructure.typeshed_integration import TypeshedService

class TestTypeshedService(unittest.TestCase):
    def setUp(self):
        # Reset singleton for testing
        TypeshedService._instance = None
        self.service = TypeshedService()

    @patch("clean_architecture_linter.infrastructure.typeshed_integration.finder")
    def test_is_stdlib_module_found_stdlib_path(self, mock_finder):
        # Scenario 1: Path contains 'stdlib' and 'site-packages'
        mock_stub = MagicMock()
        mock_stub.__str__.return_value: str = "/usr/lib/python3.11/site-packages/typeshed_client/typeshed/stdlib/re.pyi"
        mock_finder.get_stub_file.return_value = mock_stub

        self.assertTrue(self.service.is_stdlib_module("re"))
        mock_finder.get_stub_file.assert_called_with("re")

    @patch("clean_architecture_linter.infrastructure.typeshed_integration.finder")
    def test_is_stdlib_module_bundled_typeshed(self, mock_finder):
        # Scenario 2: Bundled typeshed structure
        mock_stub = MagicMock()
        mock_stub.__str__.return_value: str = "/site-packages/typeshed_client/typeshed/os/__init__.pyi"
        mock_finder.get_stub_file.return_value = mock_stub

        self.assertTrue(self.service.is_stdlib_module("os"))

    @patch("clean_architecture_linter.infrastructure.typeshed_integration.finder")
    def test_is_stdlib_module_bundled_stubs(self, mock_finder):
        # Scenario 3: Bundled 3rd party stubs (should be False)
        mock_stub = MagicMock()
        mock_stub.__str__.return_value: str = "/site-packages/typeshed_client/typeshed/stubs/yaml/__init__.pyi"
        mock_finder.get_stub_file.return_value = mock_stub

        self.assertFalse(self.service.is_stdlib_module("yaml"))

    @patch("clean_architecture_linter.infrastructure.typeshed_integration.finder")
    def test_is_stdlib_module_system_typeshed(self, mock_finder):
        # Scenario 4: System typeshed path
        mock_stub = MagicMock()
        mock_stub.__str__.return_value: str = "/usr/share/typeshed/stdlib/json.pyi"
        mock_finder.get_stub_file.return_value = mock_stub

        self.assertTrue(self.service.is_stdlib_module("json"))

    @patch("clean_architecture_linter.infrastructure.typeshed_integration.finder")
    def test_is_stdlib_module_not_found(self, mock_finder):
        mock_finder.get_stub_file.return_value = None
        self.assertFalse(self.service.is_stdlib_module("unknown_module"))

    @patch("clean_architecture_linter.infrastructure.typeshed_integration.finder")
    def test_is_stdlib_module_error(self, mock_finder):
        mock_finder.get_stub_file.side_effect = ImportError("typeshed not installed")
        self.assertFalse(self.service.is_stdlib_module("re"))

    def test_is_stdlib_qname(self):
        with patch.object(self.service, "is_stdlib_module") as mock_is_mod:
            mock_is_mod.return_value: bool = True
            self.assertTrue(self.service.is_stdlib_qname("os.path.join"))
            mock_is_mod.assert_called_with("os")

    def test_is_stdlib_qname_empty(self):
         self.assertFalse(self.service.is_stdlib_qname(""))
