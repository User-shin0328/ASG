FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
RUN groupadd --system --gid 10004 agent && useradd --system --uid 10004 --gid agent --home-dir /nonexistent --shell /usr/sbin/nologin agent
COPY demo_agent /app/demo_agent
CMD ["python", "-c", "import time; time.sleep(2147483647)"]
