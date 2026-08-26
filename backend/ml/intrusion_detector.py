import os
import joblib
from pathlib import Path
import pandas as pd
import numpy as np

from backend.core.models import TrafficEvent

# Load model artifact lazily
_model_artifact = None

def _get_artifact():
    global _model_artifact
    if _model_artifact is None:
        # Load from models/intrusion_xgboost.joblib relative to project root
        project_root = Path(__file__).resolve().parents[2]
        model_path = project_root / "models" / "intrusion_xgboost.joblib"
        if not model_path.exists():
            # Try loading from standard path
            model_path = Path(r"C:\Users\SINCHANA\Documents\GitHub\SentinelDNS\models\intrusion_xgboost.joblib")
            
        if not model_path.exists():
            raise FileNotFoundError(f"Trained intrusion detection model not found at {model_path}")
            
        _model_artifact = joblib.load(model_path)
    return _model_artifact

def event_to_xgboost_features(event: TrafficEvent, feature_names: list[str]) -> pd.DataFrame:
    """
    Map a TrafficEvent to the 52 network traffic features
    required by the XGBoost intrusion detection model.
    """
    feature_dict = {name: 0.0 for name in feature_names}
    
    # Mapping destination port
    feature_dict['destination port'] = float(event.destination_port or 53.0)
    
    # flow duration is in microseconds, duration_ms is in milliseconds
    feature_dict['flow duration'] = float(event.duration_ms * 1000.0)
    
    feature_dict['total fwd packets'] = float(event.packets_sent)
    feature_dict['total length of fwd packets'] = float(event.bytes_sent)
    
    if event.packets_sent > 0:
        avg_fwd = event.bytes_sent / event.packets_sent
        feature_dict['fwd packet length max'] = float(event.bytes_sent)
        feature_dict['fwd packet length min'] = float(event.bytes_sent)
        feature_dict['fwd packet length mean'] = float(avg_fwd)
        feature_dict['fwd packets/s'] = float(event.packets_sent / (event.duration_ms / 1000.0)) if event.duration_ms > 0 else 0.0
        feature_dict['subflow fwd bytes'] = float(event.bytes_sent)
        feature_dict['act_data_pkt_fwd'] = float(event.packets_sent)
        
    if event.packets_received > 0:
        avg_bwd = event.bytes_received / event.packets_received
        feature_dict['bwd packet length max'] = float(event.bytes_received)
        feature_dict['bwd packet length min'] = float(event.bytes_received)
        feature_dict['bwd packet length mean'] = float(avg_bwd)
        feature_dict['bwd packets/s'] = float(event.packets_received / (event.duration_ms / 1000.0)) if event.duration_ms > 0 else 0.0
        
    total_packets = event.packets_sent + event.packets_received
    total_bytes = event.bytes_sent + event.bytes_received
    
    if total_packets > 0:
        feature_dict['flow bytes/s'] = float(total_bytes / (event.duration_ms / 1000.0)) if event.duration_ms > 0 else 0.0
        feature_dict['flow packets/s'] = float(total_packets / (event.duration_ms / 1000.0)) if event.duration_ms > 0 else 0.0
        feature_dict['average packet size'] = float(total_bytes / total_packets)
        feature_dict['min packet length'] = float(min(event.bytes_sent, event.bytes_received))
        feature_dict['max packet length'] = float(max(event.bytes_sent, event.bytes_received))
        feature_dict['packet length mean'] = float(total_bytes / total_packets)

    df = pd.DataFrame([feature_dict])
    df = df[feature_names]  # Ensure column order matches trained columns exactly
    return df

def predict_intrusion(event: TrafficEvent) -> dict:
    """
    Run intrusion detection on a TrafficEvent.
    Returns a dict with:
      - 'prediction_label': decoded class name (e.g. Normal Traffic, DoS)
      - 'prediction_score': risk probability [0.0, 1.0] of it being an intrusion
      - 'probabilities': full probability distribution dict
    """
    artifact = _get_artifact()
    model = artifact["model"]
    le = artifact["label_encoder"]
    features = artifact["feature_names"]
    
    df_features = event_to_xgboost_features(event, features)
    
    pred_encoded = model.predict(df_features)[0]
    pred_label = le.classes_[pred_encoded]
    
    pred_proba = model.predict_proba(df_features)[0]
    
    # Map probabilities to classes
    proba_dict = {le.classes_[i]: float(p) for i, p in enumerate(pred_proba)}
    
    # Score represents the total probability of ANY attack type (i.e. 1.0 - normal probability)
    normal_proba = proba_dict.get("Normal Traffic", 0.0)
    prediction_score = 1.0 - normal_proba
    
    return {
        "prediction_label": pred_label,
        "prediction_score": float(prediction_score),
        "probabilities": proba_dict
    }
