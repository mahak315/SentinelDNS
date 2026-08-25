from __future__ import annotations

from pathlib import Path
import json

import pandas as pd


DEFAULT_CHUNK_SIZE = 50_000

LABEL_MAP = {
    "benign_umbrella": "BENIGN",
    "benign_cesnet": "BENIGN",
    "phishing": "PHISHING",
    "malware": "MALWARE",
}


def find_json_files(
    dataset_path: str | Path,
) -> list[Path]:
    """
    Find JSON dataset files recursively.
    """

    root = Path(dataset_path)

    if not root.exists():
        raise FileNotFoundError(
            f"Dataset path does not exist: {root}"
        )

    return sorted(
        path
        for path in root.rglob("*.json")
        if path.name != "schema.json"
        and path.name != "data_schema.json"
    )


def infer_label(path: str | Path) -> str:
    """
    Infer the dataset label from the source filename.
    """

    name = Path(path).stem.lower()

    for key, label in LABEL_MAP.items():
        if key in name:
            return label

    raise ValueError(
        f"Unable to infer label from filename: {path}"
    )


def inspect_dataset(
    dataset_path: str | Path,
    sample_size: int = 1,
) -> None:
    """
    Inspect dataset files without loading the complete dataset.
    """

    files = find_json_files(dataset_path)

    if not files:
        raise FileNotFoundError(
            f"No JSON dataset files found under {dataset_path}"
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
        print(
            f"LABEL: {infer_label(path)}"
        )

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if not isinstance(data, list):
            print(
                "WARNING: expected JSON array"
            )
            continue

        print(
            f"RECORDS: {len(data):,}"
        )

        if data:
            record = data[0]

            print("\nTOP-LEVEL FIELDS:")

            for field in record:
                print(f"  - {field}")

            print("\nSAMPLE DOMAIN:")

            print(
                record.get(
                    "domain_name",
                    "<missing>",
                )
            )


def stream_json(
    path: str | Path,
):
    """
    Stream JSON-array records.

    This intentionally uses JSON decoding incrementally
    rather than loading the entire multi-gigabyte file.
    """

    import ijson

    with Path(path).open(
        "rb"
    ) as file:

        for record in ijson.items(
            file,
            "item",
        ):
            yield record


def records_to_dataframe(
    path: str | Path,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Convert a limited number of records into a DataFrame.

    Intended for inspection/testing, not full dataset loading.
    """

    records = []

    for index, record in enumerate(
        stream_json(path)
    ):

        records.append(record)

        if (
            limit is not None
            and index + 1 >= limit
        ):
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
