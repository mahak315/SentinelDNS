# SentinelDNS

AI-powered adaptive network threat detection and response system.

## Status

🚧 Under active development.

## Planned Components

- Network/DNS traffic monitoring
- Threat intelligence
- Machine learning
- Risk scoring
- Reinforcement learning
- Adaptive response
- Security dashboard

## Linux Deployment & Execution

SentinelDNS is fully configured for Linux deployment.

### Quick Start (Native Bash)

```bash
chmod +x start.sh
./start.sh
```

### Docker Deployment

```bash
docker compose up -d --build
```

### Systemd Service Deployment

```bash
sudo cp sentineldns.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sentineldns
```

### Exposed Services

- **DNS Server**: `UDP 0.0.0.0:5300` (configurable via `SENTINEL_DNS_PORT` / `SENTINEL_DNS_HOST`)
- **API & Dashboard**: `TCP 0.0.0.0:8000` (configurable via `FASTAPI_PORT` / `FASTAPI_HOST`)

