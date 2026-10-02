FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
RUN apk upgrade --no-cache \
    && apk add --no-cache shadow
RUN groupadd --system --gid 10002 sandbox && useradd --system --uid 10002 --gid sandbox --home-dir /nonexistent --shell /usr/sbin/nologin sandbox
RUN mkdir -p /data && chown sandbox:sandbox /data
COPY tool_sandbox /app/tool_sandbox
COPY fixtures/documents /app/fixtures/documents
CMD ["python", "-m", "tool_sandbox.app"]
