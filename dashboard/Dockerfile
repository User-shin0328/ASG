FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apk upgrade --no-cache \
    && apk add --no-cache nftables util-linux shadow
RUN groupadd --system --gid 10003 dashboard && useradd --system --uid 10003 --gid dashboard --home-dir /nonexistent --shell /usr/sbin/nologin dashboard
COPY dashboard /app
COPY dashboard/start.sh /usr/local/bin/dashboard-start
RUN chmod 0755 /usr/local/bin/dashboard-start
ENTRYPOINT ["/usr/local/bin/dashboard-start"]
