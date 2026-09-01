FROM python:3.12-slim

WORKDIR /app

# libpq is needed at runtime for psycopg (even the [binary] wheel needs the
# client library present on some base images); curl is only for the
# container healthcheck. No compilers/dev headers — keeps the image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ML model artifacts and demo data ARE needed at runtime — .dockerignore
# only excludes venv/caches/local DB files, not these.
COPY . .

RUN chmod +x docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
