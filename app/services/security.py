from __future__ import annotations
import re
import pandas as pd

NRIC_PATTERN = re.compile(r"\b[STFG]\d{7}[A-Z]\b", re.IGNORECASE)

def scan_csv_basic(df: pd.DataFrame):
    if df.shape[0] > 200000:
        raise ValueError('CSV too large; please split into smaller files.')
    sample_text = ' '.join([str(x) for x in df.head(100).astype(str).values.flatten()])
    if NRIC_PATTERN.search(sample_text):
        raise ValueError('Detected NRIC-like identifiers — remove before upload.')

def sanitize_text(s: str) -> str:
    return (s or '').replace('\x00', '').strip()
