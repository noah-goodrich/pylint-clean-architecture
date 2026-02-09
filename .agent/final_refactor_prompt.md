TASK: Execute Strategic Refactor

You are the Excelsior Senior Architect. We are moving from "Tactical Fixes" to "Pattern-Based Refactoring".

Read the BLUEPRINT.md found in the root.

Focus on Strategy: {Select first strategy}.

Execution Protocol:

DO NOT just fix line by line.

Extract the identified logic into the specific pattern requested (e.g., ADAPTER, FACADE).

If a Protocol is needed, put it in src/excelsior_architect/domain/protocols.py.

Implement the Adapter in src/excelsior_architect/infrastructure/adapters/.

Validation:

Run pytest - zero failures allowed.

Run excelsior check - the systemic violations for this pattern MUST disappear.

Ready to begin Phase 0. What is the first file in the blueprint we are analyzing?