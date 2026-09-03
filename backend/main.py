from pathlib import Path
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.ml.intrusion_detector import _get_artifact

app = FastAPI(
    title="SentinelDNS",
    description="AI-powered DNS threat detection and response system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVENT_LOG = PROJECT_ROOT / "data" / "dns_events.jsonl"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/dashboard")
def dashboard():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": "Dashboard UI not found"}


def read_events():
    events = []

    if not EVENT_LOG.exists():
        return events

    try:
        with EVENT_LOG.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []

    return events


@app.get("/")
def root():
    return {
        "name": "SentinelDNS",
        "version": "1.0.0",
        "status": "online",
    }


@app.get("/health")
@app.get("/api/health")
def health():
    model_name = "sentinel_dns_random_forest.joblib"

    try:
        artifact = _get_artifact()
        model_type = artifact.get(
            "model_type",
            "RandomForestClassifier",
        )
        ml_status = model_type
    except Exception:
        ml_status = "offline"

    return {
        "status": "online",
        "service": "SentinelDNS",
        "ml": ml_status,
        "model": model_name,
    }


@app.get("/api/stats")
def stats():
    from backend.storage.events import get_stats as db_get_stats
    s = db_get_stats()
    return {
        "total_queries": s["total_queries"],
        "blocked": s["blocked_queries"],
        "ml_detections": s["dga_detections"] + s["tunneling_detections"],
        "model": "sentinel_dns_random_forest.joblib",
    }


@app.get("/api/events")
@app.get("/api/dns/events")
@app.get("/api/logs")
def events(limit: int = 100):
    from backend.storage.events import get_recent_events
    data = get_recent_events(limit)
    return data


@app.get("/api/threats")
def threats():
    data = read_events()

    threats = [
        event
        for event in data
        if str(event.get("verdict", "")).upper() != "ALLOW"
        or str(event.get("detection", "")).upper()
        not in ("", "NONE")
        or float(event.get("threat_intel_score", 0) or 0) > 0
        or float(event.get("ml_score", 0) or 0) > 0.5
    ]

    return {
        "threats": threats[-100:]
    }


@app.get("/api/ml")
def ml_info():
    try:
        artifact = _get_artifact()
        model = artifact["model"]

        return {
            "status": "online",
            "model": "RandomForestClassifier",
            "model_file": "sentinel_dns_random_forest.joblib",
            "classes": list(
                artifact["label_encoder"].classes_
            ),
            "features": artifact.get(
                "feature_columns",
                [],
            ),
            "feature_count": len(
                artifact.get("feature_columns", [])
            ),
            "estimators": getattr(
                model,
                "n_estimators",
                None,
            ),
        }

    except Exception as exc:
        return {
            "status": "offline",
            "model": "RandomForestClassifier",
            "error": str(exc),
        }


@app.get("/api/devices")
def devices():
    from backend.storage.events import get_connected_devices
    return get_connected_devices()
