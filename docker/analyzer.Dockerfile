FROM python:3.12-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app \
    PATH="/root/.config/composer/vendor/bin:/root/.composer/vendor/bin:${PATH}"
WORKDIR /app
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    git curl nodejs npm php-cli composer default-jdk maven ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt backend/analyzer-requirements.txt /app/
RUN pip install --no-cache-dir -r analyzer-requirements.txt \
    && npm install -g eslint typescript \
    && composer global require --no-interaction phpstan/phpstan laravel/pint
COPY backend/app /app/app
CMD ["celery", "-A", "app.workers.celery_app.celery", "worker", "--loglevel=INFO", "--concurrency=2"]
