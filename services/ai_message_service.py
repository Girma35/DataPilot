"""AI-powered message generation service for GLPI tickets."""

from __future__ import annotations

import logging
import re
from typing import Any

from openai import OpenAI


def _strip_desc(text: str, max_len: int) -> str:
    t = re.sub(r"<[^>]+>", " ", str(text))
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > max_len:
        t = t[: max_len - 1] + "…"
    return t

from config import OPENAI_API_KEY, LLM_PROVIDER, LLM_MODEL

logger = logging.getLogger(__name__)


class AIMessageService:
    """Service to generate AI-powered messages from ticket data."""

    def __init__(self, api_key: str | None = None) -> None:
        provider = LLM_PROVIDER.lower() if LLM_PROVIDER else "openai"
        
        if provider == "groq":
            self._client = OpenAI(
                api_key=api_key or OPENAI_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
        else:
            self._client = OpenAI(api_key=api_key or OPENAI_API_KEY)
        
        self._model = LLM_MODEL or "gpt-4o-mini"

    def generate_ticket_message(self, ticket_data: dict[str, Any]) -> str:
        """Generate a smart message from ticket data using OpenAI.

        Args:
            ticket_data: Dictionary containing ticket information

        Returns:
            A short, actionable message suitable for Slack/Discord
        """
        if not OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not configured, using fallback message")
            return self._generate_fallback_message(ticket_data)

        try:
            return self._generate_ai_message(ticket_data)
        except Exception as e:
            logger.error(f"Error generating AI message: {e}")
            return self._generate_fallback_message(ticket_data)

    def _generate_ai_message(self, ticket_data: dict[str, Any]) -> str:
        """Generate message using OpenAI."""
        ticket_info = self._format_ticket_info(ticket_data)

        system_prompt = """You are a helpful IT operations assistant.
Write a short summary (2–4 sentences, under 400 characters) for a GLPI ticket notification.
Cover: what is wrong or requested, urgency/priority, and requester or assignee if known.
The full ticket description will be shown separately in the same alert — do not repeat long text.
Use at most one emoji. No markdown headings."""

        user_prompt = f"""Ticket context:
{ticket_info}

Reply with only the summary text, no preamble."""

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=100,
            temperature=0.7,
        )

        message = response.choices[0].message.content.strip()
        return message

    def _format_ticket_info(self, ticket_data: dict[str, Any]) -> str:
        """Format ticket data for the AI prompt."""
        parts = []
        
        if ticket_data.get("name"):
            parts.append(f"Title: {ticket_data['name']}")
        if ticket_data.get("description"):
            # Truncate long descriptions
            desc = ticket_data["description"][:500]
            parts.append(f"Description: {desc}")
        if ticket_data.get("priority"):
            priority_map = {1: "Low", 2: "Medium", 3: "High", 4: "Critical", 5: "Emergency"}
            priority = priority_map.get(ticket_data["priority"], "Unknown")
            parts.append(f"Priority: {priority} ({ticket_data['priority']}/5)")
        if ticket_data.get("status"):
            parts.append(f"Status: {ticket_data['status']}")
        if ticket_data.get("category"):
            parts.append(f"Category: {ticket_data['category']}")
        if ticket_data.get("requester"):
            parts.append(f"Requester: {ticket_data['requester']}")
        if ticket_data.get("assignee"):
            parts.append(f"Assigned to: {ticket_data['assignee']}")
        
        return "\n".join(parts) if parts else "No details available"

    def _generate_fallback_message(self, ticket_data: dict[str, Any]) -> str:
        """Generate a basic message without AI."""
        parts = ["New GLPI Ticket"]

        if ticket_data.get("name"):
            name = ticket_data["name"][:80] + "..." if len(ticket_data["name"]) > 80 else ticket_data["name"]
            parts.append(name)

        if ticket_data.get("description"):
            desc = _strip_desc(ticket_data["description"], 200)
            parts.append(desc)

        if ticket_data.get("priority"):
            priority_emoji = {1: " Low", 2: " Medium", 3: " High", 4: " Critical", 5: " Emergency"}
            parts.append(f"Priority: {priority_emoji.get(ticket_data['priority'], '')}")

        if ticket_data.get("category"):
            parts.append(f"Category: {ticket_data['category']}")

        if ticket_data.get("requester"):
            parts.append(f"From: {ticket_data['requester']}")

        return " | ".join(parts)


# Singleton instance
_ai_message_service: AIMessageService | None = None


def get_ai_message_service() -> AIMessageService:
    """Get or create AI message service singleton."""
    global _ai_message_service
    if _ai_message_service is None:
        _ai_message_service = AIMessageService()
    return _ai_message_service