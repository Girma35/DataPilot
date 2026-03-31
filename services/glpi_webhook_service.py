"""GLPI webhook service for processing incoming ticket notifications."""

from __future__ import annotations

import logging
from typing import Any

from models.schemas import GLPIWebhookRequest, GLPIWebhookResponse

logger = logging.getLogger(__name__)


class GLPIWebhookService:
    """Service to process GLPI webhook notifications and optionally forward alerts."""

    def __init__(
        self,
        alert_service: "AlertService | None" = None,
        auto_forward: bool = True,
    ) -> None:
        """Initialize GLPI webhook service.

        Args:
            alert_service: AlertService instance for forwarding notifications
            auto_forward: Whether to automatically forward to Slack/Discord
        """
        self._alert_service = alert_service
        self._auto_forward = auto_forward

        # Event type patterns that can be sent to alerts
        self._forwardable_events = {
            "ticket.created",
            "ticket.updated",
            "ticket.closed",
            "ticket.resolved",
            "ticket.reply",
            "ticket.note",
            "ticket.assigned",
            "ticket.priority_changed",
            "ticket.status_changed",
        }

        # Priority to emoji mapping
        self._priority_emoji = {
            1: "1 (Low)",
            2: "2 (Medium)",
            3: "3 (High)",
            4: "4 (Critical)",
            5: "5 (Emergency)",
        }

    def process_webhook(
        self,
        payload: dict[str, Any],
        forward_to_alert: bool = True,
    ) -> GLPIWebhookResponse:
        """Process incoming GLPI webhook payload.

        Args:
            payload: Raw webhook payload from GLPI
            forward_to_alert: Whether to forward to alert service

        Returns:
            GLPIWebhookResponse with processing results
        """
        try:
            # Extract event type from common GLPI webhook fields
            event_type = self._extract_event_type(payload)

            # Parse common GLPI fields
            parsed = self._parse_glpi_payload(payload)

            # Create structured request
            request = GLPIWebhookRequest(
                event_type=event_type,
                raw_payload=payload,
                **parsed,
            )

            logger.info(f"Processed GLPI webhook: {event_type} - {parsed.get('name', 'N/A')}")

            alert_sent = False
            if forward_to_alert and self._auto_forward and self._alert_service:
                alert_sent = self._forward_to_alert(request)

            return GLPIWebhookResponse(
                ok=True,
                message=f"Processed {event_type} for item #{request.item_id}",
                processed=True,
                alert_sent=alert_sent,
            )

        except Exception as e:
            logger.error(f"Error processing GLPI webhook: {e}")
            return GLPIWebhookResponse(
                ok=False,
                error=str(e),
                processed=False,
            )

    def _extract_event_type(self, payload: dict[str, Any]) -> str | None:
        """Extract event type from various GLPI webhook formats."""
        # Direct event field
        if "event" in payload:
            return payload["event"]

        if "event_type" in payload:
            return payload["event_type"]

        if "type" in payload:
            return payload["type"]

        # Check for itemtype and id pattern
        if "itemtype" in payload or "item_type" in payload:
            item_type = payload.get("itemtype") or payload.get("item_type")
            action = payload.get("action", "created")
            return f"{item_type.lower()}.{action}"

        # Check for glpi event format
        if "glpi" in payload:
            glpi_data = payload.get("glpi", {})
            if "event" in glpi_data:
                return glpi_data["event"]

        return "unknown"

    def _parse_glpi_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Parse common GLPI fields from various webhook formats."""
        result = {}

        # Try common field mappings
        field_mappings = {
            "item_id": ["id", "item_id", "itemid", "ticket_id"],
            "item_type": ["itemtype", "item_type", "type", "object"],
            "name": ["name", "title", "subject", "name"],
            "status": ["status", "state", "statut"],
            "priority": ["priority", "urgency", "urgency_id"],
            "category": ["category", "category_id", "itilcategories_id", "type"],
            "entity": ["entity", "entity_id", "entities_id"],
            "requester": ["requester", "requester_id", "user_id", "author"],
            "assignee": ["assignee", "assigned_to", "tech_id", "assign_to_user"],
            "description": ["description", "content", "details", "body"],
            "date_creation": ["date_creation", "date_creation", "created_at", "created"],
            "date_mod": ["date_mod", "date_mod", "updated_at", "modified"],
        }

        for target, sources in field_mappings.items():
            for source in sources:
                if source in payload:
                    value = payload[source]
                    # Convert priority to int if possible
                    if target == "priority" and value is not None:
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            pass
                    result[target] = value
                    break

        return result

    def _forward_to_alert(self, request: GLPIWebhookRequest) -> bool:
        """Forward GLPI notification to configured alert channels."""
        if not self._alert_service:
            return False

        # Only forward certain event types
        if request.event_type not in self._forwardable_events:
            logger.debug(f"Skipping forward for event type: {request.event_type}")
            return False

        # Build alert message
        message = self._build_alert_message(request)

        # Send to both Slack and Discord
        try:
            result = self._alert_service.send(message, channel="both")
            # Check if at least one succeeded
            for channel, status in result.items():
                if status.get("status") == "success":
                    logger.info(f"GLPI alert forwarded to {channel}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to forward GLPI alert: {e}")
            return False

    def _build_alert_message(self, request: GLPIWebhookRequest) -> str:
        """Build alert message from GLPI webhook data."""
        parts = []

        # Event type with emoji
        event_emoji = self._get_event_emoji(request.event_type or "unknown")
        parts.append(f"{event_emoji} *{request.event_type or 'GLPI Event'}*")

        # Ticket/item info
        if request.item_id:
            parts.append(f"**Ticket #{request.item_id}**")

        if request.name:
            # Truncate long names
            name = request.name[:80] + "..." if len(request.name) > 80 else request.name
            parts.append(f"_{name}_")

        # Priority
        if request.priority is not None:
            priority_text = self._priority_emoji.get(request.priority, str(request.priority))
            parts.append(f"Priority: {priority_text}")

        # Status
        if request.status:
            parts.append(f"Status: {request.status}")

        # Category
        if request.category:
            parts.append(f"Category: {request.category}")

        # Requester
        if request.requester:
            parts.append(f"Requester: {request.requester}")

        # Assignee
        if request.assignee:
            parts.append(f"Assigned to: {request.assignee}")

        return " | ".join(parts)

    def _get_event_emoji(self, event_type: str) -> str:
        """Get emoji for event type."""
        emojis = {
            "ticket.created": "🆕",
            "ticket.updated": "🔄",
            "ticket.closed": "✅",
            "ticket.resolved": "✔️",
            "ticket.reply": "💬",
            "ticket.note": "📝",
            "ticket.assigned": "👤",
            "ticket.priority_changed": "⬆️",
            "ticket.status_changed": "📊",
        }
        return emojis.get(event_type, "🔔")


# Singleton instance (will be initialized in main.py)
_glpi_webhook_service: GLPIWebhookService | None = None


def get_glpi_webhook_service(alert_service: "AlertService | None" = None) -> GLPIWebhookService:
    """Get or create GLPI webhook service singleton."""
    global _glpi_webhook_service
    if _glpi_webhook_service is None:
        _glpi_webhook_service = GLPIWebhookService(alert_service=alert_service)
    return _glpi_webhook_service