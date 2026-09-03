#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo " Starting SentinelDNS on Linux"
echo "=========================================="

if [ ! -d "venv" ]; then
    echo "[+] Creating Python virtual environment (venv)..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "[+] Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "[+] Seeding Threat Intelligence DB..."
python -m scripts.seed_threat_intelligence

export SENTINEL_DNS_HOST="${SENTINEL_DNS_HOST:-0.0.0.0}"
export SENTINEL_DNS_PORT="${SENTINEL_DNS_PORT:-5300}"
export FASTAPI_HOST="${FASTAPI_HOST:-0.0.0.0}"
export FASTAPI_PORT="${FASTAPI_PORT:-8000}"

echo "[+] Launching SentinelDNS DNS Server on ${SENTINEL_DNS_HOST}:${SENTINEL_DNS_PORT}..."
python -m scripts.run_dns &
DNS_PID=$!

echo "[+] Launching SentinelDNS API Backend on ${FASTAPI_HOST}:${FASTAPI_PORT}..."
python -m uvicorn backend.main:app --host "$FASTAPI_HOST" --port "$FASTAPI_PORT" &
API_PID=$!

cleanup() {
    echo ""
    echo "[!] Shutting down SentinelDNS processes..."
    kill "$DNS_PID" 2>/dev/null || true
    kill "$API_PID" 2>/dev/null || true
    wait "$DNS_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
    echo "[+] Shutdown complete."
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "=========================================="
echo " SentinelDNS active!"
echo " DNS Server: udp://${SENTINEL_DNS_HOST}:${SENTINEL_DNS_PORT}"
echo " API Dashboard: http://${FASTAPI_HOST}:${FASTAPI_PORT}"
echo " Press CTRL+C to terminate"
echo "=========================================="

wait
