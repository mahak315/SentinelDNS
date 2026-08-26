import socket

from dnslib import DNSRecord, QTYPE
from dnslib.server import BaseResolver, DNSLogger, DNSServer

from backend.core.models import TrafficEvent
from backend.detection.pipeline import analyze_event


UPSTREAM_DNS = ("8.8.8.8", 53)



class SentinelDNSResolver(BaseResolver):

    def resolve(self, request, handler):

        question = request.q

        domain = str(question.qname).rstrip(".")
        query_type = QTYPE[question.qtype]

        client_ip = "unknown"

        if handler is not None:
            try:
                client_ip = handler.client_address[0]
            except Exception:
                pass

        print(
            f"[DNS] {client_ip} -> "
            f"{domain} ({query_type})"
        )

        event = TrafficEvent(
            source_ip=client_ip,
            destination_ip=UPSTREAM_DNS[0],
            protocol="UDP",
            domain=domain,
            query_type=query_type,
        )

        ml_score = 0.0

        try:
            from backend.ml.intrusion_detector import (
                predict_intrusion
            )

            prediction = predict_intrusion(event)

            ml_score = prediction["prediction_score"]

            label = prediction["prediction_label"]
            probabilities = prediction["probabilities"]

            event.reason = (
                f"ML={label} "
                f"score={ml_score:.4f}"
            )

            print(
                f"[ML] "
                f"domain={domain} "
                f"prediction={label} "
                f"score={ml_score:.4f} "
                f"BENIGN={probabilities.get('BENIGN', 0.0):.4f} "
                f"DGA={probabilities.get('DGA', 0.0):.4f} "
                f"TUNNELING={probabilities.get('TUNNELING', 0.0):.4f}"
            )

        except Exception as exc:

            print(
                f"[RESOLVER ERROR] "
                f"ML prediction failed: {exc}"
            )

            ml_score = 0.0

        result = analyze_event(
            event,
            ml_score=ml_score,
        )

        print(
            f"[DETECTION] "
            f"domain={domain} "
            f"TI={result.threat_intel_score:.2f} "
            f"ML={result.ml_score:.2f} "
            f"risk={result.risk_score:.2f} "
            f"verdict={result.verdict}"
        )

        if result.verdict.value == "BLOCK":

            return self.block_response(
                request
            )

        return self.forward_upstream(
            request
        )

    def block_response(self, request):

        reply = request.reply()

        reply.header.rcode = 3

        return reply

    def forward_upstream(self, request):

        packet = request.pack()

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

        sock.settimeout(3)

        try:

            sock.sendto(
                packet,
                UPSTREAM_DNS,
            )

            response, _ = sock.recvfrom(4096)

            return DNSRecord.parse(
                response
            )

        finally:

            sock.close()


def start_dns_server(
    host: str = "127.0.0.1",
    port: int = 5300,
):

    resolver = SentinelDNSResolver()

    logger = DNSLogger(
        prefix=False,
        log="request,error,response",
    )

    server = DNSServer(
        resolver,
        port=port,
        address=host,
        logger=logger,
    )

    print(
        f"SentinelDNS listening on "
        f"{host}:{port}"
    )

    server.start_thread()

    return server


if __name__ == "__main__":

    server = start_dns_server()

    try:

        while True:
            pass

    except KeyboardInterrupt:

        print(
            "\nStopping SentinelDNS..."
        )

        server.stop()
