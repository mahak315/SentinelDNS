import math
from collections import Counter


def shannon_entropy(value: str) -> float:
    """Calculate Shannon entropy of a string."""

    if not value:
        return 0.0

    counts = Counter(value)
    length = len(value)

    entropy = 0.0

    for count in counts.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return entropy


def extract_domain_features(domain: str) -> dict:
    """Extract ML features from a DNS domain."""

    domain = domain.rstrip(".").lower()

    labels = domain.split(".")

    tld = labels[-1] if labels else ""

    domain_without_tld = ".".join(labels[:-1])

    length = len(domain)

    digit_count = sum(
        character.isdigit()
        for character in domain
    )

    letter_count = sum(
        character.isalpha()
        for character in domain
    )

    hyphen_count = domain.count("-")

    underscore_count = domain.count("_")

    special_character_count = sum(
        not character.isalnum() and character != "."
        for character in domain
    )

    subdomain_count = max(
        len(labels) - 2,
        0,
    )

    unique_character_count = len(
        set(domain)
    )

    entropy = shannon_entropy(domain)

    return {
        "domain_length": length,
        "label_count": len(labels),
        "subdomain_count": subdomain_count,
        "digit_count": digit_count,
        "digit_ratio": digit_count / length if length else 0.0,
        "letter_count": letter_count,
        "letter_ratio": letter_count / length if length else 0.0,
        "hyphen_count": hyphen_count,
        "underscore_count": underscore_count,
        "special_character_count": special_character_count,
        "unique_character_count": unique_character_count,
        "unique_character_ratio": (
            unique_character_count / length
            if length
            else 0.0
        ),
        "entropy": entropy,
        "tld_length": len(tld),
        "domain_without_tld_length": len(
            domain_without_tld
        ),
    }

from backend.core.models import TrafficEvent


def extract_traffic_features(event: TrafficEvent) -> dict:
    """
    Extract ML features from a SentinelDNS TrafficEvent.
    """

    features = extract_domain_features(event.domain)

    features.update(
        {
            "bytes_sent": event.bytes_sent,
            "bytes_received": event.bytes_received,
            "packets_sent": event.packets_sent,
            "packets_received": event.packets_received,
            "duration_ms": event.duration_ms,
        }
    )

    return features