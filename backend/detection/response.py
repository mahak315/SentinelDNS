from backend.core.models import Severity, Verdict


def determine_severity(risk_score: float) -> Severity:
    """
    Convert the numerical risk score into a severity level.
    """

    if risk_score >= 0.90:
        return Severity.CRITICAL

    if risk_score >= 0.60:
        return Severity.HIGH

    if risk_score >= 0.30:
        return Severity.MEDIUM

    if risk_score >= 0.15:
        return Severity.LOW

    return Severity.INFORMATIONAL


def determine_verdict(risk_score: float) -> Verdict:
    """
    Convert the numerical risk score into a response action.

    This is the baseline response policy.
    The reinforcement-learning agent will eventually
    learn to make this decision adaptively.
    """

    if risk_score >= 0.90:
        return Verdict.BLOCK

    if risk_score >= 0.75:
        return Verdict.QUARANTINE

    if risk_score >= 0.60:
        return Verdict.ALERT

    if risk_score >= 0.45:
        return Verdict.RATE_LIMIT

    if risk_score >= 0.30:
        return Verdict.MONITOR

    if risk_score >= 0.15:
        return Verdict.LOG

    return Verdict.ALLOW