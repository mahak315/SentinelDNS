from backend.core.models import TrafficEvent
from backend.detection.risk import calculate_risk
from backend.detection.response import (
    determine_severity,
    determine_verdict,
)


def analyze_event(
    event: TrafficEvent,
    threat_intel_score: float,
    ml_score: float,
) -> TrafficEvent:
    """
    Analyze a network event and determine its
    risk, severity, and response.
    """

    risk_score = calculate_risk(
        threat_intel_score=threat_intel_score,
        ml_score=ml_score,
    )

    severity = determine_severity(risk_score)

    verdict = determine_verdict(risk_score)

    event.threat_intel_score = threat_intel_score
    event.ml_score = ml_score
    event.risk_score = risk_score
    event.severity = severity
    event.verdict = verdict

    return event