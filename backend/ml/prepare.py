from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from backend.ml.features import extract_domain_features


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
]

OUTPUT_COLUMNS = [
    *FEATURE_NAMES,
    "domain",
    "label",
    "source",
]

RANDOM_STATE = 42


def normalize_domain(domain: str) -> str:
    """Normalize a domain before feature extraction."""

    return (
        str(domain)
        .strip()
        .lower()
        .rstrip(".")
    )


def build_feature_row(
    domain: str,
    label: str,
    source: str,
) -> dict:
    """Convert a domain into the common SentinelDNS schema."""

    domain = normalize_domain(domain)

    if not domain:
        raise ValueError("Empty domain.")

    features = extract_domain_features(domain)

    return {
        **{
            name: features[name]
            for name in FEATURE_NAMES
        },
        "domain": domain,
        "label": label.upper(),
        "source": source,
    }


def process_domain_dataframe(
    dataframe: pd.DataFrame,
    domain_column: str,
    label_column: str,
    source: str,
) -> pd.DataFrame:
    """
    Convert a DataFrame containing domains and labels
    into the common SentinelDNS ML schema.
    """

    rows = []

    for domain, label in zip(
        dataframe[domain_column],
        dataframe[label_column],
    ):
        try:
            rows.append(
                build_feature_row(
                    domain=domain,
                    label=label,
                    source=source,
                )
            )
        except (ValueError, TypeError):
            continue

    if not rows:
        return pd.DataFrame(
            columns=OUTPUT_COLUMNS
        )

    return pd.DataFrame(rows)


def deduplicate(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Remove duplicate domain/label combinations.

    Domain-only duplicates with conflicting labels are removed
    conservatively rather than arbitrarily choosing a label.
    """

    conflicts = (
        dataframe.groupby("domain")["label"]
        .nunique()
    )

    conflicting_domains = set(
        conflicts[conflicts > 1].index
    )

    if conflicting_domains:
        print(
            "[PREPARE] Removing "
            f"{len(conflicting_domains):,} "
            "domains with conflicting labels."
        )

        dataframe = dataframe[
            ~dataframe["domain"].isin(
                conflicting_domains
            )
        ]

    before = len(dataframe)

    dataframe = dataframe.drop_duplicates(
        subset=["domain"],
        keep="first",
    )

    print(
        "[PREPARE] Removed "
        f"{before - len(dataframe):,} duplicates."
    )

    return dataframe.reset_index(drop=True)


def split_dataset(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Create stratified train/validation/test splits.

    80% train
    10% validation
    10% test
    """

    train, temporary = train_test_split(
        dataframe,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=dataframe["label"],
    )

    validation, test = train_test_split(
        temporary,
        test_size=0.50,
        random_state=RANDOM_STATE,
        stratify=temporary["label"],
    )

    return (
        train.reset_index(drop=True),
        validation.reset_index(drop=True),
        test.reset_index(drop=True),
    )


def save_splits(
    dataframe: pd.DataFrame,
    output_directory: str | Path,
    prefix: str,
) -> None:
    """Save stratified train/validation/test CSV files."""

    output_directory = Path(output_directory)

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    train, validation, test = split_dataset(
        dataframe
    )

    train.to_csv(
        output_directory / f"{prefix}_train.csv",
        index=False,
    )

    validation.to_csv(
        output_directory / f"{prefix}_validation.csv",
        index=False,
    )

    test.to_csv(
        output_directory / f"{prefix}_test.csv",
        index=False,
    )

    print("\n[PREPARE] Dataset splits:")

    print(
        f"  train:      {len(train):,}"
    )

    print(
        f"  validation: {len(validation):,}"
    )

    print(
        f"  test:       {len(test):,}"
    )

    print("\n[PREPARE] Training distribution:")

    print(
        train["label"]
        .value_counts()
        .sort_index()
        .to_string()
    )


def prepare_dns_threats(
    input_path: str | Path,
    output_directory: str | Path,
) -> None:
    """
    Prepare the DNS Threats dataset.

    This dataset uses:
        0 = BENIGN
        1 = DGA
        2 = TUNNELING
    """

    print(
        f"[PREPARE] Reading DNS Threats: {input_path}"
    )

    dataframe = pd.read_csv(
        input_path,
        usecols=["domain", "class"],
    )

    dataframe["label"] = dataframe["class"].map(
        {
            0: "BENIGN",
            1: "DGA",
            2: "TUNNELING",
        }
    )

    dataframe = dataframe.dropna(
        subset=["label"]
    )

    result = process_domain_dataframe(
        dataframe=dataframe,
        domain_column="domain",
        label_column="label",
        source="dns_threats",
    )

    result = deduplicate(result)

    print(
        f"[PREPARE] DNS Threats samples: "
        f"{len(result):,}"
    )

    save_splits(
        result,
        output_directory,
        "dns_threats",
    )


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Prepare SentinelDNS ML datasets."
        )
    )

    parser.add_argument(
        "--dns-threats",
        type=Path,
        help="Path to DNS Threats CSV/CSV.GZ.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/processed"
        ),
        help="Output directory.",
    )

    args = parser.parse_args()

    if not args.dns_threats:
        parser.error(
            "At least --dns-threats is required."
        )

    prepare_dns_threats(
        input_path=args.dns_threats,
        output_directory=args.output,
    )


if __name__ == "__main__":
    main()
