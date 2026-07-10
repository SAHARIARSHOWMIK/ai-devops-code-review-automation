# Security design

- HMAC verification is mandatory for GitHub webhooks.
- Replayed deliveries are ignored using the GitHub delivery identifier.
- GitHub App installation tokens are generated at runtime.
- Organization IDs are checked for protected resources.
- Roles limit policy, suppression, approval, publication, and administrative operations.
- Repository archives reject traversal and symbolic/hard-link entries.
- Workspaces are temporary and deleted after analysis.
- Analyzer commands are allowlisted and executed without a shell.
- Analyzer time and output are bounded.
- Human approval is required before publication by default.
- Audit records capture changes without storing repository source code.

Report security issues privately rather than opening a public issue.
