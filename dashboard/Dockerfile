FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --system --gid 10003 dashboard && useradd --system --uid 10003 --gid dashboard --home-dir /nonexistent --shell /usr/sbin/nologin dashboard
COPY dashboard /app
CMD ["python", "server.py"]
