from __future__ import annotations
import os
import logging
from typing import Optional, List

OFFLINE_MODE = os.getenv("OFFLINE_MODE", "false").lower() == "true"
logger = logging.getLogger("graph")

if OFFLINE_MODE:
    # ---------- DEAD-END / OFFLINE STUB ----------
    class GraphClient:
        """No-network stub: never calls MSAL or Graph."""
        def __init__(self):  # no config needed
            logger.info("GraphClient in OFFLINE_MODE=true (no network calls).")

        def get_manager(self, email_or_id: str) -> Optional[str]:
            # No directory lookups offline
            return None

        def send_mail(self, sender_user_id: str, to: List[str], cc: List[str], subject: str, html_body: str) -> str:
            logger.info("OFFLINE send_mail simulated to=%s cc=%s subject=%s", to, cc, subject)
            return "offline-simulated"
else:
    # ---------- REAL IMPLEMENTATION (will use MSAL token) ----------
    import requests
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    from app.services.auth_msal import get_access_token

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    class GraphClient:
        def __init__(self):
            pass

        def _get_headers(self) -> dict:
            token = get_access_token(os.getenv("GRAPH_SCOPES", "User.Read Mail.Send Directory.Read.All").split())
            return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        def get_manager(self, email_or_id: str) -> Optional[str]:
            url = f"{GRAPH_BASE}/users/{email_or_id}/manager?$select=userPrincipalName,mail"
            resp = requests.get(url, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("mail") or data.get("userPrincipalName")
            elif resp.status_code == 404:
                return None
            else:
                logger.warning("manager lookup failed status=%s", resp.status_code)
                return None

        @retry(
            reraise=True,
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=1, max=20),
            retry=retry_if_exception_type(Exception),
        )
        def send_mail(self, sender_user_id: str, to: List[str], cc: List[str], subject: str, html_body: str) -> str:
            endpoint = (
                f"{GRAPH_BASE}/me/sendMail"
                if sender_user_id in ("", "me", None)
                else f"{GRAPH_BASE}/users/{sender_user_id}/sendMail"
            )
            payload = {
                "message": {
                    "subject": subject,
                    "body": {"contentType": "HTML", "content": html_body},
                    "toRecipients": [{"emailAddress": {"address": x}} for x in to],
                    "ccRecipients": [{"emailAddress": {"address": x}} for x in cc] if cc else [],
                },
                "saveToSentItems": "true",
            }
            headers = self._get_headers()
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=15)
            if resp.status_code in (202, 200):
                logger.info("send_mail ok to=%s cc=%s", to, cc)
                return resp.headers.get("x-ms-ags-diagnostic", "")
            logger.warning("send_mail failed status=%s to=%s cc=%s", resp.status_code, to, cc)
            resp.raise_for_status()
            return ""
