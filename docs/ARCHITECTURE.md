# Architecture

## Runtime components

- **React frontend:** role-aware engineering dashboard and review workspace.
- **FastAPI API:** authentication, organizations, repositories, policies, PRs, findings, decisions, analytics, and integrations.
- **PostgreSQL:** durable production database; SQLite is supported for local use.
- **Redis/Celery:** queued pull-request analysis and retries.
- **Analyzer worker:** isolated, allowlisted language tool execution.
- **GitHub integration service:** App authentication, webhooks, repository context, and review publication.
- **AI review service:** strict structured findings and recommendations.

## Core path

```text
Webhook -> validation -> policy check -> job queue -> context -> analyzers
        -> AI review -> deduplication -> risk -> human approval -> publisher
```

## Failure behavior

Repository-context or analyzer failure is recorded as an analyzer run. The pipeline can continue with diff-only deterministic analysis where safe. Failed review runs preserve the failure reason, trigger a notification, appear in the failed-jobs page, and can be retried.
