"""Test Law of Demeter: dict and primitive stdlib methods should NOT be flagged."""

import shutil
import tempfile
from pathlib import Path

from clean_architecture_linter.infrastructure.adapters.excelsior_adapter import ExcelsiorAdapter


class TestLoDDictPrimitives:
    """Test that dict.setdefault and similar primitive methods are not flagged."""

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.adapter = ExcelsiorAdapter()

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir)

    def _create_file(self, filename: str, content: str) -> str:
        path = Path(self.tmp_dir) / filename
        path.write_text(content)
        return str(path)

    def test_dict_setdefault_not_flagged(self):
        """dict.setdefault() should NOT trigger LoD violation - it's a primitive method."""
        code = '''
def configure_template(data: dict):
    """Configure template - mimics scaffolder pattern."""
    tool_section = data.get("tool", {})
    if not isinstance(tool_section, dict):
        return

    clean_arch = tool_section.get("clean-arch")
    if not isinstance(clean_arch, dict):
        return

    # This should NOT be flagged: dict.setdefault is a primitive stdlib method
    layer_map = clean_arch.setdefault("layer_map", {})
    layer_map.update({"services": "UseCase"})
'''
        file_path = self._create_file("test_dict.py", code)
        results = self.adapter.gather_results(file_path)

        # Filter for W9006 (LoD violations)
        lod_violations = [r for r in results if r.code == "W9006"]

        # Should have ZERO LoD violations
        assert len(lod_violations) == 0, (
            f"Expected NO LoD violations for dict.setdefault(), but found {len(lod_violations)}: "
            f"{[v.message for v in lod_violations]}"
        )

    def test_dict_get_chain_not_flagged(self):
        """dict.get().get() should NOT trigger LoD when both are dicts."""
        code = '''
def nested_config(config: dict):
    """Nested dict access."""
    # Both .get() calls return dict - should be safe
    nested = config.get("outer", {}).get("inner", {})
    return nested
'''
        file_path = self._create_file("test_dict_chain.py", code)
        results = self.adapter.gather_results(file_path)

        lod_violations = [r for r in results if r.code == "W9006"]
        assert len(lod_violations) == 0, (
            f"Expected NO LoD violations for dict.get().get(), but found {len(lod_violations)}"
        )

    def test_list_append_not_flagged(self):
        """list.append() should NOT trigger LoD - primitive method."""
        code = '''
def process_items():
    """Process items with list operations."""
    items = get_items()  # Returns list
    if not isinstance(items, list):
        return

    # list.append is primitive - should be safe
    items.append("new_item")
    return items

def get_items():
    return []
'''
        file_path = self._create_file("test_list.py", code)
        results = self.adapter.gather_results(file_path)

        lod_violations = [r for r in results if r.code == "W9006"]
        assert len(lod_violations) == 0, (
            f"Expected NO LoD violations for list.append(), but found {len(lod_violations)}"
        )

    def test_str_split_not_flagged(self):
        """str.split() should NOT trigger LoD - primitive method."""
        code = '''
def parse_path(path: str):
    """Parse path with str methods."""
    # str.split is primitive - should be safe
    parts = path.split("/")
    return parts
'''
        file_path = self._create_file("test_str.py", code)
        results = self.adapter.gather_results(file_path)

        lod_violations = [r for r in results if r.code == "W9006"]
        assert len(lod_violations) == 0, (
            f"Expected NO LoD violations for str.split(), but found {len(lod_violations)}"
        )
