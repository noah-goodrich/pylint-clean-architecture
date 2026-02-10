"""Extracts code snippets (function/class bodies) at given file:line for blueprint display."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import astroid

if TYPE_CHECKING:
    from excelsior_architect.domain.protocols import AstroidProtocol, FileSystemProtocol


@dataclass(frozen=True)
class CodeSnippet:
    """A code snippet with file, symbol/location, and source."""

    file_path: str
    symbol_or_line: str
    source: str


class CodeSnippetExtractor:
    """
    Extracts enclosing function/class source at file:line.
    Used to show "current state" in blueprints.
    """

    def __init__(
        self,
        filesystem: "FileSystemProtocol",
        ast_protocol: "AstroidProtocol",
    ) -> None:
        self._fs = filesystem
        self._ast = ast_protocol

    def extract_at(self, file_path: str, line: int, root_dir: str = ".") -> CodeSnippet | None:
        """
        Return the enclosing function/class source at the given line.
        file_path may be relative (to root_dir) or absolute.
        """
        resolved = self._resolve_path(file_path, root_dir)
        if not self._fs.exists(resolved):
            return None
        try:
            tree = self._ast.parse_file(resolved)
            if tree is None:
                return None
            source = self._fs.read_text(resolved)
            lines = source.splitlines()
            node = self._node_at_line(tree, line)
            if node is None:
                return self._snippet_from_line(lines, line, resolved, f"L{line}")
            start = getattr(node, "fromlineno", line) or line
            end = getattr(node, "end_lineno", line) or line
            symbol = getattr(node, "name", None) or f"L{line}"
            snip_lines = lines[start - 1 : end]
            return CodeSnippet(
                file_path=resolved,
                symbol_or_line=symbol if isinstance(symbol, str) else f"L{line}",
                source="\n".join(snip_lines),
            )
        except Exception:
            return None

    def _resolve_path(self, path: str, root_dir: str) -> str:
        p = Path(path)
        if not p.is_absolute():
            p = Path(root_dir) / p
        return str(p.resolve())

    def _node_at_line(self, module, line: int):
        """Find the smallest node that contains the given line (function/class preferred)."""
        best = None
        best_span = float("inf")
        for node in module.nodes_of_class(
            (astroid.nodes.FunctionDef, astroid.nodes.ClassDef, astroid.nodes.Module)
        ):
            start = getattr(node, "fromlineno", None)
            end = getattr(node, "end_lineno", None)
            if start is not None and end is not None and start <= line <= end:
                span = end - start
                if span < best_span:
                    best_span = span
                    best = node
        return best

    def _snippet_from_line(
        self, lines: list[str], line: int, file_path: str, symbol: str
    ) -> CodeSnippet:
        """Fallback: return a few lines around the target when no enclosing node found."""
        idx = max(0, line - 1)
        start = max(0, idx - 2)
        end = min(len(lines), idx + 4)
        return CodeSnippet(
            file_path=file_path,
            symbol_or_line=symbol,
            source="\n".join(lines[start:end]),
        )
