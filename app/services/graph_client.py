# app/services/graph_client.py
from __future__ import annotations
import logging
from typing import Optional, List

logger = logging.getLogger("graph")

class GraphClient:
    """Offline stub: no MSAL, no HTTP."""
    def __init__(self):
        logger.info("GraphClient running in offline stub mode.")

    def get_manager(self, email_or_id: str) -> Optional[str]:
        return None

    def send_mail(self, sender_user_id: str, to: List[str], cc: List[str], subject: str, html_body: str) -> str:
        logger.info("OFFLINE send_mail simulated to=%s cc=%s subject=%s", to, cc, subject)
        return "offline-simulated"
