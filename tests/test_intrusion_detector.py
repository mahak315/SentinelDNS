from backend.core.models import TrafficEvent
from backend.ml.intrusion_detector import predict_intrusion

def test_prediction_flow():
    # Construct normal looking traffic event
    normal_event = TrafficEvent(
        source_ip="192.168.1.10",
        destination_ip="8.8.8.8",
        destination_port=53,
        protocol="UDP",
        domain="google.com",
        bytes_sent=100,
        bytes_received=150,
        packets_sent=2,
        packets_received=2,
        duration_ms=10.0
    )
    
    # Run prediction
    res = predict_intrusion(normal_event)
    
    print("\n--- Verification test result ---")
    print(f"Predicted Label: {res['prediction_label']}")
    print(f"Risk Score:      {res['prediction_score']:.4f}")
    
    # Assert return types and structures
    assert isinstance(res['prediction_label'], str)
    assert isinstance(res['prediction_score'], float)
    assert 0.0 <= res['prediction_score'] <= 1.0
    assert "probabilities" in res
    assert "BENIGN" in res["probabilities"] or "Normal Traffic" in res["probabilities"]

if __name__ == "__main__":
    test_prediction_flow()
