"""
Hydrates the Kuzu Graph with static knowledge (Violations and Patterns).
"""
import csv
from pathlib import Path
from excelsior_architect.infrastructure.gateways.kuzu_gateway import KuzuGraphGateway


class InitializeGraphUseCase:
    def __init__(self, gateway: KuzuGraphGateway):
        self.gateway = gateway

    def execute(self, violations_csv: str, patterns_csv: str):
        # 1. Load Patterns and link to violations
        with open(patterns_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                codes = [c.strip() for c in row['Violations'].split(',')]
                self.gateway.add_strategy(
                    strat_id=row['ID'],
                    pattern=row['Pattern'],
                    rationale=row['Rationale'],
                    steps=row['Implementation'].split(','),
                    codes=codes
                )

        # 2. Add remaining violations as template nodes for future mapping
        with open(violations_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # This ensures every code in our master registry exists in the graph
                self.gateway.conn.execute(
                    f"MERGE (v:Violation {{code: '{row['Code']}', message: '{row['Name']}'}})"
                )
