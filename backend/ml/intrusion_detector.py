from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from backend.core.models import TrafficEvent
from backend.ml.features import extract_traffic_features


_model_artifact = None


def _get_artifact():
    """Load the trained SentinelDNS Random Forest artifact lazily."""
    global _model_artifact

    if _model_artifact is None:
        project_root = Path(__file__).resolve().parents[2]
        model_path = (
            project_root
            / "models"
            / "sentinel_dns_random_forest.joblib"
        )

        if not model_path.exists():
            alt_paths = [
                project_root / "models" / "intrusion_xgboost.joblib",
                project_root / "models" / "sentinel_dns_xgboost.joblib",
            ]
            for alt in alt_paths:
                if alt.exists():
                    model_path = alt
                    break
            else:
                raise FileNotFoundError(
                    f"SentinelDNS model not found at {model_path}"
                )

        _model_artifact = joblib.load(model_path)

    return _model_artifact


def event_to_dns_features(
    event: TrafficEvent,
    feature_names: list[str],
) -> pd.DataFrame:
    """
    Convert a SentinelDNS TrafficEvent into the exact
    feature schema used by the trained DNS Random Forest.
    """

    features = extract_traffic_features(event)

    missing = [
        name
        for name in feature_names
        if name not in features
    ]

    if missing:
        raise ValueError(
            f"Missing DNS ML features: {missing}"
        )

    row = {
        name: features[name]
        for name in feature_names
    }

    return pd.DataFrame(
        [row],
        columns=feature_names,
    )


def predict_intrusion(event: TrafficEvent) -> dict:
    """
    Run the trained SentinelDNS DNS classifier.

    Returns:
      prediction_label:
          BENIGN, DGA, or TUNNELING

      prediction_score:
          probability of the event being malicious

      probabilities:
          probability for every model class

      features:
          feature values supplied to the model
    """

    artifact = _get_artifact()

    model = artifact["model"]
    label_encoder = artifact["label_encoder"]
    feature_names = artifact.get("feature_columns") or artifact.get("feature_names", [])

    df_features = event_to_dns_features(
        event,
        feature_names,
    )

    pred_encoded = int(
        model.predict(df_features)[0]
    )

    pred_label = str(
        label_encoder.inverse_transform(
            [pred_encoded]
        )[0]
    )

    pred_proba = model.predict_proba(
        df_features
    )[0]

    probabilities = {
        str(label_encoder.classes_[i]): float(probability)
        for i, probability in enumerate(pred_proba)
    }

    benign_probability = probabilities.get(
        "BENIGN",
        0.0,
    )

    prediction_score = 1.0 - benign_probability

    return {
        "prediction_label": pred_label,
        "prediction_score": float(prediction_score),
        "probabilities": probabilities,
        "features": df_features.iloc[0].to_dict(),
    }
