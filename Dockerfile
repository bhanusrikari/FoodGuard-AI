# FoodGuard AI — backend container image.
#
# NOT built or run as part of this change (Docker isn't installed in the
# dev environment this was written in) — review/test a build before relying
# on this in a real deployment.
#
# Known gaps this image does NOT solve (see README/docs for detail):
#   - Production media serving: Django only serves /media/ when DEBUG=True.
#     Put nginx / whitenoise / object storage in front of this container
#     for real user-uploaded image access in production.
#   - The real food-quality model.pt is not included in this image — see
#     FOOD_QUALITY_MODEL_DIR in config/settings.py; mount it as a volume
#     once a real trained model exists.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libpq is needed at runtime for psycopg2; build-essential covers any
# source builds pip falls back to when a prebuilt wheel isn't available.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/healthz/ || exit 1

# Run `python manage.py migrate` (and `collectstatic` if serving static
# files from this container) as a separate step before/around this command
# in your deployment tooling — this image does not run migrations itself.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
