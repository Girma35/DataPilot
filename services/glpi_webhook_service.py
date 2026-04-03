"""GLPI webhook: new/open tickets → rich channel message + optional GLPI API follow-up / status."""

from __future__ import annotations

import logging
import re
from typing import Any

from config import (
    GLPI_WEBHOOK_ADD_FOLLOWUP,
    GLPI_WEBHOOK_EVENTS_MODE,
    GLPI_WEBHOOK_STATUS_ID,
)
from models.schemas import GLPIWebhookRequest, GLPIWebhookResponse
from services.ai_message_service import get_ai_message_service
from services.glpi_api_service import get_glpi_api_service

logger = logging.getLogger(__name__)

# Primary workflow: ticket opened / created / reopened
_OPEN_TICKET_EVENTS = frozenset(
    {
        "ticket.created",
        "ticket.new",
        "ticket.opened",
        "ticket.open",
        "ticket.reopened",
        "ticket.reopen",
        "glpi.ticket.created",
        "ticket.add",
    }
)

# When GLPI_WEBHOOK_EVENTS_MODE=all, also notify on these (legacy behaviour)
_EXTENDED_EVENTS = frozenset(
    {
        "ticket.updated",
        "ticket.closed",
        "ticket.resolved",
        "ticket.reply",
        "ticket.note",
        "ticket.assigned",
        "ticket.priority_changed",
        "ticket.status_changed",
    }
)

_DISCORD_MAX = 1900


def _truncate(text: str, max_len: int) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _strip_html(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", " ", text)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def build_channel_notification(request: GLPIWebhookRequest, summary_line: str) -> str:
    """Readable multiline message for Slack + Discord (description included)."""
    tid = request.item_id
    header = f"New GLPI ticket #{tid}" if tid is not None else "New GLPI ticket"
    lines: list[str] = [header]

    if request.name:
        lines.append(str(request.name))
    lines.append("")

    meta_parts: list[str] = []
    if request.priority is not None:
        try:
            pv = int(request.priority)
        except (TypeError, ValueError):
            pv = request.priority
        pmap = {1: "Very low", 2: "Low", 3: "Medium", 4: "High", 5: "Critical"}
        meta_parts.append(f"Priority: {pmap.get(pv, pv)}")
    if request.status is not None:
        meta_parts.append(f"Status: {request.status}")
    if request.category:
        meta_parts.append(f"Category: {request.category}")
    if request.requester:
        meta_parts.append(f"Requester: {request.requester}")
    if request.assignee:
        meta_parts.append(f"Assigned: {request.assignee}")
    if meta_parts:
        lines.append(" | ".join(meta_parts))
        lines.append("")

    lines.append(f"Summary: {summary_line}")
    lines.append("")

    desc = _strip_html(request.description or "")
    if desc:
        lines.append("Description:")
        lines.append(_truncate(desc, 1200))
    else:
        lines.append("(No description in payload)")

    if tid is not None:
        lines.append("")
        lines.append(
            f"📎 DataPilot: Reply in this channel to add a follow-up on ticket #{tid}, "
            f"or say “new ticket …” to open one. (Slack Events API → POST /integrations/slack/events)"
        )

    body = "\n".join(lines)
    return _truncate(body, _DISCORD_MAX)


class GLPIWebhookService:
    """Process GLPI webhooks: alert channels, then optionally update the ticket via API."""

    def __init__(
        self,
        alert_service: Any = None,
        auto_forward: bool = True,
    ) -> None:
        self._alert_service = alert_service
        self._auto_forward = auto_forward

    def process_webhook(
        self,
        payload: dict[str, Any],
        forward_to_alert: bool = True,
    ) -> GLPIWebhookResponse:
        try:
            event_type = self._extract_event_type(payload)
            parsed = self._parse_glpi_payload(payload)
            request = GLPIWebhookRequest(
                event_type=event_type,
                raw_payload=payload,
                **parsed,
            )

            logger.info("GLPI webhook: event=%s ticket=%s name=%s", event_type, request.item_id, request.name)

            if not self._should_notify(event_type, request):
                return GLPIWebhookResponse(
                    ok=True,
                    message=f"Skipped notify for event {event_type!r} (open-only mode or not a new ticket)",
                    processed=True,
                    alert_sent=False,
                )

            summary = get_ai_message_service().generate_ticket_message(
                {
                    "name": request.name,
                    "description": request.description,
                    "priority": request.priority,
                    "status": request.status,
                    "category": request.category,
                    "requester": request.requester,
                    "assignee": request.assignee,
                    "event_type": request.event_type,
                    "item_id": request.item_id,
                }
            )
            message = build_channel_notification(request, summary)

            alert_sent = False
            alert_results: dict[str, Any] = {}
            if forward_to_alert and self._auto_forward and self._alert_service:
                try:
                    alert_results = self._alert_service.send(message, channel="both")
                    alert_sent = any(
                        v.get("status") == "success" for v in alert_results.values() if isinstance(v, dict)
                    )
                except Exception as e:
                    logger.error("Alert send failed: %s", e)

            glpi_followup_ok: bool | None = None
            glpi_followup_error: str | None = None
            glpi_status_updated: bool | None = None
            glpi_status_error: str | None = None

            if request.item_id is not None and GLPI_WEBHOOK_ADD_FOLLOWUP:
                api = get_glpi_api_service()
                if api.is_configured():
                    follow_lines = [
                        "DataPilot agent notified Slack/Discord about this ticket.",
                        f"Summary: {summary}",
                    ]
                    if alert_sent:
                        follow_lines.append("Channels: webhook delivery reported success for at least one target.")
                    else:
                        follow_lines.append("Note: webhook delivery may be skipped or failed — check DataPilot logs.")
                    fr = api.add_ticket_followup(request.item_id, "\n".join(follow_lines))
                    glpi_followup_ok = bool(fr.get("ok"))
                    if not glpi_followup_ok:
                        glpi_followup_error = str(fr.get("error", "followup failed"))[:500]
                else:
                    glpi_followup_ok = False
                    glpi_followup_error = (
                        "GLPI REST env missing or not loaded: set GLPI_API_URL "
                        "(e.g. http://host:8080/apirest.php), GLPI_APP_TOKEN, "
                        "GLPI_USER_TOKEN in DataPilot/.env and restart the API."
                    )

            status_id_raw = GLPI_WEBHOOK_STATUS_ID
            if request.item_id is not None and status_id_raw:
                try:
                    sid = int(status_id_raw)
                    api = get_glpi_api_service()
                    if api.is_configured():
                        sr = api.update_ticket_status(request.item_id, sid)
                        glpi_status_updated = bool(sr.get("ok"))
                        if not glpi_status_updated:
                            glpi_status_error = str(sr.get("error", "status update failed"))[:500]
                except ValueError:
                    glpi_status_error = f"Invalid GLPI_WEBHOOK_STATUS_ID: {status_id_raw!r}"

            return GLPIWebhookResponse(
                ok=True,
                message=f"Processed {event_type} for ticket #{request.item_id}",
                processed=True,
                alert_sent=alert_sent,
                glpi_followup_ok=glpi_followup_ok,
                glpi_followup_error=glpi_followup_error,
                glpi_status_updated=glpi_status_updated,
                glpi_status_error=glpi_status_error,
            )

        except Exception as e:
            logger.error("GLPI webhook error: %s", e)
            return GLPIWebhookResponse(ok=False, error=str(e), processed=False)

    def _should_notify(self, event_type: str | None, request: GLPIWebhookRequest) -> bool:
        et = (event_type or "unknown").lower().replace(" ", "_")
        mode = GLPI_WEBHOOK_EVENTS_MODE

        if mode == "all":
            return et in _OPEN_TICKET_EVENTS or et in _EXTENDED_EVENTS

        if et in _OPEN_TICKET_EVENTS:
            return True

        it = (request.item_type or "").lower()
        if it == "ticket" and request.item_id is not None:
            if et in ("unknown", "", "created", "new", "add"):
                return True
            if "creat" in et or et.endswith(".new") or "open" in et:
                return True

        return False

    def _extract_event_type(self, payload: dict[str, Any]) -> str | None:
        if "event" in payload:
            return str(payload["event"])
        if "event_type" in payload:
            return str(payload["event_type"])
        if "type" in payload:
            return str(payload["type"])
        if "itemtype" in payload or "item_type" in payload:
            item_type = payload.get("itemtype") or payload.get("item_type")
            action = str(payload.get("action", "created")).lower()
            return f"{str(item_type).lower()}.{action}"
        if "glpi" in payload and isinstance(payload["glpi"], dict):
            ge = payload["glpi"].get("event")
            if ge:
                return str(ge)
        return "unknown"

    def _parse_glpi_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = dict(payload)
        for key in ("ticket", "item", "data", "object", "record"):
            nested = payload.get(key)
            if isinstance(nested, dict):
                merged.update(nested)
        inp = merged.get("input")
        if isinstance(inp, dict):
            merged.update(inp)

        result: dict[str, Any] = {}
        field_mappings = {
            "item_id": ["id", "item_id", "itemid", "ticket_id", "items_id"],
            "item_type": ["itemtype", "item_type", "type", "object"],
            "name": ["name", "title", "subject"],
            "status": ["status", "state", "statut"],
            "priority": ["priority", "urgency", "urgency_id"],
            "category": ["category", "category_id", "itilcategories_id", "itilcategories_id_label"],
            "entity": ["entity", "entity_id", "entities_id"],
            "requester": ["requester", "requester_id", "user_id", "author", "users_id_recipient"],
            "assignee": ["assignee", "assigned_to", "tech_id", "assign_to_user", "users_id_tech"],
            "description": ["description", "content", "details", "body", "text"],
            "date_creation": ["date_creation", "created_at", "created"],
            "date_mod": ["date_mod", "updated_at", "modified"],
        }

        for target, sources in field_mappings.items():
            for source in sources:
                if source in merged and merged[source] is not None:
                    value = merged[source]
                    if target == "priority":
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            pass
                    result[target] = value
                    break

        return result


_glpi_webhook_service: GLPIWebhookService | None = None


def get_glpi_webhook_service(alert_service: Any = None) -> GLPIWebhookService:
    global _glpi_webhook_service
    if _glpi_webhook_service is None:
        _glpi_webhook_service = GLPIWebhookService(alert_service=alert_service)
    return _glpi_webhook_service
