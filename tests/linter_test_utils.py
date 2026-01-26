import astroid  # type: ignore[import-untyped]


class MockLinter:
    def __init__(self) -> None:
        self.messages = []
        self.config = type("config", (), {})()
        self.current_name = "test_module"
        self.config_loader = type("MockConfigLoader", (), {"config": {}})()

    def add_message(self, msg_id, *_args, **_kwargs):
        self.messages.append(msg_id)

    def _register_options_provider(self, provider):
        pass


def run_checker(checker_cls, code, filename="test.py", **checker_kwargs) -> list:
    linter = MockLinter()
    checker = checker_cls(linter, **checker_kwargs)
    tree = astroid.parse(code)
    tree.file = filename

    def _walk(node):
        node_name = node.__class__.__name__.lower()  # pylint: disable=law-of-demeter-violation

        # pylint: disable=law-of-demeter-violation
        if hasattr(checker, f"visit_{node_name}"):
            getattr(checker, f"visit_{node_name}")(node)

        for child in node.get_children():
            _walk(child)

        if hasattr(checker, f"leave_{node_name}"):
            getattr(checker, f"leave_{node_name}")(node)

    _walk(tree)
    return linter.messages
