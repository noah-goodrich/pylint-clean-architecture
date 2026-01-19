from astroid import extract_node
from pylint.testutils import CheckerTestCase, MessageTest

from clean_architecture_linter.checks.patterns import CouplingChecker
from clean_architecture_linter.config import ConfigurationLoader


class TestStellarLodBenchmarks(CheckerTestCase):
    CHECKER_CLASS = CouplingChecker

    def setup_method(self) -> None:
        super().setup_method()
        ConfigurationLoader._config = {}
        self.checker.config_loader = ConfigurationLoader()

    def test_stdlib_pathlib_chain_is_permitted(self) -> None:
        node = extract_node("""
            from pathlib import Path
            Path('stellar.txt').read_text().splitlines()  #@
        """)
        with self.assertNoMessages():
            self.checker.visit_call(node)

    def test_type_hint_propagation_allows_chaining(self) -> None:
        node = extract_node("""
            def get_name() -> str: return "voyager"
            name: str = get_name()
            name.upper().strip()  #@
        """)
        with self.assertNoMessages():
            self.checker.visit_call(node)

    def test_any_is_not_a_hall_pass(self) -> None:
        node = extract_node("""
            from typing import Any
            def get_data() -> Any: return "hull_breach"
            data = get_data()
            data.split().lower()  #@
        """)
        with self.assertAddsMessages(
            MessageTest(
                msg_id="law-of-demeter",
                node=node,
                args=("split().lower",),
                line=5,
                col_offset=0,
                end_line=5,
                end_col_offset=20,
            )
        ):
            self.checker.visit_call(node)
