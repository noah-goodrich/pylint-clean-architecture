import json
import yaml
from typing import List, Dict, Any
from excelsior_architect.domain.protocols import ArtifactStorageProtocol
from excelsior_architect.domain.sae_entities import StrategicBlueprint, RefactoringStep


class GenerateBlueprintUseCase:
    """
    Strategic Architecture Engine (SAE).
    Aggregates tactical violations into a holistic refactoring strategy.
    """

    def __init__(self, storage: ArtifactStorageProtocol):
        self.storage = storage

    def execute(self, source: str = "check") -> str:
        # 1. Load context and declarative tree
        handover = self._load_json(f"{source}/ai_handover.json")
        tree = self._load_yaml(
            "src/excelsior_architect/resources/strategy_tree.yaml")
        violations = handover.get("violations_by_rule", {})

        # 2. Identify Patterns based on Cluster Analysis
        blueprints = []
        for branch_name, branch in tree.get('branches', {}).items():
            for node in branch.get('nodes', []):
                # Cluster Check: Are any of these rule signatures present?
                rules_to_match = node.get('violations', [])
                affected_files = self._find_affected_files(
                    rules_to_match, violations)

                if affected_files:
                    blueprints.append(self._synthesize(node, affected_files))

        # 3. Write output Playbook
        playbook = "# Strategic Refactoring Playbook\n\n"
        if not blueprints:
            playbook += "No systemic architectural refactors required. Project health is optimal."
        else:
            playbook += f"## Total Strategies Identified: {len(blueprints)}\n\n"
            playbook += "\n\n---\n\n".join([bp.to_markdown()
                                           for bp in blueprints])

        self.storage.write_artifact("BLUEPRINT.md", playbook)
        return "BLUEPRINT.md"

    def _find_affected_files(self, trigger_rules: List[str], violations: Dict) -> List[str]:
        files = set()
        for rule in trigger_rules:
            if rule in violations:
                for v in violations[rule]:
                    # Extract file path from location string 'file.py:line'
                    files.add(v['locations'][0].split(":")[0])
        return sorted(list(files))

    def _synthesize(self, node: Dict, files: List[str]) -> StrategicBlueprint:
        """Translates a YAML strategy node into a 4-phase implementation plan."""
        steps = []

        # Phase 0: Discovery
        steps.append(RefactoringStep(0, "Analyze", "Source AST",
                     f"Locate violation logic in {len(files)} files."))

        # Phase 1: Structural (Pattern Specific)
        impl_steps = node.get('implementation', [])
        for step_text in impl_steps:
            steps.append(RefactoringStep(
                1, "Create/Modify", node['pattern'], step_text))

        # Phase 2: Integration
        steps.append(RefactoringStep(2, "Inject", "Dependency Container",
                     f"Wire the new {node['pattern']} into the application."))

        # Phase 3: Verification
        steps.append(RefactoringStep(3, "Verify", "Excelsior CLI",
                     f"Confirm removal of codes: {node['violations']}"))

        return StrategicBlueprint(
            strategy_id=node['id'],
            pattern_name=node['pattern'],
            rationale=node.get('rationale', ''),
            affected_files=files,
            steps=steps
        )

    def _load_json(self, key: str) -> Dict:
        content = self.storage.read_artifact(key)
        return json.loads(content)

    def _load_yaml(self, path: str) -> Dict:
        # Integration point for package_resources or standard loading
        with open(path, 'r') as f:
            return yaml.safe_load(f)
