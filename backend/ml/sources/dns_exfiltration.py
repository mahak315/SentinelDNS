from __future__ import annotations

from pathlib import Path

import pandas as pd


DEFAULT_CHUNK_SIZE = 100_000


def find_csv_files(
    dataset_path: str | Path,
) -> list[Path]:
    """
    Find CSV files recursively inside a dataset directory.
    """

    root = Path(dataset_path)

    if not root.exists():
        raise FileNotFoundError(
            f"Dataset path does not exist: {root}"
        )

    return sorted(
        root.rglob("*.csv")
    )


def inspect_dataset(
    dataset_path: str | Path,
    sample_rows: int = 5,
) -> None:
    """
    Inspect CSV files without loading the entire dataset.
    """

    files = find_csv_files(dataset_path)

    if not files:
        raise FileNotFoundError(
            f"No CSV files found under {dataset_path}"
        )

    print(
        f"[DNS-EXFIL] Found {len(files)} CSV file(s)"
    )

    for path in files:
        print("\n" + "=" * 70)
        print(f"FILE: {path}")
        print(
            f"SIZE: {path.stat().st_size:,} bytes"
        )

        sample = pd.read_csv(
            path,
            nrows=sample_rows,
        )

        print(
            f"COLUMNS ({len(sample.columns)}):"
        )

        for column in sample.columns:
            print(f"  - {column}")

        print("\nSAMPLE:")
        print(
            sample.to_string(index=False)
        )


def stream_csv(
    path: str | Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
):
    """
    Stream a large CSV in manageable chunks.
    """

    return pd.read_csv(
        path,
        chunksize=chunk_size,
    )


if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: "
            "python -m backend.ml.sources.dns_exfiltration "
            "<dataset_path>"
        )
        raise SystemExit(1)

    inspect_dataset(sys.argv[1])
