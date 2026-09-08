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
    Extract the feature schema expected by the DNS exfiltration model.

    Features that are not currently captured by TrafficEvent (such as
    TTL/A-record statistics and packet-length distributions) are represented
    as 0 until packet/response telemetry is added to the resolver.
    """

    domain = (event.domain or "").rstrip(".").lower()

    labels = domain.split(".") if domain else []
    domain_without_tld = ".".join(labels[:-1]) if len(labels) > 1 else ""
    subdomain = ".".join(labels[:-2]) if len(labels) > 2 else ""

    length = len(domain)

    digit_count = sum(c.isdigit() for c in domain)
    numerical_percentage = (
        digit_count / length * 100.0
        if length else 0.0
    )

    letters = [c for c in domain if c.isalpha()]
    vowels = sum(c in "aeiou" for c in letters)
    consonants = sum(
        c.isalpha() and c not in "aeiou"
        for c in domain
    )

    max_numeric = 0
    max_alpha = 0
    max_consonants = 0
    max_same_alpha = 0

    current_numeric = 0
    current_alpha = 0
    current_consonants = 0
    current_same_alpha = 0
    previous_alpha = None

    for c in domain:
        if c.isdigit():
            current_numeric += 1
        else:
            current_numeric = 0

        if c.isalpha():
            current_alpha += 1
            if c.lower() == previous_alpha:
                current_same_alpha += 1
            else:
                current_same_alpha = 1
            previous_alpha = c.lower()
        else:
            current_alpha = 0
            current_same_alpha = 0
            previous_alpha = None

        if c.isalpha() and c not in "aeiou":
            current_consonants += 1
        else:
            current_consonants = 0

        max_numeric = max(max_numeric, current_numeric)
        max_alpha = max(max_alpha, current_alpha)
        max_consonants = max(max_consonants, current_consonants)
        max_same_alpha = max(max_same_alpha, current_same_alpha)

    duration = max(float(event.duration_ms) / 1000.0, 0.0)
    total_bytes = event.bytes_sent + event.bytes_received
    total_packets = event.packets_sent + event.packets_received

    packets_rate = (
        total_packets / duration
        if duration > 0 else 0.0
    )

    packets_len_rate = (
        total_bytes / total_packets
        if total_packets > 0 else 0.0
    )

    return {
        "src_port": float(event.source_port or 0),
        "dst_port": float(event.destination_port or 53),
        "duration": duration,
        "total_bytes": float(total_bytes),
        "receiving_bytes": float(event.bytes_received),
        "sending_bytes": float(event.bytes_sent),
        "packets_rate": packets_rate,
        "packets_len_rate": packets_len_rate,
        "min_packets_len": 0.0,
        "max_packets_len": 0.0,
        "mean_packets_len": (
            total_bytes / total_packets
            if total_packets else 0.0
        ),
        "standard_deviation_packets_len": 0.0,
        "variance_packets_len": 0.0,
        "coefficient_of_variation_packets_len": 0.0,
        "dns_domain_name_length": float(len(domain_without_tld)),
        "dns_subdomain_name_length": float(len(subdomain)),
        "numerical_percentage": numerical_percentage,
        "character_entropy": shannon_entropy(domain),
        "max_continuous_numeric_len": float(max_numeric),
        "max_continuous_alphabet_len": float(max_alpha),
        "max_continuous_consonants_len": float(max_consonants),
        "max_continuous_same_alphabet_len": float(max_same_alpha),
        "vowels_consonant_ratio": (
            vowels / consonants
            if consonants else 0.0
        ),
        "conv_freq_vowels_consonants": (
            (vowels + consonants) / length
            if length else 0.0
        ),
        "distinct_ttl_values": 0.0,
        "ttl_values_min": 0.0,
        "ttl_values_max": 0.0,
        "ttl_values_mean": 0.0,
        "ttl_values_mode": 0.0,
        "ttl_values_median": 0.0,
        "distinct_A_records": 0.0,
    }
