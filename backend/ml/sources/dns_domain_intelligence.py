from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pandas as pd


LABEL_MAP = {
    "benign_umbrella": "BENIGN",
    "benign_cesnet": "BENIGN",
    "phishing": "PHISHING",
    "malware": "MALWARE",
}


def find_json_files(
    dataset_path: str | Path,
) -> list[Path]:
    """Find JSON dataset files recursively."""

    root = Path(dataset_path)

    if not root.exists():
        raise FileNotFoundError(
            f"Dataset path does not exist: {root}"
        )

    return sorted(root.rglob("*.json"))


def infer_label(path: str | Path) -> str:
    """Infer the dataset label from the filename."""

    name = Path(path).stem.lower()

    for key, label in LABEL_MAP.items():
        if key in name:
            return label

    raise ValueError(
        f"Unable to infer label from filename: {path}"
    )


def stream_json(
    path: str | Path,
) -> Iterator[dict]:
    """
    Stream records from a JSON array without loading
    the complete file into memory.
    """

    import ijson

    with Path(path).open("rb") as file:
        yield from ijson.items(file, "item")


def inspect_dataset(
    dataset_path: str | Path,
    sample_size: int = 2,
) -> None:
    """
    Inspect dataset structure without loading complete files.
    """

    files = find_json_files(dataset_path)

    if not files:
        raise FileNotFoundError(
            f"No JSON files found under {dataset_path}"
        )

    print(
        f"[DNS-INTEL] Found {len(files)} JSON file(s)"
    )

    for path in files:

        print("\n" + "=" * 70)
        print(f"FILE: {path}")
        print(
            f"SIZE: {path.stat().st_size:,} bytes"
        )

        try:
            label = infer_label(path)
        except ValueError:
            label = "UNKNOWN"

        print(f"LABEL: {label}")

        records = stream_json(path)

        samples = []

        for index, record in enumerate(records):

            samples.append(record)

            if index + 1 >= sample_size:
                break

        print(
            f"SAMPLE RECORDS READ: {len(samples)}"
        )

        for index, record in enumerate(samples):

            print(
                f"\nRECORD {index + 1} FIELDS:"
            )

            if isinstance(record, dict):

                for field in record.keys():
                    print(f"  - {field}")

                domain = (
                    record.get("domain_name")
                    or record.get("domain")
                    or record.get("fqdn")
                )

                print(
                    f"DOMAIN: {domain}"
                )

            else:

                print(
                    f"WARNING: expected object, "
                    f"got {type(record).__name__}"
                )


def records_to_dataframe(
    path: str | Path,
    limit: int = 1000,
) -> pd.DataFrame:
    """
    Convert a limited number of streamed records
    into a DataFrame.

    This function is intentionally limited and should
    only be used for inspection/testing.
    """

    records = []

    for index, record in enumerate(
        stream_json(path)
    ):

        records.append(record)

        if index + 1 >= limit:
            break

    return pd.DataFrame(records)


if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: "
            "python -m backend.ml.sources.dns_domain_intelligence "
            "<dataset_path>"
        )
        raise SystemExit(1)

    inspect_dataset(sys.argv[1])
