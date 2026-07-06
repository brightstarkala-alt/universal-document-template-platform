"""
`machine_key` normalization — Module 7.

Every `ExtractedField`/`ExtractedTableColumn` carries both a `display_label`
(exact source text) and a `machine_key` (normalized snake_case identifier).
The LLM proposes a key from the label; this module is the single place that
enforces the key is actually snake_case and unique within one extraction
result, so two fields never collide (e.g. two "Date" labels on one document).
"""

import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_machine_key(label: str) -> str:
    lowered = label.strip().lower()
    normalized = _NON_ALNUM.sub("_", lowered).strip("_")
    if not normalized:
        normalized = "field"
    if normalized[0].isdigit():
        normalized = f"field_{normalized}"
    return normalized


def dedupe_machine_keys(keys: list[str]) -> list[str]:
    """Appends `_2`, `_3`, ... to repeats, in order of first appearance."""
    seen: dict[str, int] = {}
    result: list[str] = []
    for key in keys:
        count = seen.get(key, 0)
        seen[key] = count + 1
        result.append(key if count == 0 else f"{key}_{count + 1}")
    return result
