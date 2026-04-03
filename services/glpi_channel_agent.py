"""Agent: channel message → LLM plan → GLPI follow-up, ticket update, or new ticket."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

from config import LLM_MODEL, LLM_PROVIDER, OPENAI_API_KEY
from services.glpi_api_service import get_glpi_api_service

logger = logging.getLogger(__name__)

_TICKET_ID_PATTERNS = (
    re.compile(r"\b(?:ticket|tkt)\s*#?\s*(\d+)\b", re.I),
    re.compile(r"\bGLPI\s*#?\s*(\d+)\b", re.I),
    re.compile(r"Ticket\s*ID\s*:\s*(\d+)", re.I),
    re.compile(r"📎\s*DataPilot:.*?#\s*(\d+)", re.I),
)

_ALLOWED_GLPI_UPDATE_KEYS = frozenset({"status", "urgency", "impact", "itilcategories_id", "name"})


def extract_ticket_ids(text: str) -> list[int]:
    found: list[int] = []
    for pat in _TICKET_ID_PATTERNS:
        for m in pat.finditer(text):
            try:
                found.append(int(m.group(1)))
            except ValueError:
                continue
    out: list[int] = []
    for x in found:
        if x not in out:
            out.append(x)
    return out


def _sanitize_updates(d: dict[str, Any] | None) -> dict[str, Any]:
    if not d:
        return {}
    out: dict[str, Any] = {}
    for k, v in d.items():
        if k not in _ALLOWED_GLPI_UPDATE_KEYS or v is None:
            continue
        if k in ("status", "urgency", "impact", "itilcategories_id"):
            try:
                out[k] = int(v)
            except (TypeError, ValueError):
                continue
        elif k == "name" and isinstance(v, str):
            out[k] = v[:255]
    return out


def _heuristic_plan(text: str, context_ticket_id: int | None) -> dict[str, Any]:
    t = text.lower()
    ids = extract_ticket_ids(text)
    tid = ids[0] if ids else context_ticket_id
    if any(p in t for p in ("new ticket", "create ticket", "open a ticket", "raise a ticket")):
        name = text.strip()[:200] or "Request from channel"
        return {
            "action": "create_ticket",
            "ticket_id": None,
            "followup_plain": None,
            "new_ticket_name": name,
            "new_ticket_description": text.strip(),
            "urgency": 3,
            "impact": 3,
            "update_fields": {},
        }
    if tid:
        return {
            "action": "add_followup",
            "ticket_id": tid,
            "followup_plain": text.strip(),
            "new_ticket_name": None,
            "new_ticket_description": None,
            "urgency": 3,
            "impact": 3,
            "update_fields": {},
        }
    return {
        "action": "none",
        "ticket_id": None,
        "followup_plain": None,
        "new_ticket_name": None,
        "new_ticket_description": None,
        "urgency": 3,
        "impact": 3,
        "update_fields": {},
    }


def _llm_plan(text: str, context_ticket_id: int | None) -> dict[str, Any] | None:
    if not OPENAI_API_KEY:
        return None
    provider = (LLM_PROVIDER or "openai").lower()
    client = (
        OpenAI(api_key=OPENAI_API_KEY, base_url="https://api.groq.com/openai/v1")
        if provider == "groq"
        else OpenAI(api_key=OPENAI_API_KEY)
    )
    model = LLM_MODEL or "gpt-4o-mini"
    system = """You route Slack/Teams-style IT channel messages to GLPI actions.
Return ONLY a JSON object with keys:
- action: one of "add_followup", "create_ticket", "update_ticket", "none"
- ticket_id: number or null (GLPI ticket; use context_ticket_id or parse #123 from message)
- followup_plain: string or null (plain text to append as GLPI follow-up)
- new_ticket_name: string or null (short title for create_ticket)
- new_ticket_description: string or null (body for new ticket, plain text)
- urgency: integer 1-5 (default 3)
- impact: integer 1-5 (default 3)
- update_fields: object or null — only GLPI Ticket fields: status, urgency, impact, itilcategories_id, name (integers for numeric fields). Use only if user clearly asks to change status/priority.

Rules:
- add_followup: user adds information to an EXISTING ticket (must resolve ticket_id).
- create_ticket: user wants a NEW ticket opened.
- update_ticket: user wants metadata changed (combine with followup if they also comment).
- none: greetings, thanks, or unrelated chatter.

Prefer add_followup when ticket_id is known from context or message and user is not asking for a brand-new ticket."""
    ctx = f"context_ticket_id: {context_ticket_id}" if context_ticket_id else "context_ticket_id: null"
    user = f"{ctx}\n\nUser message:\n{text}"

    try:
        common = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 500,
        }
        try:
            resp = client.chat.completions.create(
                **common, response_format={"type": "json_object"}
            )
        except Exception:
            resp = client.chat.completions.create(**common)
        raw = (resp.choices[0].message.content or "").strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning("LLM channel plan failed: %s", e)
        return None


class GLPIChannelAgent:
    def run(self, user_text: str, *, context_ticket_id: int | None = None) -> dict[str, Any]:
        plan = _llm_plan(user_text, context_ticket_id) or _heuristic_plan(user_text, context_ticket_id)
        action = (plan.get("action") or "none").lower()
        api = get_glpi_api_service()
        out: dict[str, Any] = {"ok": True, "action": action, "plan": plan, "glpi": {}}

        if not api.is_configured():
            out["ok"] = False
            out["error"] = "GLPI API not configured"
            return out

        if action == "none":
            out["message"] = "No GLPI action taken"
            return out

        if action == "create_ticket":
            name = (plan.get("new_ticket_name") or "Channel request").strip()[:255]
            desc = (plan.get("new_ticket_description") or user_text).strip()
            urgency = int(plan.get("urgency") or 3)
            impact = int(plan.get("impact") or 3)
            cr = api.create_ticket(name, desc, urgency=urgency, impact=impact)
            out["glpi"]["create_ticket"] = cr
            out["ok"] = bool(cr.get("ok"))
            return out

        ticket_id = plan.get("ticket_id")
        if ticket_id is None:
            ids = extract_ticket_ids(user_text)
            ticket_id = ids[0] if ids else context_ticket_id
        try:
            ticket_id_int = int(ticket_id) if ticket_id is not None else None
        except (TypeError, ValueError):
            ticket_id_int = None

        if ticket_id_int is None:
            out["ok"] = False
            out["error"] = "Could not determine ticket_id for this action"
            return out

        if action in ("add_followup", "update_ticket"):
            updates = _sanitize_updates(plan.get("update_fields"))
            if updates:
                ur = api.update_ticket(ticket_id_int, updates)
                out["glpi"]["update_ticket"] = ur
                if not ur.get("ok"):
                    out["ok"] = False

            fu = (plan.get("followup_plain") or "").strip()
            if fu or action == "add_followup":
                text = fu or user_text.strip()
                if text:
                    fr = api.add_ticket_followup(
                        ticket_id_int,
                        f"[Channel agent]\n{text}",
                    )
                    out["glpi"]["followup"] = fr
                    if not fr.get("ok"):
                        out["ok"] = False

            return out

        out["ok"] = False
        out["error"] = f"Unknown action {action}"
        return out


_channel_agent: GLPIChannelAgent | None = None


def get_glpi_channel_agent() -> GLPIChannelAgent:
    global _channel_agent
    if _channel_agent is None:
        _channel_agent = GLPIChannelAgent()
    return _channel_agent
