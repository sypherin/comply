from __future__ import annotations
import logging
from typing import Optional, List

logger = logging.getLogger('graph')

class GraphClient:
    def __init__(self):
        logger.info('GraphClient running in offline stub mode.')
    def get_manager(self, email_or_id: str) -> Optional[str]:
        return None
    def send_mail(self, sender_user_id: str, to: List[str], cc: List[str], subject: str, html_body: str) -> str:
        logger.info('SIMULATED send_mail to=%s cc=%s subject=%s', to, cc, subject)
        return 'offline-simulated'
