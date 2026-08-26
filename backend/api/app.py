from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router


app = FastAPI(
    title="SentinelDNS",
    description="AI-powered DNS security and threat detection platform",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)


@app.get("/")
def root():
    return {
        "service": "SentinelDNS",
        "status": "online",
        "version": "1.0.0",
    }
