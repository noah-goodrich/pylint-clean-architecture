from typing import TypedDict


class RuleRegistryEntry(TypedDict, total=False):
    short_description: str
    display_name: str
    symbol: str
    message_template: str
    manual_instructions: str
    proactive_guidance: str
    fixable: bool
    comment_only: bool
    references: list[str]
    rule_id: str
