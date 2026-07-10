# Implementation status

## Implemented

- FastAPI API and React/TypeScript frontend.
- Organizations, five-role RBAC, authentication, repositories, policies, PRs, review runs, analyzer runs, findings, decisions, publications, suppressions, notifications, and audit logs.
- GitHub App JWT and installation-token flow, webhook HMAC verification, duplicate-delivery protection, PR event handling, metadata/diff/commit/context collection, archive download, and controlled review publication.
- Repository-policy enforcement for monitored branches, ignored paths, re-review behavior, analyzer toggles, maximum diff size, security/test/documentation review, severity, and approval.
- Python, JavaScript/TypeScript, PHP/Laravel, and Java analyzer adapters plus deterministic fallback checks.
- Structured local AI provider and OpenAI-compatible external provider integration.
- Finding validation, confidence filtering, fingerprinting, deduplication, lifecycle decisions, and suppressions.
- Explainable risk scoring, merge recommendations, human approval, dry-run publication, live GitHub publication, and re-analysis/resolution tracking.
- In-app notifications, failed-job retry, security/quality/engineering analytics, and audit history.
- Redis/Celery background worker, PostgreSQL/SQLite, Alembic migrations, Docker Compose, CI, controlled sample repositories, Windows scripts, tests, and screenshots.

## Requires user-owned credentials or infrastructure

- A live GitHub App installation and public HTTPS webhook endpoint.
- A real LLM provider if the external AI mode is enabled.
- A public staging/production deployment, domain, TLS, backups, and monitoring accounts.
- SMTP/Slack/Teams provider credentials for external notifications if added to a deployment.
- Recording and publishing the portfolio demonstration video.

The included application is runnable without those credentials in local controlled-data mode, while the live integration paths remain implemented and configurable.
