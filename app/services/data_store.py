from __future__ import annotations
import logging
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any

logger = logging.getLogger('store')

class InMemoryStore:
    def __init__(self):
        self.reminders: List[Dict[str,Any]] = []
    def save_dataset(self, df: pd.DataFrame) -> int:
        return int(df.shape[0])
    def log_reminder_batch(self, actor_email: str, results: List[Dict[str,Any]]):
        ts = datetime.utcnow().isoformat()
        for r in results:
            self.reminders.append({'ts': ts, 'actor': actor_email, **r})
        logger.info('logged reminder batch size=%s (in-memory only, metadata)', len(results))
