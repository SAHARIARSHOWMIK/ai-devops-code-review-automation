# Deployment

## Recommended services

- Nginx/React frontend
- FastAPI API
- Celery analyzer worker
- PostgreSQL
- Redis
- TLS-enabled reverse proxy or managed ingress
- Managed secret storage and centralized logs

## Required production changes

- Replace every sample secret.
- Use PostgreSQL and run `alembic upgrade head` before deployment.
- Store the GitHub App private key outside the container image.
- Restrict network access between services.
- Run analyzers only in the dedicated worker image.
- Configure HTTPS, backups, monitoring, rate limits, retention, and workspace cleanup.
- Disable sample seeding and demonstration accounts.
