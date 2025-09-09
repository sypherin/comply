from __future__ import annotations
import os
import logging
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("store")

class InMemoryStore:
    def __init__(self):
        self.reminders: List[Dict[str,Any]] = []

    def save_dataset(self, df: pd.DataFrame) -> int:
        return int(df.shape[0])

    def log_reminder_batch(self, actor_email: str, results: List[Dict[str,Any]]):
        ts = datetime.utcnow().isoformat()
        for r in results:
            self.reminders.append({"ts": ts, "actor": actor_email, **r})
        logger.info("logged reminder batch size=%s (in-memory only, metadata)", len(results))

def _build_conn_str() -> str:
    server = os.getenv("SQL_SERVER")
    db = os.getenv("SQL_DATABASE")
    user = os.getenv("SQL_USERNAME")
    pwd = os.getenv("SQL_PASSWORD")
    if user and pwd:
        return f"mssql+pyodbc://{user}:{pwd}@{server}:1433/{db}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
    return f"mssql+pyodbc://@{server}:1433/{db}?driver=ODBC+Driver+18+for+SQL+Server&authentication=ActiveDirectoryMsi&Encrypt=yes&TrustServerCertificate=no"

def get_sql_engine() -> Engine:
    return create_engine(_build_conn_str(), pool_pre_ping=True, pool_recycle=1800, fast_executemany=True)

class SqlStore:
    def __init__(self, engine: Engine, retention_days: int = 90):
        self.engine = engine
        self.retention_days = retention_days
        self._init()

    def _init(self):
        with self.engine.begin() as conn:
            conn.execute(text("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'reminder_logs')
            CREATE TABLE reminder_logs (
                id INT IDENTITY(1,1) PRIMARY KEY,
                ts DATETIME2 NOT NULL,
                actor NVARCHAR(256) NOT NULL,
                recipient NVARCHAR(256) NOT NULL,
                cc NVARCHAR(512) NULL,
                course_count INT NOT NULL,
                status NVARCHAR(64) NOT NULL,
                message_id NVARCHAR(256) NULL
            )
            """))
            conn.execute(text("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'datasets')
            CREATE TABLE datasets (
                id INT IDENTITY(1,1) PRIMARY KEY,
                ts DATETIME2 NOT NULL,
                row_count INT NOT NULL,
                org NVARCHAR(128) NULL
            )
            """))

    def save_dataset(self, df: pd.DataFrame) -> int:
        with self.engine.begin() as conn:
            org_val = None
            if "Org" in df.columns and not df["Org"].empty:
                try:
                    org_val = str(df["Org"].mode().iloc[0])
                except Exception:
                    org_val = None
            conn.execute(text("INSERT INTO datasets(ts, row_count, org) VALUES (SYSUTCDATETIME(), :n, :org)"),
                         {"n": int(df.shape[0]), "org": org_val})
        return int(df.shape[0])

    def log_reminder_batch(self, actor_email: str, results):
        with self.engine.begin() as conn:
            for r in results or []:
                cc_str = ",".join(r.get("cc",[])) if isinstance(r.get("cc"), list) else (r.get("cc") or "")
                conn.execute(text("""
                    INSERT INTO reminder_logs(ts, actor, recipient, cc, course_count, status, message_id)
                    VALUES (SYSUTCDATETIME(), :actor, :rcpt, :cc, :cnt, :status, :mid)
                """), {
                    "actor": actor_email,
                    "rcpt": r.get("email",""),
                    "cc": cc_str,
                    "cnt": int(r.get("course_count", 0)),
                    "status": r.get("status",""),
                    "mid": r.get("id","")
                })
        logger.info("logged %s reminder items (metadata only)", len(results or []))

    def purge_old(self):
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM reminder_logs WHERE ts < DATEADD(DAY, -:d, SYSUTCDATETIME())"), {"d": int(self.retention_days)})
            conn.execute(text("DELETE FROM datasets WHERE ts < DATEADD(DAY, -:d, SYSUTCDATETIME())"), {"d": int(self.retention_days)})
        logger.info("purge executed for retention=%s days", self.retention_days)
