from __future__ import annotations
import os, logging

def setup_logging():
    level = os.getenv('LOG_LEVEL','INFO').upper()
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(name)s - %(message)s')
