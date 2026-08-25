from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    LOG = "LOG"
    MONITOR = "MONITOR"
    RATE_LIMIT = "RATE_LIMIT"
    ALERT = "ALERT"
    QUARANTINE = "QUARANTINE"
    BLOCK = "BLOCK"


class Severity(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TrafficEvent(BaseModel):
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    source_ip: str
    destination_ip: str | None = None

    source_port: int | None = None
    destination_port: int | None = None

    protocol: str

    domain: str | None = None
    query_type: str | None = None

    bytes_sent: int = 0
    bytes_received: int = 0

    packets_sent: int = 0
    packets_received: int = 0

    duration_ms: float = 0.0

    threat_intel_score: float = 0.0
    ml_score: float = 0.0
    risk_score: float = 0.0

    severity: Severity = Severity.INFORMATIONAL
    verdict: Verdict = Verdict.ALLOW

    reason: str | None = None