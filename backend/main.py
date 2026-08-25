from fastapi import FastAPI

app = FastAPI(
    title="SentinelDNS",
    description="AI-powered adaptive network threat detection and response system",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "name": "SentinelDNS",
        "version": "0.1.0",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }