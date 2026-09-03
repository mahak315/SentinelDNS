import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly on Linux
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.intelligence.models import (
    IndicatorType,
    ThreatIndicator,
    ThreatLevel,
)

from backend.intelligence.service import (
    ThreatIntelligenceService,
)


def main() -> None:

    service = ThreatIntelligenceService()

    indicators = [
        ThreatIndicator(
            indicator="malware.test",
            indicator_type=IndicatorType.DOMAIN,
            threat_level=ThreatLevel.CRITICAL,
            confidence=1.0,
            source="sentineldns-test",
            description="Test malicious domain",
        ),
        ThreatIndicator(
            indicator="phishing.test",
            indicator_type=IndicatorType.DOMAIN,
            threat_level=ThreatLevel.HIGH,
            confidence=0.95,
            source="sentineldns-test",
            description="Test phishing domain",
        ),
        ThreatIndicator(
            indicator="suspicious.test",
            indicator_type=IndicatorType.DOMAIN,
            threat_level=ThreatLevel.MEDIUM,
            confidence=0.80,
            source="sentineldns-test",
            description="Test suspicious domain",
        ),
    ]

    for indicator in indicators:
        service.add_indicator(indicator)

        print(
            f"Added: {indicator.indicator}"
        )


if __name__ == "__main__":
    main()