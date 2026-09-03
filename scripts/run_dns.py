import os
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path when executed directly on Linux
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.dns.resolver import start_dns_server


def main():
    host = os.getenv("SENTINEL_DNS_HOST", "127.0.0.1")
    port = int(os.getenv("SENTINEL_DNS_PORT", "5300"))

    server = start_dns_server(
        host=host,
        port=port,
    )

    print("SentinelDNS DNS server started.")
    print(f"Listening on {host}:{port}")
    print("Press CTRL+C to stop.")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping SentinelDNS...")
        server.stop()


if __name__ == "__main__":
    main()