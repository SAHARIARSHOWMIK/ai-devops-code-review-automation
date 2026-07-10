# AI DevOps & Code Review Automation Platform

[![CI](https://github.com/SAHARIARSHOWMIK/ai-devops-code-review-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/SAHARIARSHOWMIK/ai-devops-code-review-automation/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST_API-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-TypeScript-61DAFB)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A production-style, human-in-the-loop platform for reviewing GitHub pull requests with repository context, deterministic analyzers, structured AI findings, risk scoring, approval workflows, GitHub publication, re-analysis, engineering analytics, notifications, and audit logs.

> The platform identifies and explains risks. Human reviewers decide what to accept and publish.

## Why this project exists

Manual pull-request review is slow, repetitive, and inconsistent. Generic AI review is also difficult to trust when it lacks repository context, precise evidence, approval controls, or traceability. SentinelReview combines deterministic analysis and repository-aware AI while preserving human control over every published finding.

## Platform capabilities

- GitHub App authentication, installation-token exchange, webhook signature verification, delivery deduplication, PR synchronization, archive download, and review publication.
- Repository-specific policies for monitored branches, ignored paths, review profiles, analyzer settings, severity thresholds, re-review behavior, and approval requirements.
- Safe context collection across PR metadata, commits, changed files, patches, tests, configuration, dependencies, and repository guidance documents.
- Analyzer adapters for Python, JavaScript/TypeScript, PHP/Laravel, and Java, with deterministic fallback analysis when external tools are unavailable.
- Structured AI output for correctness, security, maintainability, performance, tests, documentation, and DevOps risks.
- Finding normalization, fingerprinting, multi-source deduplication, confidence filtering, suppressions, and lifecycle tracking.
- Explainable pull-request risk scores from 0–100 with merge recommendations and contributing factors.
- Human approval, editing, dismissal, false-positive marking, suppression, internal notes, and controlled GitHub publication.
- Re-analysis after new commits with findings marked fixed, still present, outdated, or reopened.
- Role-based access for platform administrators, engineering managers, repository maintainers, developers, and auditors.
- Security, quality, review-turnaround, acceptance, false-positive, analyzer, and repository-risk analytics.
- FastAPI, React/TypeScript, PostgreSQL/SQLite, Redis/Celery, Docker Compose, Alembic, and GitHub Actions.

## Review lifecycle

```text
GitHub Webhook
      ↓
Signature + delivery validation
      ↓
Repository policy and branch eligibility
      ↓
Review job queue
      ↓
Repository context collector
      ↓
Deterministic and language-specific analyzers
      ↓
Repository-aware structured AI review
      ↓
Finding normalization + deduplication
      ↓
Explainable risk engine
      ↓
Human review workspace
      ↓
Approved GitHub inline comments / summary
      ↓
Re-analysis, analytics, notifications, and audit trail
```

## User roles

| Role | Main permissions |
|---|---|
| Platform Administrator | Organizations, users, GitHub integration, global settings, audit and retention |
| Engineering Manager | Team analytics, policies, severity thresholds, reviewer assignment |
| Repository Maintainer | Repository connection, profiles, suppressions, review approval and publication |
| Developer | Assigned PR reviews, findings, responses, fixes, and re-analysis requests |
| Auditor | Read-only repositories, review history, reports, and audit logs |

## Supported review profiles

- Standard Application
- Security-Sensitive Application
- API Service
- Data/ML Project
- Laravel Application

## Supported languages and analyzer adapters

| Language | Supported adapters |
|---|---|
| Python | Ruff, Bandit, mypy, pytest/coverage |
| JavaScript / TypeScript | ESLint, TypeScript compiler, npm audit, test command |
| PHP / Laravel | PHPStan, Laravel Pint, Composer audit, PHPUnit/Laravel tests |
| Java | Checkstyle, SpotBugs, PMD, Maven tests |

Analyzer execution is isolated in the analyzer-worker container and uses fixed command allowlists, `shell=False`, execution timeouts, limited environment variables, bounded outputs, and temporary workspace cleanup. The API can continue with deterministic diff analysis if a repository or analyzer fails.

## Screenshots

### Login and engineering overview

![Login](docs/screenshots/01_login.png)

![Engineering dashboard](docs/screenshots/02_engineering_dashboard.png)

### Repository and pull-request operations

![Repository list](docs/screenshots/03_repository_list.png)

![Repository configuration](docs/screenshots/04_repository_configuration.png)

![Pull-request queue](docs/screenshots/05_pull_request_queue.png)

### Main review workspace

![Pull-request review workspace](docs/screenshots/06_review_workspace.png)

![Security finding detail](docs/screenshots/07_security_finding_detail.png)

![Diff and inline context](docs/screenshots/08_diff_and_inline_context.png)

![Test and documentation recommendations](docs/screenshots/09_test_and_documentation_recommendations.png)

![Analyzer runs](docs/screenshots/10_analyzer_runs.png)

### Approval, history, analytics, and administration

![Pending approvals](docs/screenshots/11_pending_approvals.png)

![Published review](docs/screenshots/12_published_review.png)

![Review history](docs/screenshots/13_review_history_and_reanalysis.png)

![Security dashboard](docs/screenshots/14_security_dashboard.png)

![Quality analytics](docs/screenshots/15_quality_analytics.png)

![Audit logs](docs/screenshots/16_audit_logs.png)

![GitHub integration](docs/screenshots/17_github_app_status.png)

![Configuration and RBAC](docs/screenshots/18_configuration_and_rbac.png)

![Failed analysis and retry](docs/screenshots/19_failed_analysis_retry.png)

![FastAPI documentation](docs/screenshots/20_api_documentation.png)

## Repository structure

```text
.
├── backend/
│   ├── alembic/                 # Database migrations
│   ├── app/
│   │   ├── api/                 # REST endpoints and RBAC dependencies
│   │   ├── core/                # Settings, database, and security
│   │   ├── services/            # GitHub, analyzers, AI, risk, publishing, audit
│   │   ├── workers/             # Celery worker tasks
│   │   ├── models.py            # SQLAlchemy domain model
│   │   ├── schemas.py           # Validated request/response structures
│   │   └── main.py              # FastAPI application
│   └── tests/                   # API, service, security, and context tests
├── frontend/
│   └── src/                     # React/TypeScript application
├── docker/                      # Nginx and analyzer-worker images
├── docs/                        # Architecture, deployment, security, screenshots
├── sample_repositories/         # Controlled multi-language review samples
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Run locally on Windows

### Requirements

- Python 3.12+
- Node.js 20+
- Git
- Docker Desktop is optional for the full PostgreSQL/Redis/worker stack

### Quick setup

1. Extract the project.
2. Double-click:

```text
setup_windows.bat
```

3. Load controlled demonstration repositories and review history:

```text
seed_demo.bat
```

4. Start the backend:

```text
start_backend.bat
```

5. Start the frontend in a second window:

```text
start_frontend.bat
```

6. Open:

```text
Frontend: http://localhost:5173
API docs: http://localhost:8000/docs
Health:   http://localhost:8000/api/health
```

### Demonstration accounts

All local demonstration accounts use password `demo1234`.

| Role | Email |
|---|---|
| Platform Administrator | `admin@demo.com` |
| Engineering Manager | `manager@demo.com` |
| Repository Maintainer | `maintainer@demo.com` |
| Developer | `developer@demo.com` |
| Auditor | `auditor@demo.com` |

The demonstration mode uses controlled sample repositories only. It does not publish to real GitHub repositories.

## Manual development setup

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy ..\.env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```powershell
cd frontend
npm ci
npm run dev
```

### Worker

For queued production-style processing, run Redis and then:

```powershell
cd backend
.venv\Scripts\Activate.ps1
celery -A app.workers.celery_app.celery worker -l info
```

## Docker Compose

Copy the environment template and update secrets first:

```powershell
copy .env.example .env
docker compose up --build
```

Services:

- React/Nginx frontend: `http://localhost:8080`
- FastAPI backend: `http://localhost:8000`
- PostgreSQL: internal service `db`
- Redis: internal service `redis`
- Analyzer/Celery worker: internal service `worker`

## Configure a real GitHub App

The live integration is implemented, but GitHub credentials cannot be committed to a public repository.

1. Create a GitHub App.
2. Grant only the required repository permissions:
   - Metadata: read
   - Contents: read
   - Pull requests: read/write
   - Checks: read
3. Subscribe to pull-request events.
4. Generate a private key.
5. Configure `.env`:

```text
DEMO_MODE=false
GITHUB_APP_ID=...
GITHUB_INSTALLATION_ID=...
GITHUB_PRIVATE_KEY_PATH=/secure/path/github-app.pem
GITHUB_WEBHOOK_SECRET=replace-with-a-strong-random-secret
USE_CELERY=true
```

6. Configure the webhook URL:

```text
https://your-domain.example/api/webhooks/github
```

7. Run the API, worker, PostgreSQL, Redis, and frontend.

See [GitHub App setup](docs/GITHUB_APP_SETUP.md) for the complete checklist.

## Configure the AI provider

The default structured provider is deterministic and local so the application works without paid credentials. For an OpenAI-compatible provider:

```text
AI_PROVIDER=openai_compatible
AI_BASE_URL=https://provider.example/v1
AI_API_KEY=...
AI_MODEL=your-model-name
```

The response is validated against strict structured schemas. Malformed responses are rejected, low-confidence findings are filtered, duplicates are merged, and findings are never published without the configured human approval flow.

## Testing

Backend:

```powershell
cd backend
$env:PYTHONPATH="."
pytest -q
```

Frontend:

```powershell
cd frontend
npm ci
npm run lint
npm run build
```

The repository currently includes **52 passing backend tests** covering authentication, RBAC, policies, reviews, decisions, suppressions, publishing, webhooks, context extraction safety, analyzer behavior, risk scoring, analytics, notifications, and audit logs.

GitHub Actions runs backend tests with coverage, TypeScript checks, the React production build, and both Docker image builds.

## Security architecture

- GitHub App installation tokens instead of committed personal access tokens.
- HMAC-SHA256 webhook verification and delivery-ID deduplication.
- Organization-level isolation and endpoint-level RBAC.
- PBKDF2 password hashing and signed JWT access tokens.
- Path-traversal and archive-link protections during repository extraction.
- Temporary clone cleanup after every analysis.
- Fixed analyzer command allowlists with no shell expansion.
- Timeouts, bounded outputs, and optional project-test execution.
- Source code and secrets excluded from application logs and public analytics.
- Human approval required before publication by default.
- Audit records for authentication, configuration, findings, approvals, and publication.

See [Security](docs/SECURITY.md).

## Controlled sample repositories

`sample_repositories/` contains intentionally flawed examples for Python/FastAPI, Laravel/PHP, React/TypeScript, and Java. They exist only to demonstrate review behavior and must never be deployed as production applications.

## Production notes and limitations

- Real GitHub connectivity requires your own GitHub App installation and webhook endpoint.
- Real LLM analysis requires a configured provider; the built-in provider is local and deterministic.
- External analyzers must be installed in the worker image or execution environment.
- A public staging deployment, DNS, TLS certificate, GitHub App ownership, and demonstration video require external accounts and therefore are not bundled.
- Automatic pull-request merge is intentionally not implemented.
- The platform never labels a pull request “safe”; it issues evidence-based recommendations for human review.

## Resume highlights

**AI DevOps & Code Review Automation Platform**  
*Python, FastAPI, React, PostgreSQL, Redis, GitHub App/API, LLMs, Docker*

- Built an AI-powered DevOps platform that analyzes GitHub pull requests using repository context, deterministic analyzers, and structured LLM review to identify correctness, security, maintainability, testing, documentation, and deployment risks.
- Developed a human-in-the-loop workflow with explainable pull-request risk scoring, finding approval/edit/dismiss/suppression, controlled GitHub review publication, re-analysis after new commits, and finding-resolution tracking.
- Implemented multi-language analyzer adapters, background jobs, five-role RBAC, webhook verification, retries, notifications, audit logs, engineering analytics, Docker deployment, migrations, and automated CI testing.

## License

Released under the [MIT License](LICENSE).
