"""Categorisation: first matching rule wins, case-insensitive substring."""
UNCATEGORISED = "Uncategorised"


def categorise(description: str, rules) -> str:
    text = description.lower()
    for rule in rules:
        if rule.pattern in text:
            return rule.category
    return UNCATEGORISED
