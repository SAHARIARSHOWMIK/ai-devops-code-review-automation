# GitHub App setup

1. Create a GitHub App for the organization that will own the repositories.
2. Set the webhook URL to `https://YOUR_DOMAIN/api/webhooks/github`.
3. Create a strong webhook secret and store it only in the deployment secret manager.
4. Request minimal repository permissions:
   - Metadata: read
   - Contents: read
   - Pull requests: read/write
   - Checks: read
5. Subscribe to pull-request events.
6. Generate and securely store the private key.
7. Install the App only on the intended repositories.
8. Set `GITHUB_APP_ID`, `GITHUB_INSTALLATION_ID`, `GITHUB_PRIVATE_KEY_PATH`, and `GITHUB_WEBHOOK_SECRET`.
9. Set `DEMO_MODE=false` and restart the API and worker.
10. Verify the integration page reports configured status.

Never commit the private key or installation token. Installation tokens are generated at runtime and expire automatically.
