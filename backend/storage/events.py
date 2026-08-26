from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from backend.core.models import TrafficEvent


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "sentinel_dns.db"

_db_lock = Lock()


def _connect():
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    with _db_lock:
        connection = _connect()

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dns_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source_ip TEXT,
                domain TEXT,
                query_type TEXT,
                threat_intel_score REAL DEFAULT 0,
                ml_score REAL DEFAULT 0,
                risk_score REAL DEFAULT 0,
                severity TEXT,
                verdict TEXT,
                reason TEXT
            )
            """
        )

        connection.commit()
        connection.close()


def record_event(event: TrafficEvent):
    with _db_lock:
        connection = _connect()

        connection.execute(
            """
            INSERT INTO dns_events (
                timestamp,
                source_ip,
                domain,
                query_type,
                threat_intel_score,
                ml_score,
                risk_score,
                severity,
                verdict,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.timestamp.isoformat(),
                event.source_ip,
                event.domain,
                event.query_type,
                event.threat_intel_score,
                event.ml_score,
                event.risk_score,
                event.severity.value,
                event.verdict.value,
                event.reason,
            ),
        )

        connection.commit()
        connection.close()


def get_recent_events(limit: int = 100):
    initialize_database()

    with _db_lock:
        connection = _connect()

        rows = connection.execute(
            """
            SELECT *
            FROM dns_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        connection.close()

    return [dict(row) for row in rows]


def get_stats():
    initialize_database()

    with _db_lock:
        connection = _connect()

        total = connection.execute(
            "SELECT COUNT(*) FROM dns_events"
        ).fetchone()[0]

        blocked = connection.execute(
            "SELECT COUNT(*) FROM dns_events WHERE verdict = 'BLOCK'"
        ).fetchone()[0]

        alerts = connection.execute(
            """
            SELECT COUNT(*)
            FROM dns_events
            WHERE verdict IN ('ALERT', 'QUARANTINE')
            """
        ).fetchone()[0]

        dga = connection.execute(
            """
            SELECT COUNT(*)
            FROM dns_events
            WHERE reason LIKE '%DGA%'
            """
        ).fetchone()[0]

        tunneling = connection.execute(
            """
            SELECT COUNT(*)
            FROM dns_events
            WHERE reason LIKE '%TUNNELING%'
            """
        ).fetchone()[0]

        threat_intel = connection.execute(
            """
            SELECT COUNT(*)
            FROM dns_events
            WHERE threat_intel_score > 0
            """
        ).fetchone()[0]

        connection.close()

    return {
        "total_queries": total,
        "blocked_queries": blocked,
        "alerts": alerts,
        "dga_detections": dga,
        "tunneling_detections": tunneling,
        "threat_intel_hits": threat_intel,
    }


initialize_database()
