from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
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

        # Seed initial logs if empty
        cursor = connection.execute("SELECT COUNT(*) FROM dns_events")
        if cursor.fetchone()[0] == 0:
            now = datetime.now(timezone.utc)
            mock_entries = [
                ((now - timedelta(minutes=2)).isoformat(), "192.168.1.15", "google.com", "A", 0.0, 0.01, 0.005, "INFORMATIONAL", "ALLOW", "Clean domain request"),
                ((now - timedelta(minutes=8)).isoformat(), "192.168.1.20", "malware.test", "A", 1.0, 0.95, 0.98, "CRITICAL", "BLOCK", "Threat intelligence block: malicious domain"),
                ((now - timedelta(minutes=15)).isoformat(), "192.168.1.10", "suspicious.test", "AAAA", 0.8, 0.65, 0.74, "HIGH", "BLOCK", "ML detected suspicious behavior"),
                ((now - timedelta(hours=1)).isoformat(), "192.168.1.15", "github.com", "A", 0.0, 0.02, 0.01, "INFORMATIONAL", "ALLOW", "Clean domain request"),
                ((now - timedelta(hours=2)).isoformat(), "192.168.1.32", "phishing.test", "TXT", 0.95, 0.88, 0.91, "HIGH", "BLOCK", "Threat intelligence match: phishing indicator"),
                ((now - timedelta(hours=5)).isoformat(), "192.168.1.10", "netflix.com", "A", 0.0, 0.0, 0.0, "INFORMATIONAL", "ALLOW", "Clean domain request")
            ]
            connection.executemany(
                """
                INSERT INTO dns_events (
                    timestamp, source_ip, domain, query_type,
                    threat_intel_score, ml_score, risk_score,
                    severity, verdict, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                mock_entries
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


def get_connected_devices():
    initialize_database()

    with _db_lock:
        connection = _connect()
        rows = connection.execute(
            """
            SELECT 
                source_ip,
                MAX(timestamp) as last_active,
                SUM(CASE WHEN verdict = 'BLOCK' THEN 1 ELSE 0 END) as threats_blocked,
                COUNT(*) as total_queries
            FROM dns_events
            GROUP BY source_ip
            ORDER BY last_active DESC
            """
        ).fetchall()
        connection.close()

    friendly_names = {
        "127.0.0.1": "SentinelDNS Host Gateway",
        "192.168.1.10": "SecOps Administrator Workstation",
        "192.168.1.15": "Corporate Employee Laptop",
        "192.168.1.20": "External Partner Terminal",
        "192.168.1.32": "IoT Smart Camera Sensor"
    }

    devices = []
    now = datetime.now(timezone.utc)
    for row in rows:
        ip = row["source_ip"] or "unknown"
        last_active_str = row["last_active"]

        status = "offline"
        try:
            last_active_dt = datetime.fromisoformat(last_active_str)
            if last_active_dt.tzinfo is None:
                last_active_dt = last_active_dt.replace(tzinfo=timezone.utc)

            diff = now - last_active_dt
            if diff.total_seconds() < 600:  # 10 mins
                status = "online"
            elif diff.total_seconds() < 3600:  # 1 hour
                status = "idle"
        except Exception:
            pass

        devices.append({
            "ip": ip,
            "device_name": friendly_names.get(ip, f"DHCP Network Device ({ip.split('.')[-1]})" if "." in ip else "Network Device"),
            "status": status,
            "last_active": last_active_str,
            "threats_blocked": row["threats_blocked"],
            "total_queries": row["total_queries"]
        })

    return devices


initialize_database()
