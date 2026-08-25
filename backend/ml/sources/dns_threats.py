from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.ml.features import extract_domain_features


CLASS_MAP = {
    0: "BENIGN",
    1: "DGA",
    2: "TUNNELING",
}


def load_dns_threats(
    path: str | Path,
) -> pd.DataFrame:
    """
    Load and normalize the DNS Threats Dataset.

    Source classes:
        0 -> BENIGN
        1 -> DGA
        2 -> TUNNELING
    """

    path = Path(path)

    df = pd.read_csv(path)

    required_columns = {"domain", "class"}

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    df = df[["domain", "class"]].copy()

    df["domain"] = (
        df["domain"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.rstrip(".")
    )

    df = df[df["domain"] != ""]

    unknown_classes = set(df["class"].unique()) - set(CLASS_MAP)

    if unknown_classes:
        raise ValueError(
            f"Unknown dataset classes: {sorted(unknown_classes)}"
        )

    df["label"] = df["class"].map(CLASS_MAP)

    df["source"] = "dns_threats"

    df = df.drop_duplicates(
        subset=["domain", "label"]
    )

    return df.reset_index(drop=True)


def extract_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extract SentinelDNS lexical features.
    """

    feature_rows = [
        extract_domain_features(domain)
        for domain in df["domain"]
    ]

    features = pd.DataFrame(feature_rows)

    result = pd.concat(
        [
            features.reset_index(drop=True),
            df[["domain", "label", "source"]].reset_index(
                drop=True
            ),
        ],
        axis=1,
    )

    return result


def build_processed_dataset(
    input_path: str | Path,
    output_path: str | Path,
) -> pd.DataFrame:
    """
    Convert the raw DNS Threats Dataset into
    SentinelDNS ML features.
    """

    df = load_dns_threats(input_path)

    print(
        f"[DNS-THREATS] Loaded {len(df):,} unique samples"
    )

    print(
        "\n[DNS-THREATS] Class distribution:"
    )

    print(
        df["label"].value_counts().to_string()
    )

    processed = extract_features(df)

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    processed.to_csv(
        output_path,
        index=False,
    )

    print(
        f"\n[DNS-THREATS] Saved "
        f"{len(processed):,} samples to "
        f"{output_path}"
    )

    return processed


if __name__ == "__main__":

    build_processed_dataset(
        input_path=(
            "data/raw/dns_threats/"
            "train_combined_multiclass.csv.gz"
        ),
        output_path=(
            "data/processed/"
            "dns_threats_train.csv"
        ),
    )
