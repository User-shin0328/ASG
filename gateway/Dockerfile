FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
RUN apk upgrade --no-cache \
    && apk add --no-cache shadow
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r /app/requirements.lock
RUN groupadd --system --gid 10001 gateway && useradd --system --uid 10001 --gid gateway --home-dir /nonexistent --shell /usr/sbin/nologin gateway
RUN mkdir -p /data && chown gateway:gateway /data
COPY gateway /app/gateway
COPY migrations /app/migrations
COPY config /app/config
COPY scripts /app/scripts
CMD ["python", "-m", "gateway.app.main"]
