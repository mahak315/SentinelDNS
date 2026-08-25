from datetime import datetime, timezone

from backend.intelligence.database import (
    get_connection,
    initialize_database,
)
from backend.intelligence.models import (
    IndicatorType,
    ThreatIndicator,
    ThreatLevel,
)


THREAT_LEVEL_SCORES = {
    ThreatLevel.LOW: 0.40,
    ThreatLevel.MEDIUM: 0.60,
    ThreatLevel.HIGH: 0.80,
    ThreatLevel.CRITICAL: 1.00,
}


class ThreatIntelligenceService:

    def __init__(self) -> None:
        initialize_database()

    def add_indicator(
        self,
        indicator: ThreatIndicator,
    ) -> None:

        connection = get_connection()

        connection.execute(
            """
            INSERT INTO indicators (
                indicator,
                indicator_type,
                threat_level,
                source,
                confidence,
                description,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(indicator, indicator_type)
            DO UPDATE SET
                threat_level = excluded.threat_level,
                source = excluded.source,
                confidence = excluded.confidence,
                description = excluded.description
            """,
            (
                indicator.indicator,
                indicator.indicator_type.value,
                indicator.threat_level.value,
                indicator.source,
                indicator.confidence,
                indicator.description,
                indicator.created_at.isoformat(),
            ),
        )

        connection.commit()
        connection.close()

    def lookup(
        self,
        indicator: str,
        indicator_type: IndicatorType,
    ) -> ThreatIndicator | None:

        connection = get_connection()

        row = connection.execute(
            """
            SELECT
                indicator,
                indicator_type,
                threat_level,
                source,
                confidence,
                description,
                created_at
            FROM indicators
            WHERE indicator = ?
              AND indicator_type = ?
            """,
            (
                indicator,
                indicator_type.value,
            ),
        ).fetchone()

        connection.close()

        if row is None:
            return None

        return ThreatIndicator(
            indicator=row["indicator"],
            indicator_type=IndicatorType(
                row["indicator_type"]
            ),
            threat_level=ThreatLevel(
                row["threat_level"]
            ),
            source=row["source"],
            confidence=row["confidence"],
            description=row["description"],
            created_at=datetime.fromisoformat(
                row["created_at"]
            ),
        )

    def get_score(
        self,
        indicator: str,
        indicator_type: IndicatorType,
    ) -> float:

        result = self.lookup(
            indicator,
            indicator_type,
        )

        if result is None:
            return 0.0

        base_score = THREAT_LEVEL_SCORES[
            result.threat_level
        ]

        return min(
            1.0,
            base_score * result.confidence,
        )