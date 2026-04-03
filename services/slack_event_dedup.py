"""In-memory dedup for Slack event retries (do not run GLPI twice)."""

from __future__ import annotations

_seen: set[str] = set()
_MAX = 4000


def should_skip_slack_delivery(event_id: str | None) -> bool:
    if not event_id:
        return False
    if event_id in _seen:
        return True
    _seen.add(event_id)
    if len(_seen) > _MAX:
        _seen.clear()
    return False
