import time

from backend.dns.resolver import start_dns_server


def main():
    server = start_dns_server(
        host="127.0.0.1",
        port=5300,
    )

    print("SentinelDNS DNS server started.")
    print("Listening on 127.0.0.1:5300")
    print("Press CTRL+C to stop.")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping SentinelDNS...")
        server.stop()


if __name__ == "__main__":
    main()