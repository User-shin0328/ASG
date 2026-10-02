FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --system --gid 10003 dashboard && useradd --system --uid 10003 --gid dashboard --home-dir /nonexistent --shell /usr/sbin/nologin dashboard
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y --no-install-recommends nftables util-linux && rm -rf /var/lib/apt/lists/*
COPY dashboard /app
COPY dashboard/start.sh /usr/local/bin/dashboard-start
RUN chmod 0755 /usr/local/bin/dashboard-start
ENTRYPOINT ["/usr/local/bin/dashboard-start"]
