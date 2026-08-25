from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class IndicatorType(str, Enum):
    DOMAIN = "DOMAIN"
    IP = "IP"
    URL = "URL"
    HASH = "HASH"


class ThreatLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ThreatIndicator(BaseModel):
    indicator: str
    indicator_type: IndicatorType

    threat_level: ThreatLevel

    source: str = "manual"

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )

    description: str | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )