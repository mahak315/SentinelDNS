from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.preprocessing import LabelEncoder


FEATURE_COLUMNS = [
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

TARGET_COLUMN = "label"


def load_split(path: str | Path):
    """Load one processed dataset split."""

    path = Path(path)

    print(f"[TRAIN] Loading: {path}")

    df = pd.read_csv(
        path,
        usecols=[
            *FEATURE_COLUMNS,
            TARGET_COLUMN,
        ],
    )

    print(f"[TRAIN] Samples: {len(df):,}")

    return df


def evaluate_model(
    model,
    X,
    y,
    label_encoder: LabelEncoder,
    split_name: str,
):
    """Evaluate the trained model."""

    predictions = model.predict(X)
    probabilities = model.predict_proba(X)

    accuracy = accuracy_score(y, predictions)

    macro_f1 = f1_score(
        y,
        predictions,
        average="macro",
    )

    weighted_f1 = f1_score(
        y,
        predictions,
        average="weighted",
    )

    print()
    print("=" * 70)
    print(f"{split_name.upper()} RESULTS")
    print("=" * 70)

    print(f"Accuracy:    {accuracy:.4f}")
    print(f"Macro F1:    {macro_f1:.4f}")
    print(f"Weighted F1: {weighted_f1:.4f}")

    print()
    print("Classification Report:")
    print(
        classification_report(
            y,
            predictions,
            target_names=label_encoder.classes_,
            digits=4,
            zero_division=0,
        )
    )

    print("Confusion Matrix:")

    matrix = confusion_matrix(
        y,
        predictions,
    )

    matrix_df = pd.DataFrame(
        matrix,
        index=label_encoder.classes_,
        columns=label_encoder.classes_,
    )

    print(matrix_df)

    try:
        roc_auc = roc_auc_score(
            y,
            probabilities,
            multi_class="ovr",
            average="macro",
        )

        print()
        print(f"Macro ROC-AUC: {roc_auc:.4f}")

    except ValueError:
        roc_auc = None

    precision, recall, f1, support = (
        precision_recall_fscore_support(
            y,
            predictions,
            labels=range(len(label_encoder.classes_)),
            zero_division=0,
        )
    )

    metrics = {
        "accuracy": float(accuracy),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "roc_auc_macro_ovr": (
            float(roc_auc)
            if roc_auc is not None
            else None
        ),
        "classes": label_encoder.classes_.tolist(),
        "per_class": {},
    }

    for index, label in enumerate(
        label_encoder.classes_
    ):
        metrics["per_class"][label] = {
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(f1[index]),
            "support": int(support[index]),
        }

    return metrics


def main():
    parser = argparse.ArgumentParser(
        description="Train SentinelDNS DNS domain classifier."
    )

    parser.add_argument(
        "--train",
        default="data/processed/dns_threats_train.csv",
    )

    parser.add_argument(
        "--validation",
        default="data/processed/dns_threats_validation.csv",
    )

    parser.add_argument(
        "--test",
        default="data/processed/dns_threats_test.csv",
    )

    parser.add_argument(
        "--output",
        default="models/dns_domain_classifier.joblib",
    )

    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------------------
    # Load data
    # ---------------------------------------------------------

    train_df = load_split(args.train)
    validation_df = load_split(args.validation)
    test_df = load_split(args.test)

    # ---------------------------------------------------------
    # Encode labels
    # ---------------------------------------------------------

    label_encoder = LabelEncoder()

    y_train = label_encoder.fit_transform(
        train_df[TARGET_COLUMN]
    )

    y_validation = label_encoder.transform(
        validation_df[TARGET_COLUMN]
    )

    y_test = label_encoder.transform(
        test_df[TARGET_COLUMN]
    )

    X_train = train_df[FEATURE_COLUMNS]
    X_validation = validation_df[FEATURE_COLUMNS]
    X_test = test_df[FEATURE_COLUMNS]

    print()
    print("[TRAIN] Classes:")

    for index, label in enumerate(
        label_encoder.classes_
    ):
        print(
            f"  {index}: {label}"
        )

    # ---------------------------------------------------------
    # Train
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("TRAINING RANDOM FOREST")
    print("=" * 70)

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
    )

    print("[TRAIN] Starting model training...")

    model.fit(
        X_train,
        y_train,
    )

    print("[TRAIN] Training complete.")

    # ---------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------

    validation_metrics = evaluate_model(
        model=model,
        X=X_validation,
        y=y_validation,
        label_encoder=label_encoder,
        split_name="validation",
    )

    test_metrics = evaluate_model(
        model=model,
        X=X_test,
        y=y_test,
        label_encoder=label_encoder,
        split_name="test",
    )

    # ---------------------------------------------------------
    # Feature importance
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("FEATURE IMPORTANCE")
    print("=" * 70)

    importance = pd.Series(
        model.feature_importances_,
        index=FEATURE_COLUMNS,
    ).sort_values(
        ascending=False
    )

    print(
        importance.to_string()
    )

    # ---------------------------------------------------------
    # Save model
    # ---------------------------------------------------------

    artifact = {
        "model": model,
        "label_encoder": label_encoder,
        "feature_columns": FEATURE_COLUMNS,
        "model_type": "RandomForestClassifier",
        "random_state": 42,
    }

    joblib.dump(
        artifact,
        output_path,
    )

    print()
    print(
        f"[TRAIN] Model saved to: {output_path}"
    )

    # ---------------------------------------------------------
    # Save metrics
    # ---------------------------------------------------------

    metrics_path = output_path.with_suffix(
        ".metrics.json"
    )

    metrics = {
        "model": "RandomForestClassifier",
        "features": FEATURE_COLUMNS,
        "validation": validation_metrics,
        "test": test_metrics,
        "training_samples": len(train_df),
        "validation_samples": len(validation_df),
        "test_samples": len(test_df),
    }

    with metrics_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metrics,
            file,
            indent=2,
        )

    print(
        f"[TRAIN] Metrics saved to: {metrics_path}"
    )


if __name__ == "__main__":
    main()
