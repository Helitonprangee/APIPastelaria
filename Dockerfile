# Multi-stage build
# Builder stage
FROM python:3.14-alpine AS builder

LABEL maintainer="Heliton"
LABEL description="API FastAPI com Hypercorn e QUIC"
LABEL version="1.0.0"

RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.14-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/local/bin:$PATH" \
    PYTHONPATH="/app/local/lib/python3.14/site-packages"

RUN apk add --no-cache curl && rm -rf /var/cache/apk/*

RUN addgroup -g 1001 appuser && \
    adduser -D -u 1001 -G appuser appuser && \
    mkdir -p /app /cert /app/logs && \
    chown -R appuser:appuser /app /cert

WORKDIR /app/src

COPY --from=builder /usr/local/lib/python3.14/site-packages /app/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /app/local/bin

COPY --chown=appuser:appuser . /app
COPY --chown=appuser:appuser cert /cert

USER appuser

EXPOSE 4443/tcp
EXPOSE 4443/udp

ENTRYPOINT ["hypercorn", "--certfile=/cert/cert.pem", "--keyfile=/cert/ecc-key.pem"]
CMD ["--bind", "0.0.0.0:4443", "--quic-bind", "0.0.0.0:4443", "main:app"]