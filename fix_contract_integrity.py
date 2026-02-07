#!/usr/bin/env python3
import re

file_path = "src/excelsior_architect/domain/rules/contract_integrity.py"

with open(file_path, "r") as f:
    content = f.read()

# Replace isinstance check with hasattr checks
old_pattern = r'if not isinstance\(node, astroid\.nodes\.ClassDef\):\s+return \[\]'
new_text = '''# Only ClassDef nodes have 'bases' and 'name' attributes
        if not hasattr(node, "bases") or not hasattr(node, "name"):
            return []'''

content = re.sub(old_pattern, new_text, content)

with open(file_path, "w") as f:
    f.write(content)

print("File updated successfully")
