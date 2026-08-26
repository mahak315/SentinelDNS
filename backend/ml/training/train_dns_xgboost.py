from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.preprocessing import LabelEncoder


# --------------------------------------------------
# Paths
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[3]

TRAIN_PATH = ROOT / "data" / "processed" / "dns_threats_train.csv"
VAL_PATH = ROOT / "data" / "processed" / "dns_threats_validation.csv"
TEST_PATH = ROOT / "data" / "processed" / "dns_threats_test.csv"

MODEL_DIR = ROOT / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "sentinel_dns_xgboost.joblib"


# --------------------------------------------------
# DNS feature schema
# --------------------------------------------------

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

TARGET = "label"


# --------------------------------------------------
# Load dataset
# --------------------------------------------------

def load_dataset(path: Path):
    print(f"\nLoading: {path}")

    columns = FEATURE_NAMES + [TARGET]

    df = pd.read_csv(path, usecols=columns)

    print(f"Rows: {len(df):,}")

    return df


# --------------------------------------------------
# Prepare features
# --------------------------------------------------

def prepare_features(df):
    X = df[FEATURE_NAMES].copy()

    # Replace invalid numeric values
    X = X.replace([np.inf, -np.inf], np.nan)

    # XGBoost can handle missing values, but explicitly
    # filling them makes the inference pipeline predictable.
    X = X.fillna(0.0)

    y = df[TARGET].astype(str)

    return X, y


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    print("=" * 70)
    print("SentinelDNS - DNS XGBoost Training")
    print("=" * 70)

    # ------------------------------
    # Load splits
    # ------------------------------

    train_df = load_dataset(TRAIN_PATH)
    val_df = load_dataset(VAL_PATH)
    test_df = load_dataset(TEST_PATH)

    # ------------------------------
    # Prepare
    # ------------------------------

    X_train, y_train_raw = prepare_features(train_df)
    X_val, y_val_raw = prepare_features(val_df)
    X_test, y_test_raw = prepare_features(test_df)

    # ------------------------------
    # Encode labels
    # ------------------------------

    label_encoder = LabelEncoder()

    label_encoder.fit(
        pd.concat(
            [y_train_raw, y_val_raw, y_test_raw],
            ignore_index=True,
        )
    )

    y_train = label_encoder.transform(y_train_raw)
    y_val = label_encoder.transform(y_val_raw)
    y_test = label_encoder.transform(y_test_raw)

    print("\nClasses:")
    for i, label in enumerate(label_encoder.classes_):
        print(f"  {i}: {label}")

    # ------------------------------
    # Class weights
    # ------------------------------
    #
    # TUNNELING is severely underrepresented.
    # Compute balanced sample weights from the
    # training distribution.
    # ------------------------------

    class_counts = np.bincount(y_train)
    total = len(y_train)
    num_classes = len(class_counts)

    class_weights = {}

    for class_id, count in enumerate(class_counts):
        weight = total / (num_classes * count)
        class_weights[class_id] = weight

    print("\nClass weights:")

    for class_id, weight in class_weights.items():
        print(
            f"  {label_encoder.classes_[class_id]}: "
            f"{weight:.4f}"
        )

    sample_weights = np.array(
        [class_weights[class_id] for class_id in y_train],
        dtype=np.float32,
    )

    # ------------------------------
    # XGBoost model
    # ------------------------------

    model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=num_classes,

        n_estimators=500,
        max_depth=8,
        learning_rate=0.08,

        subsample=0.85,
        colsample_bytree=0.85,

        min_child_weight=3,
        gamma=0.0,

        reg_alpha=0.0,
        reg_lambda=1.0,

        tree_method="hist",

        eval_metric="mlogloss",

        random_state=42,
        n_jobs=-1,

        early_stopping_rounds=30,
    )

    # ------------------------------
    # Train
    # ------------------------------

    print("\nStarting XGBoost training...")
    print(f"Training rows:   {len(X_train):,}")
    print(f"Validation rows: {len(X_val):,}")
    print(f"Test rows:       {len(X_test):,}")
    print(f"Features:        {len(FEATURE_NAMES)}")

    model.fit(
        X_train,
        y_train,

        sample_weight=sample_weights,

        eval_set=[
            (X_train, y_train),
            (X_val, y_val),
        ],

        verbose=True,
    )

    # ------------------------------
    # Evaluation helper
    # ------------------------------

    def evaluate(name, X, y):

        print("\n" + "=" * 70)
        print(name)
        print("=" * 70)

        predictions = model.predict(X)

        accuracy = accuracy_score(y, predictions)

        print(f"\nAccuracy: {accuracy:.6f}")

        print("\nClassification report:")

        print(
            classification_report(
                y,
                predictions,
                target_names=label_encoder.classes_,
                digits=4,
                zero_division=0,
            )
        )

        print("Confusion matrix:")

        print(
            confusion_matrix(
                y,
                predictions,
            )
        )

    # ------------------------------
    # Evaluate
    # ------------------------------

    evaluate(
        "VALIDATION RESULTS",
        X_val,
        y_val,
    )

    evaluate(
        "TEST RESULTS",
        X_test,
        y_test,
    )

    # ------------------------------
    # Feature importance
    # ------------------------------

    print("\n" + "=" * 70)
    print("FEATURE IMPORTANCE")
    print("=" * 70)

    importances = model.feature_importances_

    importance_df = (
        pd.DataFrame(
            {
                "feature": FEATURE_NAMES,
                "importance": importances,
            }
        )
        .sort_values(
            "importance",
            ascending=False,
        )
    )

    print(importance_df.to_string(index=False))

    # ------------------------------
    # Save model
    # ------------------------------

    artifact = {
        "model": model,
        "label_encoder": label_encoder,
        "feature_names": FEATURE_NAMES,
        "class_names": list(label_encoder.classes_),
    }

    joblib.dump(
        artifact,
        MODEL_PATH,
    )

    print("\n" + "=" * 70)
    print("MODEL SAVED")
    print("=" * 70)

    print(MODEL_PATH)

    print("\nDone.")


if __name__ == "__main__":
    main()