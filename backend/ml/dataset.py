from __future__ import annotations

import csv
from pathlib import Path

from backend.core.models import TrafficEvent
from backend.ml.features import extract_traffic_features


FEATURE_NAMES = [
    "domain_length",
    "label_count",
    "subdomain_count",
    "digit_count",
    "digit_ratio",
    "letter_count",
    "letter_ratio",
    "hyphen_count",
    "underscore_count",
    "special_character_count",
    "unique_character_count",
    "unique_character_ratio",
    "entropy",
    "tld_length",
    "domain_without_tld_length",
    "bytes_sent",
    "bytes_received",
    "packets_sent",
    "packets_received",
    "duration_ms",
]

LABEL_NAME = "label"


def build_traffic_event(
    domain: str,
    label: str,
) -> tuple[TrafficEvent, str]:
    """
    Build a TrafficEvent for a labeled DNS domain sample.

    Traffic values remain zero when the source dataset
    contains domain information only.
    """

    domain = domain.strip()
    label = label.strip().upper()

    if not domain:
        raise ValueError("Domain cannot be empty.")

    if not label:
        raise ValueError("Label cannot be empty.")

    event = TrafficEvent(
        source_ip="dataset",
        destination_ip=None,
        protocol="UDP",
        domain=domain,
        query_type="A",
    )

    return event, label


def event_to_dataset_row(
    event: TrafficEvent,
    label: str,
) -> dict:
    """
    Convert a TrafficEvent into the common SentinelDNS
    feature representation.
    """

    label = label.strip().upper()

    if not label:
        raise ValueError("Label cannot be empty.")

    features = extract_traffic_features(event)

    return {
        **{
            feature_name: features[feature_name]
            for feature_name in FEATURE_NAMES
        },
        LABEL_NAME: label,
    }


def extract_dataset_row(
    domain: str,
    label: str,
) -> dict:
    """
    Convert one domain-only dataset sample into
    the common SentinelDNS ML representation.
    """

    event, normalized_label = build_traffic_event(
        domain=domain,
        label=label,
    )

    return event_to_dataset_row(
        event=event,
        label=normalized_label,
    )


def build_dataset(
    samples: list[tuple[str, str]],
    output_path: str | Path,
) -> Path:
    """
    Build a CSV dataset from domain/label samples.
    """

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        *FEATURE_NAMES,
        LABEL_NAME,
    ]

    rows = []

    for domain, label in samples:
        try:
            rows.append(
                extract_dataset_row(
                    domain=domain,
                    label=label,
                )
            )

        except ValueError as exc:
            print(
                f"[DATASET] Skipping sample "
                f"{domain!r}: {exc}"
            )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    print(
        f"[DATASET] Wrote {len(rows)} samples "
        f"to {output_path}"
    )

    return output_path
