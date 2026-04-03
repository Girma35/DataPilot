"""GLPI REST API (apirest.php) — session + ticket follow-up / status updates."""

from __future__ import annotations

import html
import logging
from typing import Any

import requests

from config import GLPI_API_URL, GLPI_APP_TOKEN, GLPI_USER_TOKEN

logger = logging.getLogger(__name__)


def _response_json(r: requests.Response) -> Any:
    if not r.text:
        return {}
    try:
        return r.json()
    except ValueError:
        return {"message": (r.text or "")[:1000]}


def _as_dict(j: Any) -> dict[str, Any]:
    """GLPI sometimes returns JSON arrays e.g. ['ERROR','API disabled']."""
    if isinstance(j, dict):
        return j
    return {"message": str(j), "_raw": j}


class GLPIApiService:
    """Minimal GLPI 9.x/10.x API client for ticket updates after webhook processing."""

    def __init__(
        self,
        base_url: str | None = None,
        app_token: str | None = None,
        user_token: str | None = None,
    ) -> None:
        self._base = (base_url or GLPI_API_URL or "").rstrip("/")
        self._app_token = app_token or GLPI_APP_TOKEN
        self._user_token = user_token or GLPI_USER_TOKEN

    def is_configured(self) -> bool:
        return bool(self._base and self._app_token and self._user_token)

    def _headers(self, session_token: str | None = None) -> dict[str, str]:
        h: dict[str, str] = {
            "Content-Type": "application/json",
            "App-Token": self._app_token,
        }
        if session_token:
            h["Session-Token"] = session_token
        else:
            h["Authorization"] = f"user_token {self._user_token}"
        return h

    def init_session(self) -> dict[str, Any]:
        if not self.is_configured():
            return {"ok": False, "error": "GLPI API not configured (GLPI_API_URL, GLPI_APP_TOKEN, GLPI_USER_TOKEN)"}
        try:
            r = requests.get(
                f"{self._base}/initSession",
                headers=self._headers(session_token=None),
                timeout=30,
            )
            raw = _response_json(r)
            data = _as_dict(raw)
            if r.ok and isinstance(raw, dict) and raw.get("session_token"):
                return {"ok": True, "session_token": raw["session_token"]}
            logger.warning("GLPI initSession failed: %s %s", r.status_code, raw)
            err = data.get("message") or data.get("error") or raw
            return {"ok": False, "error": err if isinstance(err, str) else str(err)}
        except requests.RequestException as e:
            logger.error("GLPI initSession request error: %s", e)
            return {"ok": False, "error": str(e)}

    def kill_session(self, session_token: str) -> None:
        try:
            requests.get(
                f"{self._base}/killSession",
                headers=self._headers(session_token=session_token),
                timeout=15,
            )
        except requests.RequestException:
            pass

    def add_ticket_followup(
        self,
        ticket_id: int,
        text: str,
        *,
        is_private: bool = False,
    ) -> dict[str, Any]:
        """Add a public (or private) follow-up to a ticket."""
        session = self.init_session()
        if not session.get("ok"):
            return session
        st = session["session_token"]
        try:
            safe = html.escape(text).replace("\n", "<br />")
            body = {
                "input": {
                    "itemtype": "Ticket",
                    "items_id": ticket_id,
                    "content": f"<p>{safe}</p>",
                    "is_private": 1 if is_private else 0,
                }
            }
            data: dict[str, Any] = {}
            last_status = 0
            for url in (
                f"{self._base}/ITILFollowup",
                f"{self._base}/ITILFollowup/",
                f"{self._base}/Ticket/{ticket_id}/ITILFollowup",
            ):
                r = requests.post(
                    url,
                    headers=self._headers(session_token=st),
                    json=body,
                    timeout=30,
                )
                last_status = r.status_code
                raw = _response_json(r)
                data = _as_dict(raw)
                if r.ok and isinstance(raw, dict):
                    return {"ok": True, "id": raw.get("id"), "raw": raw}
                if r.status_code == 404:
                    continue
                break
            logger.warning("GLPI ITILFollowup failed: %s %s", last_status, raw)
            return {
                "ok": False,
                "error": data.get("message") or data.get("error") or str(raw),
                "status": last_status,
            }
        finally:
            self.kill_session(st)

    def update_ticket_status(self, ticket_id: int, status_id: int) -> dict[str, Any]:
        """Set ticket status (IDs are instance-specific, e.g. 2 = processing)."""
        session = self.init_session()
        if not session.get("ok"):
            return session
        st = session["session_token"]
        try:
            body = {"input": {"id": ticket_id, "status": status_id}}
            r = requests.put(
                f"{self._base}/Ticket/{ticket_id}",
                headers=self._headers(session_token=st),
                json=body,
                timeout=30,
            )
            raw = _response_json(r)
            data = _as_dict(raw)
            if r.ok:
                return {"ok": True, "raw": raw}
            logger.warning("GLPI Ticket PUT failed: %s %s", r.status_code, raw)
            return {
                "ok": False,
                "error": data.get("message") or data.get("error") or r.text,
                "status": r.status_code,
            }
        finally:
            self.kill_session(st)

    def create_ticket(
        self,
        name: str,
        content: str,
        *,
        urgency: int = 3,
        impact: int = 3,
        itilcategories_id: int | None = None,
    ) -> dict[str, Any]:
        """Create a new Ticket (HTML content)."""
        session = self.init_session()
        if not session.get("ok"):
            return session
        st = session["session_token"]
        try:
            safe = html.escape(content).replace("\n", "<br />")
            inp: dict[str, Any] = {
                "name": name[:255],
                "content": f"<p>{safe}</p>",
                "urgency": urgency,
                "impact": impact,
            }
            if itilcategories_id is not None:
                inp["itilcategories_id"] = itilcategories_id
            r = requests.post(
                f"{self._base}/Ticket",
                headers=self._headers(session_token=st),
                json={"input": inp},
                timeout=30,
            )
            raw = _response_json(r)
            data = _as_dict(raw)
            if r.ok:
                tid = raw.get("id") if isinstance(raw, dict) else None
                return {"ok": True, "id": tid, "raw": raw}
            logger.warning("GLPI Ticket POST failed: %s %s", r.status_code, raw)
            return {
                "ok": False,
                "error": data.get("message") or data.get("error") or r.text,
                "status": r.status_code,
            }
        finally:
            self.kill_session(st)

    def update_ticket(self, ticket_id: int, fields: dict[str, Any]) -> dict[str, Any]:
        """Partial update (e.g. status, urgency, impact). Always includes id."""
        session = self.init_session()
        if not session.get("ok"):
            return session
        st = session["session_token"]
        try:
            inp = {"id": ticket_id, **fields}
            r = requests.put(
                f"{self._base}/Ticket/{ticket_id}",
                headers=self._headers(session_token=st),
                json={"input": inp},
                timeout=30,
            )
            raw = _response_json(r)
            data = _as_dict(raw)
            if r.ok:
                return {"ok": True, "raw": raw}
            logger.warning("GLPI Ticket PUT failed: %s %s", r.status_code, raw)
            return {
                "ok": False,
                "error": data.get("message") or data.get("error") or r.text,
                "status": r.status_code,
            }
        finally:
            self.kill_session(st)


_glpi_api: GLPIApiService | None = None


def get_glpi_api_service() -> GLPIApiService:
    global _glpi_api
    if _glpi_api is None:
        _glpi_api = GLPIApiService()
    return _glpi_api
