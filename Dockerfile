# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM python:3.13-alpine3.23 AS builder

RUN apk add --no-cache gammu-dev gcc musl-dev pkgconf

RUN pip install --no-cache-dir setuptools && \
    pip install --no-cache-dir --prefix=/install --no-build-isolation \
    "python-gammu==3.2.5" paho-mqtt

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.13-alpine3.23

RUN apk add --no-cache gammu tzdata

COPY --from=builder /install /usr/local

WORKDIR /app
COPY sms2mqtt.py .

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ps aux | grep -q "[p]ython /app/sms2mqtt.py" || exit 1

ENTRYPOINT ["python", "/app/sms2mqtt.py"]
