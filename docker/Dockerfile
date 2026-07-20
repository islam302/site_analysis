FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Shared location for the Playwright Chromium (link checker JS rendering).
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# libpq-dev/gcc for psycopg build fallbacks; curl for the healthcheck.
# The Arabic PDF font (Tajawal) is bundled in the repo (assets/fonts).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/production.txt ./requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

# Chromium + its OS libraries for the link checker's optional JS rendering.
# (Adds ~400 MB. Skip this line if you never use render_js.)
RUN apt-get update && \
    playwright install --with-deps chromium && \
    chmod -R a+rx /ms-playwright && \
    rm -rf /var/lib/apt/lists/*

COPY . .

RUN chmod +x docker/entrypoint.sh

# Non-root user. Own the writable dirs so freshly-created named volumes
# (media, staticfiles) inherit the correct ownership.
RUN useradd --create-home --uid 1000 appuser && \
    mkdir -p /app/media /app/staticfiles && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Migrations + collectstatic run in the entrypoint (gated by env flags) so they
# happen once, at runtime, against the mounted volumes.
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", \
     "--workers", "4", "--timeout", "120", "--access-logfile", "-"]
