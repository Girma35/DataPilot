"""Verify Slack Events API requests (signing secret + replay window)."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time

logger = logging.getLogger(__name__)


def verify_slack_signature(*, signing_secret: str, timestamp: str, raw_body: bytes, slack_signature: str) -> bool:
    if not signing_secret or not slack_signature or not timestamp:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > 60 * 5:
        logger.warning("Slack request timestamp outside allowed window")
        return False
    basestring = f"v0:{timestamp}:{raw_body.decode('utf-8')}"
    digest = hmac.new(
        signing_secret.encode("utf-8"),
        basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, slack_signature)


def slack_events_channel_allowed(channel_id: str | None) -> bool:
    from config import SLACK_EVENTS_CHANNEL_IDS

    raw = (SLACK_EVENTS_CHANNEL_IDS or "").strip()
    if not raw:
        return True
    if not channel_id:
        return False
    allowed = {x.strip() for x in raw.split(",") if x.strip()}
    return channel_id in allowed


def slack_message_plain_text(text: str) -> str:
    """Remove user/channel mentions '<@U>' '<#C|name>' for cleaner agent input."""
    if not text:
        return ""
    import re

    t = re.sub(r"<@[^>]+>\s*", "", text)
    t = re.sub(r"<#[^|>]+\|([^>]+)>", r"#\1", t)
    t = re.sub(r"<([^|>]+)>", r"\1", t)
    return t.strip()
