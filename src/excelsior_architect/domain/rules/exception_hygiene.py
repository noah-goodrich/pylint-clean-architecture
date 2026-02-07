"""Exception Hygiene rule (W9035): bare except, except Exception without re-raise, empty except body."""

import astroid

from excelsior_architect.domain.rules import Checkable, Violation


class ExceptionHygieneRule(Checkable):
    """Rule for W9035: Bare except, except Exception without re-raise, or empty except body."""

    code: str = "W9035"
    description: str = "Exception hygiene: avoid bare except, swallow Exception, or empty except body."
    fix_type: str = "code"

    def check(self, node: astroid.nodes.NodeNG) -> list[Violation]:
        """Check an ExceptHandler for W9035. Call once per handler."""
        if not isinstance(node, astroid.nodes.ExceptHandler):
            return []
        violations: list[Violation] = []
        # Bare except:
        if node.type is None:
            msg = "Bare 'except:' catches all; use 'except Exception:' and re-raise or handle explicitly."
            violations.append(
                Violation.from_node(
                    code=self.code,
                    message=msg,
                    node=node,
                    message_args=(msg,),
                )
            )
            return violations
        # except Exception: without re-raise and non-empty body -> suggest re-raise or log
        if self._is_exception_type(node.type) and not self._body_reraises(node):
            if not self._body_is_empty(node):
                msg = "'except Exception:' without re-raise may swallow errors; re-raise or log and re-raise."
                violations.append(
                    Violation.from_node(
                        code=self.code,
                        message=msg,
                        node=node,
                        message_args=(msg,),
                    )
                )
        # Empty except body
        if self._body_is_empty(node):
            msg = "Empty except body swallows errors; add pass with comment, log, or re-raise."
            violations.append(
                Violation.from_node(
                    code=self.code,
                    message=msg,
                    node=node,
                    message_args=(msg,),
                )
            )
        return violations

    def _is_exception_type(self, type_node: astroid.nodes.NodeNG) -> bool:
        """True if type is Exception or BaseException (or name suggests it)."""
        if isinstance(type_node, astroid.nodes.Name):
            return getattr(type_node, "name", "") in ("Exception", "BaseException")
        if isinstance(type_node, astroid.nodes.Tuple):
            return any(self._is_exception_type(elt) for elt in getattr(type_node, "elts", []))
        return False

    def _body_reraises(self, node: astroid.nodes.ExceptHandler) -> bool:
        """True if body contains raise (re-raise) or raise SomeError()."""
        body = getattr(node, "body", []) or []
        for stmt in body:
            if isinstance(stmt, astroid.nodes.Raise):
                return True
            # Recursively check nested blocks
            if hasattr(stmt, "body"):
                for child in stmt.body:
                    if isinstance(child, astroid.nodes.Raise):
                        return True
        return False

    def _body_is_empty(self, node: astroid.nodes.ExceptHandler) -> bool:
        """True if body is empty or only pass."""
        body = getattr(node, "body", []) or []
        if not body:
            return True
        return all(
            isinstance(s, astroid.nodes.Pass) for s in body
        )
