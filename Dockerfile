FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     curl     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV SENTINEL_DNS_HOST=0.0.0.0
ENV SENTINEL_DNS_PORT=5300
ENV FASTAPI_HOST=0.0.0.0
ENV FASTAPI_PORT=8000

EXPOSE 5300/udp
EXPOSE 8000/tcp

RUN chmod +x start.sh
CMD ["./start.sh"]
