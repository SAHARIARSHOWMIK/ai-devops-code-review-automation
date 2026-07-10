FROM node:22-bookworm-slim AS node-runtime
FROM composer:2.8 AS composer-runtime

FROM python:3.12-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    COMPOSER_HOME=/opt/composer \
    COMPOSER_ALLOW_SUPERUSER=1 \
    COMPOSER_NO_INTERACTION=1 \
    PATH="/opt/composer/vendor/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
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
        php-curl \
        php-mbstring \
        php-xml \
        php-zip \
        unzip \
    && mkdir -p "$COMPOSER_HOME" \
    && php -r 'foreach (["curl", "json", "mbstring", "tokenizer", "xml", "zip"] as $extension) { if (!extension_loaded($extension)) { fwrite(STDERR, "Missing PHP extension: {$extension}\n"); exit(1); } }' \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/analyzer-requirements.txt /app/

RUN pip install --no-cache-dir -r analyzer-requirements.txt

RUN npm install --global --no-audit --no-fund \
        eslint@10.6.0 \
        typescript@5.8.3

RUN composer global require \
        --no-interaction \
        --no-progress \
        --prefer-dist \
        phpstan/phpstan:^2.1 \
        laravel/pint:^1.24 \
    && phpstan --version \
    && pint --version

COPY backend/app /app/app

CMD ["celery", "-A", "app.workers.celery_app.celery", "worker", "--loglevel=INFO", "--concurrency=2"]
