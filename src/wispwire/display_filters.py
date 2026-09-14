"""Shared helpers for Wireshark display-filter UX."""

from __future__ import annotations

import re
from bisect import bisect_left


def format_display_filter_error(error: str) -> str:
    """Compact a TShark error and add a helpful hint for common cases."""

    compact = " ".join(line.strip() for line in error.splitlines() if line.strip())
    lowered = compact.lower()
    if '"tcp" is not a valid protocol' in lowered:
        return "Invalid display filter. Wireshark expects `tcp`, not `TCP`."
    if '"udp" is not a valid protocol' in lowered:
        return "Invalid display filter. Wireshark expects `udp`, not `UDP`."
    if "not a valid protocol or protocol field" in lowered:
        return "Invalid display filter. Check the protocol or field-name casing."
    if "syntax error" in lowered or "is neither a field nor a protocol name" in lowered:
        return f"Invalid display filter: {compact}"
    return compact


def filter_suggestions(value: str, fields: tuple[str, ...]) -> tuple[str, ...]:
    """Return nearest display-filter fields for the current token."""

    if not fields:
        return ()
    match = re.search(r"([A-Za-z_][A-Za-z0-9_.]*)$", value)
    if match is None:
        return ()
    prefix = match.group(1).lower()
    index = bisect_left(fields, prefix)
    suggestions: list[str] = []
    while index < len(fields) and fields[index].startswith(prefix):
        suggestions.append(fields[index])
        if len(suggestions) == 6:
            break
        index += 1
    return tuple(suggestions)


def draft_filter_error(value: str, fields: tuple[str, ...]) -> str | None:
    """Return a quick error for an obviously unknown field while typing."""

    if not fields:
        return None
    match = re.search(r"([A-Za-z_][A-Za-z0-9_.]*)$", value)
    if match is None:
        return None
    token = match.group(1)
    prefix = token.lower()
    if prefix in fields:
        return None
    if filter_suggestions(token, fields):
        return None
    return f"Unknown display-filter field: {token}"
