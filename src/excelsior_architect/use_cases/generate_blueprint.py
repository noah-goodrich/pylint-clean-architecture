"""
Strategic Architecture Engine (SAE).
Ingests project + violations into the graph, queries strategies, synthesizes BLUEPRINT.md.
"""
import json
import yaml
from typing import TYPE_CHECKING, Any, Dict, List

from excelsior_architect.domain.protocols import ArtifactStorageProtocol
from excelsior_architect.domain.sae_entities import (
    RecommendedStrategy,
    RefactoringStep,
    StrategicBlueprint,
)

if TYPE_CHECKING:
    from excelsior_architect.domain.protocols import (
        CodeSnippetExtractorProtocol,
        GraphGatewayProtocol,
        TelemetryPort,
    )
    from excelsior_architect.domain.services.graph_ingestor import GraphIngestor


class GenerateBlueprintUseCase:
    """Aggregates tactical violations into a holistic refactoring strategy via the knowledge graph."""

    def __init__(
        self,
        storage: ArtifactStorageProtocol,
        graph_gateway: "GraphGatewayProtocol",
        ingestor: "GraphIngestor",
        telemetry: "TelemetryPort",
        snippet_extractor: "CodeSnippetExtractorProtocol | None" = None,
    ) -> None:
        self.storage = storage
        self.graph_gateway = graph_gateway
        self.ingestor = ingestor
        self.telemetry = telemetry
        self._snippet_extractor = snippet_extractor

    def execute(self, source: str = "check", root_dir: str = ".") -> str:
        # #region agent log
        import os, time
        _log_path = os.environ.get("EXCELSIOR_DEBUG_LOG", "/development/.cursor/debug.log")
        _log = lambda loc, msg, data, hid: open(_log_path, "a").write(json.dumps({"timestamp": int(time.time() * 1000), "location": loc, "message": msg, "data": data, "hypothesisId": hid}) + "\n")
        _log("generate_blueprint.py:execute", "entry", {"source": source, "root_dir": root_dir}, "H4")
        # #endregion
        handover = self._load_json(f"{source}/ai_handover.json")
        violation_list = self._handover_to_violation_list(handover)
        self.telemetry.step("Ingesting project and violations into knowledge graph...")
        self.ingestor.ingest_project(root_dir, violation_list)
        strategies = self.graph_gateway.query_recommended_strategies()
        tree = self._load_strategy_tree()
        if strategies:
            blueprints = [
                self._strategy_to_blueprint(rec, tree, handover, root_dir)
                for rec in strategies
            ]
        else:
            blueprints = self._fallback_yaml_blueprints(handover, tree, root_dir)
        playbook = "# Strategic Refactoring Playbook\n\n"
        if not blueprints:
            playbook += "No systemic architectural refactors required. Project health is optimal."
        else:
            playbook += f"## Total Strategies Identified: {len(blueprints)}\n\n"
            playbook += "\n\n---\n\n".join([bp.to_markdown() for bp in blueprints])
        # #region agent log
        _log("generate_blueprint.py:execute", "before write_artifact", {"playbook_len": len(playbook)}, "H2")
        # #endregion
        self.storage.write_artifact("BLUEPRINT.md", playbook)
        # #region agent log
        _log("generate_blueprint.py:execute", "after write_artifact", {}, "H2")
        # #endregion
        return "BLUEPRINT.md"

    def _handover_to_violation_list(self, handover: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for code, entries in handover.get("violations_by_rule", {}).items():
            for v in entries:
                out.append({
                    "code": code,
                    "message": v.get("message", ""),
                    "locations": v.get("locations", []),
                    "rule_id": v.get("rule_id"),
                })
        return out

    def _strategy_to_blueprint(
        self,
        rec: RecommendedStrategy,
        tree: Dict[str, Any],
        handover: Dict[str, Any],
        root_dir: str,
    ) -> StrategicBlueprint:
        pattern = rec["pattern"]
        files = list(rec["affected_files"])
        violations = list(rec["violations"])
        rationale = rec.get("rationale", "")
        node = self._find_tree_node(tree, pattern)
        steps = []
        steps.append(RefactoringStep(0, "Analyze", "Source AST", f"Locate violation logic in {len(files)} files."))
        if node and node.get("implementation"):
            for step_text in node["implementation"]:
                steps.append(RefactoringStep(1, "Create/Modify", pattern, step_text))
        steps.append(RefactoringStep(2, "Inject", "Dependency Container", f"Wire the new {pattern} into the application."))
        steps.append(RefactoringStep(3, "Verify", "Excelsior CLI", f"Confirm removal of codes: {violations}"))
        # Use "." for path resolution - file paths are relative to project root (cwd)
        snippets = self._extract_snippets_for_strategy(rec, handover, ".")
        return StrategicBlueprint(
            strategy_id=node.get("id", pattern) if node else pattern,
            pattern_name=pattern,
            rationale=rationale,
            affected_files=files,
            steps=steps,
            current_snippets=snippets,
        )

    def _find_tree_node(self, tree: Dict[str, Any], pattern: str) -> Dict[str, Any] | None:
        for branch in tree.get("branches", {}).values():
            for node in branch.get("nodes", []):
                if node.get("pattern") == pattern:
                    return node
        return None

    def _extract_snippets_for_strategy(
        self,
        rec: RecommendedStrategy,
        handover: Dict[str, Any],
        root_dir: str,
    ) -> List[Dict[str, Any]]:
        """Collect (file, line) from handover for this strategy, extract snippets."""
        if not self._snippet_extractor:
            return []
        affected = set(f.replace("\\", "/") for f in rec.get("affected_files", []))
        violation_codes = set(rec.get("violations", []))
        locations: List[tuple[str, int]] = []
        for code, entries in handover.get("violations_by_rule", {}).items():
            if code not in violation_codes:
                continue
            for v in entries:
                for loc in v.get("locations") or []:
                    parts = str(loc).split(":")
                    if len(parts) >= 2:
                        fpath = parts[0].replace("\\", "/")
                        try:
                            line_num = int(parts[1])
                        except ValueError:
                            continue
                        if self._path_matches_affected(fpath, affected):
                            locations.append((fpath, line_num))
        snippets: List[Dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()
        for fpath, line_num in locations[:20]:
            if (fpath, line_num) in seen:
                continue
            seen.add((fpath, line_num))
            snip = self._snippet_extractor.extract_at(fpath, line_num, root_dir)
            if snip:
                snippets.append({
                    "file_path": snip.file_path,
                    "symbol_or_line": snip.symbol_or_line,
                    "source": snip.source,
                })
        return snippets

    def _path_matches_affected(self, fpath: str, affected: set[str]) -> bool:
        """Check if fpath matches any affected file (handles relative/absolute)."""
        n = fpath.replace("\\", "/")
        for af in affected:
            an = af.replace("\\", "/")
            if n == an:
                return True
            if n.endswith(an) or an.endswith(n):
                return True
            # Compare normalized tails (e.g. domain/analysis.py)
            n_parts = n.split("/")
            an_parts = an.split("/")
            if len(n_parts) >= 2 and len(an_parts) >= 2:
                n_tail = n_parts[-2] + "/" + n_parts[-1]
                an_tail = an_parts[-2] + "/" + an_parts[-1]
                if n_tail == an_tail:
                    return True
        return False

    def _fallback_yaml_blueprints(
        self, handover: Dict[str, Any], tree: Dict[str, Any], root_dir: str = "."
    ) -> List[StrategicBlueprint]:
        blueprints: List[StrategicBlueprint] = []
        violations = handover.get("violations_by_rule", {})
        for branch in tree.get("branches", {}).values():
            for node in branch.get("nodes", []):
                rules_to_match = node.get("violations", [])
                affected_files = self._find_affected_files(rules_to_match, violations)
                if affected_files:
                    blueprints.append(self._synthesize(node, affected_files))
        return blueprints

    def _find_affected_files(self, trigger_rules: List[str], violations: Dict) -> List[str]:
        files = set()
        for rule in trigger_rules:
            if rule in violations:
                for v in violations[rule]:
                    locs = v.get("locations") or []
                    if locs:
                        files.add(str(locs[0]).split(":")[0])
        return sorted(files)

    def _synthesize(self, node: Dict, files: List[str]) -> StrategicBlueprint:
        steps = [
            RefactoringStep(0, "Analyze", "Source AST", f"Locate violation logic in {len(files)} files."),
        ]
        for step_text in node.get("implementation", []):
            steps.append(RefactoringStep(1, "Create/Modify", node["pattern"], step_text))
        steps.append(RefactoringStep(2, "Inject", "Dependency Container", f"Wire the new {node['pattern']} into the application."))
        steps.append(RefactoringStep(3, "Verify", "Excelsior CLI", f"Confirm removal of codes: {node.get('violations', [])}"))
        return StrategicBlueprint(
            strategy_id=node.get("id", ""),
            pattern_name=node["pattern"],
            rationale=node.get("rationale", ""),
            affected_files=files,
            steps=steps,
        )

    def _load_json(self, key: str) -> Dict:
        content = self.storage.read_artifact(key)
        return json.loads(content)

    def _load_strategy_tree(self) -> Dict[str, Any]:
        try:
            from importlib.resources import files as resource_files
            pkg = resource_files("excelsior_architect")
            path = pkg.joinpath("resources", "strategy_tree.yaml")
            if path.is_file():
                return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            pass
        from pathlib import Path
        for candidate in [Path("resources/strategy_tree.yaml"), Path("src/excelsior_architect/resources/strategy_tree.yaml")]:
            if candidate.exists():
                return yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
        return {}
