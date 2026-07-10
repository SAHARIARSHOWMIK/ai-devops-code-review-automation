FROM node:22-bookworm-slim AS node-runtime
FROM composer:2.8 AS composer-runtime

FROM python:3.12-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/root/.config/composer/vendor/bin:/root/.composer/vendor/bin:${PATH}"
WORKDIR /app

COPY --from=node-runtime /usr/local/ /usr/local/
COPY --from=composer-runtime /usr/bin/composer /usr/local/bin/composer

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        default-jdk \
        git \
        maven \
        php-cli \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/analyzer-requirements.txt /app/
RUN pip install --no-cache-dir -r analyzer-requirements.txt \
    && npm install --global --no-audit --no-fund eslint@10.6.0 typescript@5.8.3 \
    && composer global require --no-interaction --no-progress --prefer-dist \
        phpstan/phpstan:^2.1 laravel/pint:^1.24

COPY backend/app /app/app
CMD ["celery", "-A", "app.workers.celery_app.celery", "worker", "--loglevel=INFO", "--concurrency=2"]
