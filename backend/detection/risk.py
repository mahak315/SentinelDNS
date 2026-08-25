def calculate_risk(
    threat_intel_score: float,
    ml_score: float,
) -> float:
    """
    Calculate a normalized threat risk score between 0 and 1.

    Threat intelligence has a higher weight because
    a known malicious indicator is stronger evidence
    than an ML prediction alone.
    """

    risk = (
        0.60 * threat_intel_score
        + 0.40 * ml_score
    )

    return max(0.0, min(1.0, risk))