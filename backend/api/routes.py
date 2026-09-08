from fastapi import APIRouter, Query

from backend.storage.events import (
    get_recent_events,
    get_stats,
)


router = APIRouter(
    prefix="/api",
    tags=["dashboard"],
)


@router.get("/health")
def health():
    return {
        "status": "online",
        "service": "SentinelDNS",
        "ml": "RandomForest",
        "model": "dns_exfiltration_xgboost.json",
    }


@router.get("/stats")
def stats():
    return get_stats()


@router.get("/events")
def events(
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    )
):
    return {
        "events": get_recent_events(limit)
    }
