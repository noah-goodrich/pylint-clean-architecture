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
    # Scoring (priority formula)
    impact_weight: int | float
    confidence: float
    effort_category: int | float
    eli5_description: str
