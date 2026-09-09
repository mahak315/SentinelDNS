from __future__ import annotations

from pathlib import Path
import xgboost as xgb

import joblib
import pandas as pd

from backend.core.models import TrafficEvent
from backend.ml.features import extract_traffic_features


_model_artifact = None


def _get_artifact():
    """Load the trained DNS XGBoost model lazily."""
    global _model_artifact

    if _model_artifact is None:
        project_root = Path(__file__).resolve().parents[2]
        model_path = project_root / "models" / "dns_exfiltration_xgboost.json"

        if not model_path.exists():
            raise FileNotFoundError(
                f"DNS XGBoost model not found at {model_path}"
            )

        model = xgb.XGBClassifier()
        model.load_model(model_path)

        feature_names = model.get_booster().feature_names

        _model_artifact = {
            "model": model,
            "feature_names": feature_names,
        }

    return _model_artifact

def event_to_dns_features(
    event: TrafficEvent,
    feature_names: list[str],
) -> pd.DataFrame:
    """
    Convert a SentinelDNS TrafficEvent into the exact
    feature schema used by the trained DNS XGBoost.
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
          BENIGN or MALICIOUS

      prediction_score:
          probability of the event being malicious

      probabilities:
          probability for every model class

      features:
          feature values supplied to the model
    """

    artifact = _get_artifact()

    model = artifact["model"]
    feature_names = artifact.get("feature_columns") or artifact.get("feature_names", [])

    df_features = event_to_dns_features(
        event,
        feature_names,
    )

    pred_encoded = int(
        model.predict(df_features)[0]
    )

    pred_label = "MALICIOUS" if pred_encoded == 1 else "BENIGN"

    pred_proba = model.predict_proba(
        df_features
    )[0]

    probabilities = {
        "BENIGN": float(pred_proba[0]),
        "MALICIOUS": float(pred_proba[1]),
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
