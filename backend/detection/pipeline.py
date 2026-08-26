from backend.core.models import TrafficEvent
from backend.detection.risk import calculate_risk
from backend.detection.response import (
    determine_severity,
    determine_verdict,
)
from backend.intelligence.models import IndicatorType
from backend.intelligence.service import (
    ThreatIntelligenceService,
)


threat_intelligence = ThreatIntelligenceService()


def analyze_event(
    event: TrafficEvent,
    ml_score: float,
    threat_intel_score: float | None = None,
) -> TrafficEvent:
    """
    Analyze a DNS/network event.

    Threat intelligence is automatically checked using
    the domain contained in the event.
    """

    if threat_intel_score is None:
        threat_intel_score = 0.0
        if event.domain:
            threat_intel_score = (
                threat_intelligence.get_score(
                    event.domain,
                    IndicatorType.DOMAIN,
                )
            )

    risk_score = calculate_risk(
        threat_intel_score=threat_intel_score,
        ml_score=ml_score,
    )

    severity = determine_severity(
        risk_score
    )

    verdict = determine_verdict(
        risk_score
    )

    event.threat_intel_score = threat_intel_score
    event.ml_score = ml_score
    event.risk_score = risk_score
    event.severity = severity
    event.verdict = verdict

    return event