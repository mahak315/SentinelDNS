import pytest

from backend.core.models import TrafficEvent, Verdict
from backend.detection.pipeline import analyze_event


@pytest.mark.parametrize(
    ("score", "expected_verdict"),
    [
        (0.05, Verdict.ALLOW),
        (0.20, Verdict.LOG),
        (0.35, Verdict.MONITOR),
        (0.50, Verdict.RATE_LIMIT),
        (0.65, Verdict.ALERT),
        (0.80, Verdict.QUARANTINE),
        (0.95, Verdict.BLOCK),
    ],
)
def test_response_levels(score, expected_verdict):
    event = TrafficEvent(
        source_ip="192.168.1.10",
        destination_ip="8.8.8.8",
        protocol="UDP",
        domain="example.com",
    )

    result = analyze_event(
        event,
        threat_intel_score=score,
        ml_score=score,
    )

    assert result.risk_score == pytest.approx(score)
    assert result.verdict == expected_verdict